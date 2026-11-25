# REST API
from flask import Flask, request, jsonify, make_response
import requests
import json
import os
from pathlib import Path

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
    return next((u for u in users if str(u["id"]) == str(userid)), None)


def graphql_query(url, query, variables=None):
    """Envoie une requête GraphQL (POST HTTP) et renvoie (data, erreur, code HTTP).

    - service injoignable : (None, message, 502)
    - erreur GraphQL      : (None, message, code déduit de extensions.code, 400 par défaut)
    - succès              : (data, None, 200)
    """
    try:
        response = requests.post(url, json={'query': query, 'variables': variables or {}}, timeout=10)
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


@app.route("/users", methods=['GET'])
def get_users():
    """Retourne tous les utilisateurs au format JSON (200)."""
    res = make_response(jsonify(users), 200)
    return res


@app.route("/users/<userid>", methods=['GET'])
def get_users_byid(userid):
    """Retourne l'utilisateur demandé (200), ou une erreur si absent (404)."""
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    return make_response(jsonify(user), 200)


@app.route("/users/<userid>", methods=["POST"])
def add_user(userid):
    """Crée un utilisateur (200), ou renvoie 400 (id incohérent), 409 (doublon), 415 (format)."""
    if not request.is_json:
        return make_response(jsonify({'error': 'Content-Type must be application/json.'}), 415)
    req = request.get_json()
    if str(req.get("id")) != str(userid):
        return make_response(jsonify({"error": "The id in the body must match the id in the URL."}), 400)
    if find_user(userid) is not None:
        return make_response(jsonify({"error": "User ID already exists."}), 409)
    users.append(req)
    write(users)

    response = make_response(jsonify({'message': 'User added.'}), 200)
    return response


@app.route("/users/<userid>/<last_active>", methods=['PUT'])
def update_user_last_active(userid, last_active):
    """Met à jour l'activité (200), ou retourne 400 si invalide et 404 si absent."""
    try:
        timestamp = int(last_active)
    except ValueError:
        return make_response(jsonify({'error': 'User last_active must be an integer timestamp.'}), 400)
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    user["last_active"] = timestamp
    write(users)
    return make_response(jsonify(user), 200)


@app.route("/users/<userid>", methods=['DELETE'])
def del_user(userid):
    """Supprime et retourne un utilisateur (200), ou une erreur si absent (404)."""
    user = find_user(userid)
    if user is None:
        return make_response(jsonify({"error": "User ID not found."}), 404)
    users.remove(user)
    write(users)
    return make_response(jsonify(user), 200)


@app.route("/users/<userid>/bookings", methods=['GET'])
def get_user_bookings(userid):
    """Retourne les réservations de l'utilisateur via Booking (GraphQL) : 200, ou 404."""
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
    """Retourne les réservations avec le détail des films (Booking -> Movie en GraphQL) : 200, ou 404."""
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
    """Ajoute une réservation {date, movieid} via la mutation GraphQL de Booking : 200, 400, 404 ou 409."""
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
    """Retire une seule réservation (un film à une date) via Booking (GraphQL) : 200, ou 404."""
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
