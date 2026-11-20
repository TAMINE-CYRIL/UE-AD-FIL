
import json
from pathlib import Path

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

PORT = 3201
HOST = "0.0.0.0"

SCHEDULE_URL = "http://localhost:3202"
MOVIE_URL = "http://localhost:3200"
BOOKINGS_PATH = Path(__file__).resolve().parent / "databases" / "bookings.json"

with BOOKINGS_PATH.open(encoding="utf-8") as f:
    bookings = json.load(f)["bookings"]


def write():
    """Sauvegarde les réservations dans le fichier JSON."""
    with BOOKINGS_PATH.open("w", encoding="utf-8") as f:
        json.dump({"bookings": bookings}, f, indent=2, ensure_ascii=False)


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

    req = request.get_json(silent=True)

    if not isinstance(req, dict):
        return jsonify({"error": "Invalid JSON."}), 400

    date = req.get("date")
    movieid = req.get("movieid")

    if not isinstance(date, str) or not isinstance(movieid, str) or not date or not movieid:
        return jsonify({"error": "Date and movieid required."}), 400

    for booking in bookings:
        if booking["userid"] == userid:

            for entry in booking["dates"]:
                if entry["date"] == date:

                    if movieid in entry["movies"]:
                        return jsonify({
                            "error": "Movie already booked."
                        }), 409

                    entry["movies"].append(movieid)
                    write()

                    return jsonify({"message": "Booking added."}), 201

            booking["dates"].append({
                "date": date,
                "movies": [movieid]
            })

            write()
            return jsonify({"message": "Booking added."}), 201

    new_booking = {
        "userid": userid,
        "dates": [
            {
                "date": date,
                "movies": [movieid]
            }
        ]
    }

    bookings.append(new_booking)
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
            response = get_service(f"{MOVIE_URL}/movies/{movieid}")

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
