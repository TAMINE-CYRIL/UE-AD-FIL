# REST API
from flask import Flask, request, jsonify, make_response
import requests
import json
import os
from pathlib import Path

from werkzeug.security import check_password_hash, generate_password_hash

from auth import create_token, get_connected_user

app = Flask(__name__)

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

USERS_PATH = Path(__file__).resolve().parent / 'data' / 'users.json'

with USERS_PATH.open(encoding='utf-8') as jsf:
    users = json.load(jsf)["users"]


def write(users):
    """Enregistre la liste des utilisateurs dans le fichier JSON du service."""
    with USERS_PATH.open('w', encoding='utf-8') as f:
        json.dump({'users': users}, f, ensure_ascii=False, indent=2)


def find_user(userid):
    """Renvoie l'utilisateur correspondant à l'identifiant, ou None."""
    for user in users:
        if str(user["id"]) == str(userid):
            return user
    return None


def public_user(user):
    """Copie de l'utilisateur sans le hash du mot de passe (à utiliser pour toute réponse)."""
    result = dict(user)
    result.pop('password_hash', None)
    return result


def check_admin():
    """Renvoie une réponse d'erreur si l'appelant n'est pas admin (401 ou 403), sinon None."""
    user = get_connected_user()
    if user is None:
        return make_response(jsonify({"error": "Authentication required."}), 401)
    if not user['admin']:
        return make_response(jsonify({"error": "Admin rights required."}), 403)
    return None


def check_self_or_admin(userid):
    """Renvoie une réponse d'erreur si l'appelant n'est ni `userid` ni admin (401 ou 403), sinon None."""
    user = get_connected_user()
    if user is None:
        return make_response(jsonify({"error": "Authentication required."}), 401)
    if user['sub'] != userid and not user['admin']:
        return make_response(jsonify({"error": "You can only access your own data."}), 403)
    return None


def graphql_query(url, query, variables=None):
    """Envoie une requête GraphQL (POST HTTP) en transmettant le JWT de l'appelant,
    et renvoie (data, erreur, code HTTP).

    - service injoignable : (None, message, 502)
    - erreur GraphQL      : (None, message, code déduit de extensions.code, 400 par défaut)
    - succès              : (data, None, 200)
    """
    headers = {}
    if request.headers.get('Authorization'):
        headers['Authorization'] = request.headers['Authorization']
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
    """Connexion {id, password} : renvoie un JWT (200), ou 401 si les identifiants sont invalides."""
    req = request.get_json(silent=True) or {}
    user = find_user(req.get('id'))
    if user is None or not check_password_hash(user.get('password_hash', ''), str(req.get('password', ''))):
        return make_response(jsonify({"error": "Invalid credentials."}), 401)
    return make_response(jsonify({"token": create_token(user)}), 200)


@app.route("/users", methods=['GET'])
def get_users():
    """Retourne tous les utilisateurs (admin uniquement) : 200, 401 ou 403."""
    error = check_admin()
    if error:
        return error
    result = []
    for user in users:
        result.append(public_user(user))
    return make_response(jsonify(result), 200)


@app.route("/users/<userid>", methods=['GET'])
def get_users_byid(userid):
    """Retourne l'utilisateur demandé (lui-même ou admin) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    return make_response(jsonify(public_user(user)), 200)


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
    # Seul un admin connecté peut créer un autre admin
    caller = get_connected_user()
    if req.get('admin') and caller is not None and caller['admin']:
        new_user['admin'] = True
    users.append(new_user)
    write(users)
    return make_response(jsonify({'message': 'User added.'}), 200)


@app.route("/users/<userid>/<last_active>", methods=['PUT'])
def update_user_last_active(userid, last_active):
    """Met à jour l'activité (lui-même ou admin) : 200, 400 si invalide, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    try:
        timestamp = int(last_active)
    except ValueError:
        return make_response(jsonify({'error': 'User last_active must be an integer timestamp.'}), 400)
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    user["last_active"] = timestamp
    write(users)
    return make_response(jsonify(public_user(user)), 200)


@app.route("/users/<userid>", methods=['DELETE'])
def del_user(userid):
    """Supprime et retourne un utilisateur (lui-même ou admin) : 200, 401, 403 ou 404."""
    error = check_self_or_admin(userid)
    if error:
        return error
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    users.remove(user)
    write(users)
    return make_response(jsonify(public_user(user)), 200)


@app.route("/users/<userid>/bookings", methods=['GET'])
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
