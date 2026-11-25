from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3202
HOST = '0.0.0.0'

with open('{}/databases/times.json'.format("."), "r") as jsf:
   schedule = json.load(jsf)["schedule"]

def write(schedule):
    """Fonction d'écriture de fichier."""
    with open('{}/databases/times.json'.format("."), 'w') as f:
        full = {}
        full['schedule']=schedule
        json.dump(full, f)


def schedule_validation_error(showtime, date):
    """Retourne le premier message d'erreur si la programmation est invalide."""
    if not isinstance(showtime, dict):
        return 'Request body must be a valid JSON object.'
    if showtime.get('date') != date:
        return 'Schedule date must match the URL date.'
    movies = showtime.get('movies')
    if not isinstance(movies, list):
        return 'Schedule movies must be a list of non-empty movie IDs.'
    for movieid in movies:
        if not isinstance(movieid, str) or not movieid.strip():
            return 'Schedule movies must be a list of non-empty movie IDs.'
    return None


@app.route("/", methods=['GET'])
def home():
   """ Renvoie la page d'accueil de l'API schedule. """
   return "<h1 style='color:blue'>Welcome to the Showtime service!</h1>"

@app.route("/schedule", methods=['GET'])
def get_schedule():
   """Renvoie l'intégralité des plannings, renvoie 200"""
   return make_response(jsonify(schedule), 200)

@app.route("/schedule/<date>", methods=['GET'])
def get_schedule_bydate(date):
   """Renvoie un planning basé sur sa date. Renvoie 404 si la date n'est pas trouvé, sinon 200"""
   for showtime in schedule:
        if str(showtime["date"]) == date:
            return jsonify(showtime), 200

   return jsonify({"error": "Date not found."}), 404

@app.route("/schedule/<date>", methods=["POST"])
def create_schedule(date):
   """Crée un planning (201), ou renvoie 400, 409 ou 415."""
   if not request.is_json:
      return jsonify({'error': 'Content-Type must be application/json.'}), 415
   req = request.get_json()
   error = schedule_validation_error(req, date)
   if error is not None:
      return jsonify({'error': error}), 400
   for showtime in schedule:
      if str(showtime["date"]) == date:
         return make_response(jsonify({"error" : "This date already exists."}), 409)

   schedule.append(req)
   write(schedule)
   return make_response(jsonify({"message": "Schedule added."}), 201)

@app.route("/schedule/<date>", methods=['DELETE'])
def delete_schedule(date):
   """Supprime un planning basé sur sa date, renvoie 200 si le planning est supprimé.
   Sinon renvoie 404 si le planning n'est pas trouvé. 
   """
   for showtime in schedule:
      if str(showtime["date"]) == str(date):
         schedule.remove(showtime)
         write(schedule)
         return make_response(jsonify({"message" : "Schedule deleted."}), 200)

   return make_response(jsonify({"error": "Schedule not found."}), 404)

if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
