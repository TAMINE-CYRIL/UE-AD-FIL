# REST API
from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import (JWTManager, create_access_token, get_jwt, get_jwt_identity,
                                jwt_required, set_access_cookies, verify_jwt_in_request)
import requests
import json
import os
from datetime import timedelta
from pathlib import Path

from pymongo import MongoClient
from bson.json_util import dumps
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Initialisation de la partie JWT (même secret dans les 4 services, défini dans le .env)
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET', 'dev-secret-change-me')
# Le token est accepté dans l'en-tête Authorization OU dans un cookie
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
# Si à True, le cookie n'est envoyé qu'en HTTPS (compliqué en développement local)
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

PORT = 3203
HOST = '0.0.0.0'

BOOKING_URL = os.environ.get('BOOKING_URL', 'http://localhost:3201/graphql')

BOOKING_QUERY = """
query($userid: String!) {
    booking_by_user(userid: $userid) {
        userid
        dates {
            date
            movies
        }
    }
}
"""

BOOKING_MOVIES_QUERY = """
query($userid: String!) {
    booking_by_user(userid: $userid) {
        userid
        dates {
            date
            movies_details {
                id
                title
                director
                rating
            }
        }
    }
}
"""

ADD_BOOKING_MUTATION = """
mutation($userid: String!, $date: String!, $movieid: String!) {
    add_booking(userid: $userid, date: $date, movieid: $movieid) {
        userid
        dates {
            date
            movies
        }
    }
}
"""

DELETE_BOOKING_MOVIE_MUTATION = """
mutation($userid: String!, $date: String!, $movieid: String!) {
    delete_booking_movie(userid: $userid, date: $date, movieid: $movieid) {
        userid
        dates {
            date
            movies
        }
    }
}
"""


# Correspondance entre le code d'erreur GraphQL renvoyé par Booking (extensions.code) et le code HTTP
ERROR_STATUS = {
    'BAD_REQUEST': 400,
    'UNAUTHENTICATED': 401,
    'FORBIDDEN': 403,
    'NOT_FOUND': 404,
    'CONFLICT': 409,
    'SERVICE_UNAVAILABLE': 502,
}

# Fichier JSON qui sert uniquement à remplir la base au premier démarrage
USERS_PATH = Path(__file__).resolve().parent / 'data' / 'users.json'

# Connexion à la base MongoDB (dans Docker, MONGO_URL pointe sur le conteneur "mongo")
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://root:example@localhost:27017/')
client = MongoClient(MONGO_URL)

# Base de données "users" et collection "users" (créées si elles n'existent pas)
db = client["users"]
collection = db["users"]

# Chargement initial : on insère les utilisateurs du fichier JSON si la collection est vide
# (sinon ils seraient ajoutés en double à chaque redémarrage du service)
if collection.count_documents({}) == 0:
    with USERS_PATH.open(encoding='utf-8') as jsf:
        users = json.load(jsf)["users"]
    collection.insert_many(users)


def find_user(userid):
    """Renvoie l'utilisateur correspondant à l'identifiant, ou None."""
    return collection.find_one({"id": str(userid)})


def public_user(user):
    """Copie de l'utilisateur sans le hash du mot de passe (à utiliser pour toute réponse)."""
    result = dict(user)
    result.pop('password_hash', None)
    return result


def is_admin():
    """Indique si l'utilisateur du token est admin (False si le champ "admin" est absent du token)."""
    claims = get_jwt()
    return claims.get('admin', False)


def check_admin():
    """Renvoie une réponse d'erreur 403 si l'utilisateur du token n'est pas admin, sinon None.
    (Le token lui-même est déjà vérifié par @jwt_required() : 401 s'il est absent ou expiré.)"""
    if not is_admin():
        return make_response(jsonify({"error": "Admin rights required."}), 403)
    return None


def check_self_or_admin(userid):
    """Renvoie une réponse d'erreur 403 si l'utilisateur du token n'est ni `userid` ni admin, sinon None."""
    if get_jwt_identity() != userid and not is_admin():
        return make_response(jsonify({"error": "You can only access your own data."}), 403)
    return None


def get_token():
    """Renvoie le token JWT brut reçu par la requête : dans l'en-tête Authorization, sinon dans le cookie."""
    header = request.headers.get('Authorization', '')
    if header.startswith('Bearer '):
        return header[len('Bearer '):]
    return request.cookies.get('access_token_cookie')


def graphql_query(url, query, variables=None):
    """Envoie une requête GraphQL (POST HTTP) en transmettant le JWT de l'appelant,
    et renvoie (data, erreur, code HTTP).

    Le token est toujours retransmis dans l'en-tête Authorization, même s'il est arrivé par cookie.

    - service injoignable : (None, message, 502)
    - erreur GraphQL      : (None, message, code déduit de extensions.code, 400 par défaut)
    - succès              : (data, None, 200)
    """
    headers = {}
    token = get_token()
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        response = requests.post(url, json={'query': query, 'variables': variables or {}},
                                 headers=headers, timeout=10)
        body = response.json()
    except (requests.RequestException, ValueError):
        return None, "Booking service unavailable.", 502
    if body.get('errors'):
        error = body['errors'][0]
        code = (error.get('extensions') or {}).get('code')
        return None, error.get('message', 'GraphQL error'), ERROR_STATUS.get(code, 400)
    return body['data'], None, 200


@app.route("/", methods=['GET'])
def home():
    """Retourne la page d'accueil HTML du service."""
    return make_response("<h1 style='color:blue'>Welcome to the User service!</h1>", 200)


@app.route("/login", methods=['POST'])
def login():
    """Connexion {id, password} : renvoie un JWT dans la réponse ET dans un cookie (200),
    ou 401 si les identifiants sont invalides."""
    # 1. Récupérer dans la requête l'utilisateur qui souhaite se connecter
    req = request.get_json(silent=True) or {}
    # 2. Valider que l'utilisateur existe bien (et que son mot de passe est correct)
    user = find_user(req.get('id'))
    if user is None or not check_password_hash(user.get('password_hash', ''), str(req.get('password', ''))):
        return make_response(jsonify({"error": "Invalid credentials."}), 401)
    # 3. Création d'un token d'accès JWT, avec le rôle admin en claim supplémentaire
    additional_claims = {'admin': user.get('admin', False)}
    token = create_access_token(identity=user['id'], additional_claims=additional_claims)
    # 4. Renvoi du token créé, dans la réponse et dans un cookie
    response = make_response(jsonify({"token": token}), 200)
    set_access_cookies(response, token)
    return response


@app.route("/users", methods=['GET'])
@jwt_required()
def get_users():
    """Retourne tous les utilisateurs (admin uniquement) : 200, 401 ou 403."""
    error = check_admin()
    if error:
        return error
    result = []
    for user in list(collection.find()):
        result.append(public_user(user))
    return make_response(dumps(result), 200)


@app.route("/users/<userid>", methods=['GET'])
@jwt_required()
def get_users_byid(userid):
    """Retourne l'utilisateur demandé (lui-même ou admin) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    return make_response(dumps(public_user(user)), 200)


@app.route("/users/<userid>", methods=["POST"])
def add_user(userid):
    """Inscription {id, name, password, ...} : 200, ou 400 (id incohérent / mot de passe manquant),
    409 (doublon), 415 (format). Le mot de passe est haché ; 'admin' est forcé à false sauf si
    l'appelant est un admin connecté."""
    if not request.is_json:
        return make_response(jsonify({'error': 'Content-Type must be application/json.'}), 415)
    req = request.get_json()
    if str(req.get("id")) != str(userid):
        return make_response(jsonify({"error": "The id in the body must match the id in the URL."}), 400)
    if not req.get("password"):
        return make_response(jsonify({"error": "Field 'password' is required."}), 400)
    if find_user(userid) is not None:
        return make_response(jsonify({"error": "User ID already exists."}), 409)

    new_user = {
        'id': userid,
        'name': req.get('name', ''),
        'last_active': req.get('last_active', 0),
        'password_hash': generate_password_hash(req['password']),
        'admin': False,
    }
    # Seul un admin connecté peut créer un autre admin (token facultatif sur cette route)
    if req.get('admin') and verify_jwt_in_request(optional=True) and is_admin():
        new_user['admin'] = True
    collection.insert_one(new_user)
    return make_response(jsonify({'message': 'User added.'}), 200)


@app.route("/users/<userid>", methods=['PUT'])
@jwt_required()
def update_user_last_active(userid):
    """Met à jour l'activité avec le corps JSON {"last_active": <timestamp entier>} (lui-même ou admin) :
    200, 400 si la valeur est absente ou invalide, 401, 403, 404, ou 415 si le corps n'est pas du JSON."""
    error = check_self_or_admin(userid)
    if error:
        return error
    if not request.is_json:
        return make_response(jsonify({'error': 'Content-Type must be application/json.'}), 415)
    req = request.get_json(silent=True) or {}
    timestamp = req.get('last_active')
    # type(...) is int refuse aussi True/False, qui sont des int en Python
    if type(timestamp) is not int:
        return make_response(jsonify({'error': "Field 'last_active' must be an integer timestamp."}), 400)
    if find_user(userid) is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    myquery = {"id": userid}
    newvalues = {"$set": {"last_active": timestamp}}
    collection.update_one(myquery, newvalues)
    return make_response(dumps(public_user(find_user(userid))), 200)


@app.route("/users/<userid>", methods=['DELETE'])
@jwt_required()
def del_user(userid):
    """Supprime et retourne un utilisateur (lui-même ou admin) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    collection.delete_one({"id": userid})
    return make_response(dumps(public_user(user)), 200)


@app.route("/users/<userid>/bookings", methods=['GET'])
@jwt_required()
def get_user_bookings(userid):
    """Retourne les réservations de l'utilisateur via Booking (GraphQL) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    if find_user(userid) is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    data, error, status = graphql_query(BOOKING_URL, BOOKING_QUERY, {'userid': userid})
    if error:
        return make_response(jsonify({"error": error}), status)
    booking = data['booking_by_user']
    if booking is None:
        return make_response(jsonify({"error": "No booking for this user."}), 404)
    return make_response(jsonify(booking), 200)


@app.route("/users/<userid>/bookings/movies", methods=['GET'])
@jwt_required()
def get_user_bookings_movies(userid):
    """Retourne les réservations avec le détail des films (Booking -> Movie) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    if find_user(userid) is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    data, error, status = graphql_query(BOOKING_URL, BOOKING_MOVIES_QUERY, {'userid': userid})
    if error:
        return make_response(jsonify({"error": error}), status)
    booking = data['booking_by_user']
    if booking is None:
        return make_response(jsonify({"error": "No booking for this user."}), 404)
    return make_response(jsonify(booking), 200)


@app.route("/users/<userid>/bookings", methods=['POST'])
@jwt_required()
def add_user_booking(userid):
    """Ajoute une réservation {date, movieid} via Booking : 200, 400, 401, 403, 404 ou 409."""
    error = check_self_or_admin(userid)
    if error:
        return error
    if find_user(userid) is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    req = request.get_json(silent=True) or {}
    if not req.get('date') or not req.get('movieid'):
        return make_response(jsonify({"error": "Fields 'date' and 'movieid' are required."}), 400)
    data, error, status = graphql_query(BOOKING_URL, ADD_BOOKING_MUTATION,
                                        {'userid': userid, 'date': req['date'], 'movieid': req['movieid']})
    if error:
        return make_response(jsonify({"error": error}), status)
    return make_response(jsonify(data['add_booking']), 200)


@app.route("/users/<userid>/bookings/<date>/<movieid>", methods=['DELETE'])
@jwt_required()
def delete_user_booking(userid, date, movieid):
    """Retire une seule réservation (un film à une date) via Booking : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    if find_user(userid) is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    data, error, status = graphql_query(BOOKING_URL, DELETE_BOOKING_MOVIE_MUTATION,
                                        {'userid': userid, 'date': date, 'movieid': movieid})
    if error:
        return make_response(jsonify({"error": error}), status)
    return make_response(jsonify(data['delete_booking_movie']), 200)


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
