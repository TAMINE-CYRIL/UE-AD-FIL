
import json

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

PORT = 3201
HOST = "0.0.0.0"

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
    bookings = json.load(jsf)["bookings"]


def write():
    """Sauvegarde les réservations dans le fichier JSON."""
    with open('{}/databases/bookings.json'.format("."), 'w') as f:
        full = {}
        full['bookings'] = bookings
        json.dump(full, f)


def find_user(userid):
    """Recherche les réservations d'un utilisateur."""
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            return booking
    return None


def get_service(url):
    """Interroge un autre microservice."""
    try:
        return requests.get(url, timeout=5)
    except requests.RequestException:
        return None


def schedule_error(date, movieid):
    """Retourne une réponse d'erreur si le film ne peut pas être réservé."""
    response = get_service(f"http://localhost:3202/schedule/{date}")
    if response is None:
        return jsonify({"error": "Schedule service unavailable."}), 502
    if response.status_code == 404:
        return jsonify({"error": "Schedule date not found."}), 404
    if response.status_code != 200:
        return jsonify({"error": "Could not retrieve schedule."}), 502

    try:
        showtime = response.json()
    except ValueError:
        return jsonify({"error": "Invalid schedule response."}), 502

    if not isinstance(showtime, dict) or not isinstance(showtime.get("movies"), list):
        return jsonify({"error": "Invalid schedule response."}), 502
    if movieid not in showtime["movies"]:
        return jsonify({"error": "Movie is not scheduled for this date."}), 404
    return None


@app.route("/", methods=["GET"])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"


@app.route("/bookings/<userid>", methods=["GET"])
def get_bookings(userid):
    booking = find_user(userid)

    if booking is None:
        return jsonify({"error": "Booking not found."}), 404

    return jsonify(booking), 200



@app.route("/bookings/<userid>", methods=["POST"])
def add_booking(userid):
    if not request.is_json:
        return jsonify({"error": "JSON required."}), 415

    req = request.get_json()

    if not isinstance(req, dict):
        return jsonify({"error": "Invalid JSON."}), 400

    date = req.get("date")
    movieid = req.get("movieid")

    if not isinstance(date, str) or not isinstance(movieid, str) or not date or not movieid:
        return jsonify({"error": "Date and movieid required."}), 400

    error = schedule_error(date, movieid)
    if error is not None:
        return error

    booking = find_user(userid)
    if booking is None:
        booking = {"userid": userid, "dates": []}
        bookings.append(booking)

    booking_date = None
    for entry in booking["dates"]:
        if entry["date"] == date:
            booking_date = entry
            break

    if booking_date is None:
        booking_date = {"date": date, "movies": []}
        booking["dates"].append(booking_date)

    if movieid in booking_date["movies"]:
        return jsonify({"error": "Movie already booked."}), 409

    booking_date["movies"].append(movieid)
    write()
    return jsonify({"message": "Booking added."}), 201


@app.route("/bookings/<userid>/<date>/<movieid>", methods=["DELETE"])
def delete_booking(userid, date, movieid):

    booking = find_user(userid)

    if booking is None:
        return jsonify({"error": "Booking not found."}), 404

    for entry in booking["dates"]:
        if entry["date"] == date:

            if movieid not in entry["movies"]:
                return jsonify({"error": "Movie not booked."}), 404

            entry["movies"].remove(movieid)

            if not entry["movies"]:
                booking["dates"].remove(entry)

            if not booking["dates"]:
                bookings.remove(booking)

            write()
            return jsonify({"message": "Booking deleted."}), 200

    return jsonify({"error": "Booking not found."}), 404


@app.route("/bookings/<userid>", methods=["DELETE"])
def delete_user_bookings(userid):

    booking = find_user(userid)

    if booking is None:
        return jsonify({"error": "Booking not found."}), 404

    bookings.remove(booking)
    write()

    return jsonify({"message": "All bookings deleted."}), 200


@app.route("/bookings/<userid>/details", methods=["GET"])
def get_booking_details(userid):

    booking = find_user(userid)

    if booking is None:
        return jsonify({"error": "Booking not found."}), 404

    result = {
        "userid": str(userid),
        "dates": []
    }

    for entry in booking["dates"]:
        movies_details = []

        for movieid in entry["movies"]:
            response = get_service(f"{"http://localhost:3200"}/movies/{movieid}")

            if response is None:
                return jsonify({
                    "error": "Movie service unavailable."
                }), 502

            if response.status_code != 200:
                return jsonify({
                    "error": "Could not retrieve movie details."
                }), 502

            try:
                movies_details.append(response.json())
            except ValueError:
                return jsonify({
                    "error": "Invalid movie response."
                }), 502

        result["dates"].append({
            "date": entry["date"],
            "movies": movies_details
        })

    return jsonify(result), 200


if __name__ == "__main__":
    print(f"Server running on port {PORT}")
    app.run(host=HOST, port=PORT)
