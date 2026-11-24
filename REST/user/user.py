import json

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'

with open('{}/databases/users.json'.format("."), "r") as jsf:
    users = json.load(jsf)["users"]


def write(users):
    """Enregistre la liste des utilisateurs dans le fichier JSON du service."""
    with open('{}/databases/users.json'.format("."), 'w') as f:
        full = {}
        full['users'] = users
        json.dump(full, f)

def user_validation_error(user, userid):
    """Retourne le premier message d'erreur si l'utilisateur est invalide."""
    if not isinstance(user, dict):
        return 'Request body must be a valid JSON object.'
    name = user.get('name')
    last_active = user.get('last_active')
    if user.get('id') != userid:
        return 'User ID must match the URL ID.'
    if not isinstance(name, str) or not name.strip():
        return 'User name must be a non-empty string.'
    if type(last_active) is not int:
        return 'User last_active must be an integer timestamp.'
    return None


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
    """Retourne l'utilisateur demandé (201), ou une erreur si absent (404)."""
    for user in users:
        if str(user["id"]) == str(userid):
            return make_response(jsonify(user), 200)
    return make_response(jsonify({"error": "User ID not found."}), 404)

@app.route("/users/<userid>", methods=["POST"])
def add_user(userid):
    """Crée un utilisateur (201), ou renvoie 400, 409 ou 415."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json.'}), 415
    req = request.get_json()
    error = user_validation_error(req, userid)
    if error is not None:
        return jsonify({'error': error}), 400
    for user in users:
        if str(user["id"]) == str(userid):
            return make_response(jsonify({"error": "User ID already exists."}), 409)
    users.append(req)
    write(users)

    response = make_response(jsonify({'message': 'User added.'}), 201)
    return response


@app.route("/users/<userid>/<last_active>", methods=['PUT'])
def update_user_last_active(userid, last_active):
    """Met à jour l'activité (200), ou retourne 400 si invalide et 404 si absent."""
    try:
        timestamp = int(last_active)
    except ValueError:
        return jsonify({'error': 'User last_active must be an integer timestamp.'}), 400
    for user in users:
        if str(user["id"]) == str(userid):
            user["last_active"] = timestamp
            res = make_response(jsonify(user), 200)
            write(users)
            return res

    res = make_response(jsonify({"error": "User ID not found."}), 404)
    return res


@app.route("/users/<userid>", methods=['DELETE'])
def del_user(userid):
    """Supprime et retourne un utilisateur (200), ou une erreur si absent (404)."""
    for user in users:
        if str(user["id"]) == str(userid):
            users.remove(user)
            write(users)
            return make_response(jsonify(user), 200)

    res = make_response(jsonify({"error": "User ID not found."}), 404)
    return res


if __name__ == "__main__":
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
