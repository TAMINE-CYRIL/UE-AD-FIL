from flask import Flask, request, jsonify, make_response
from flask_jwt_extended import JWTManager, get_jwt, jwt_required
import json
import os
from datetime import timedelta
from pathlib import Path

app = Flask(__name__)

# Initialisation de la partie JWT (même secret dans les 4 services, défini dans le .env)
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET', 'dev-secret-change-me')
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

PORT = 3202
HOST = '0.0.0.0'

TIMES_PATH = Path(__file__).resolve().parent / 'data' / 'times.json'

with TIMES_PATH.open(encoding='utf-8') as jsf:
    schedule = json.load(jsf)["schedule"]


def write(schedule):
    """Fonction d'écriture de fichier."""
    with TIMES_PATH.open('w', encoding='utf-8') as f:
        full = {}
        full['schedule'] = schedule
        json.dump(full, f, indent=2)


def check_admin():
    """Renvoie une réponse d'erreur 403 si l'utilisateur du token n'est pas admin, sinon None.
    (Le token lui-même est déjà vérifié par @jwt_required() : 401 s'il est absent ou expiré.)"""
    claims = get_jwt()
    # Si le champ "admin" n'est pas dans le token, l'utilisateur n'est pas admin
    if not claims.get('admin', False):
        return make_response(jsonify({"error": "Admin rights required."}), 403)
    return None


@app.route("/", methods=['GET'])
def home():
    """Renvoie la page d'accueil de l'API schedule."""
    return "<h1 style='color:blue'>Welcome to the Showtime service!</h1>"


@app.route("/schedule", methods=['GET'])
def get_schedule():
    """Renvoie l'intégralité des plannings, renvoie 200"""
    return make_response(jsonify(schedule), 200)


@app.route("/schedule/<date>", methods=['GET'])
def get_schedule_bydate(date):
    """Renvoie un planning basé sur sa date. Renvoie 404 si la date n'est pas trouvée, sinon 200"""
    for showtime in schedule:
        if str(showtime["date"]) == str(date):
            return make_response(jsonify(showtime), 200)
    return make_response(jsonify({"error": "Date not found."}), 404)


@app.route("/schedule/<date>", methods=["POST"])
@jwt_required()
def create_schedule(date):
    """Crée un planning (admin, sinon 401/403). Renvoie 415 si le corps n'est pas du JSON, 400 si la date du corps
    ne correspond pas à celle de l'URL, 409 si la date existe déjà, sinon 200."""
    error = check_admin()
    if error:
        return error
    if not request.is_json:
        return make_response(jsonify({"error": "Content-Type must be application/json."}), 415)
    req = request.get_json()
    if str(req.get("date")) != str(date):
        return make_response(jsonify({"error": "The date in the body must match the date in the URL."}), 400)
    for showtime in schedule:
        if str(showtime["date"]) == str(date):
            return make_response(jsonify({"error": "This date already exists."}), 409)

    schedule.append(req)
    write(schedule)
    return make_response(jsonify({"message": "Schedule added."}), 200)


@app.route("/schedule/<date>", methods=['DELETE'])
@jwt_required()
def delete_schedule(date):
    """Supprime un planning basé sur sa date (admin, sinon 401/403), renvoie 200 si le planning est supprimé.
    Sinon renvoie 404 si le planning n'est pas trouvé.
    """
    error = check_admin()
    if error:
        return error
    for showtime in schedule:
        if str(showtime["date"]) == str(date):
            schedule.remove(showtime)
            write(schedule)
            return make_response(jsonify({"message": "Schedule deleted."}), 200)

    return make_response(jsonify({"error": "Schedule not found."}), 404)


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
