from flask import Flask, request, jsonify, make_response
import json

app = Flask(__name__)

PORT = 3202
HOST = '0.0.0.0'

with open('{}/data/times.json'.format("."), "r") as jsf:
    schedule = json.load(jsf)["schedule"]


def write(schedule):
    """Fonction d'écriture de fichier."""
    with open('{}/data/times.json'.format("."), 'w') as f:
        full = {}
        full['schedule'] = schedule
        json.dump(full, f, indent=2)


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
def create_schedule(date):
    """Crée un planning. Renvoie 415 si le corps n'est pas du JSON, 400 si la date du corps
    ne correspond pas à celle de l'URL, 409 si la date existe déjà, sinon 200."""
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
def delete_schedule(date):
    """Supprime un planning basé sur sa date, renvoie 200 si le planning est supprimé.
    Sinon renvoie 404 si le planning n'est pas trouvé.
    """
    for showtime in schedule:
        if str(showtime["date"]) == str(date):
            schedule.remove(showtime)
            write(schedule)
            return make_response(jsonify({"message": "Schedule deleted."}), 200)

    return make_response(jsonify({"error": "Schedule not found."}), 404)


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
