import json

from flask import Flask, jsonify, make_response, request, url_for

app = Flask(__name__)

PORT = 3200
HOST = '0.0.0.0'

with open('{}/databases/movies.json'.format("."), "r") as jsf:
    movies = json.load(jsf)["movies"]


def write(movies):
    """Enregistre la liste des films dans le fichier JSON du service."""
    with open('{}/databases/movies.json'.format("."), 'w') as f:
        full = {}
        full['movies'] = movies
        json.dump(full, f)


def valid_rating(value):
    """Vérifie qu'une note est un nombre fini compris entre 0 et 10."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 10
    )


def movie_validation_error(movie, movieid):
    """Retourne le premier message d'erreur si le film est invalide."""
    if not isinstance(movie, dict):
        return 'Request body must be a valid JSON object.'
    title = movie.get('title')
    rating = movie.get('rating')
    director = movie.get('director')
    if movie.get('id') != movieid:
        return 'Movie ID must match the URL ID.'
    if not isinstance(title, str) or not title.strip():
        return 'Movie title must be a non-empty string.'
    if not valid_rating(rating):
        return 'Movie rating must be a number between 0 and 10.'
    if not isinstance(director, str):
        return 'Movie director must be a string.'
    return None


@app.route("/", methods=['GET'])
def home():
    """Retourne la page d'accueil HTML du service."""
    return make_response("<h1 style='color:blue'>Welcome to the Movie service!</h1>", 200)


@app.route("/movies", methods=['GET'])
def get_movies():
    """Retourne tous les films au format JSON (200)."""
    res = make_response(jsonify(movies), 200)
    return res


@app.route("/movies/<movieid>", methods=['GET'])
def get_movies_byid(movieid):
    """Retourne le film demandé (200), ou une erreur si absent (404)."""
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            return make_response(jsonify(movie), 200)
    return make_response(jsonify({"error": "Movie ID not found."}), 404)


@app.route('/moviesbytitle', methods=['GET'])
def get_movie_bytitle():
    """Recherche un titre exact : succès 200, paramètre invalide 400, absent 404."""
    title = request.args.get('title')
    if title is None or not title.strip():
        return jsonify({'error': 'A non-empty title query parameter is required.'}), 400
    for movie in movies:
        if movie['title'] == title:
            return jsonify(movie), 200
    return jsonify({'error': 'Movie title not found.'}), 404


@app.route("/movies/<movieid>", methods=["POST"])
def add_movie(movieid):
    """Crée un film (201), ou renvoie 400, 409 ou 415."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json.'}), 415
    req = request.get_json()
    error = movie_validation_error(req, movieid)
    if error is not None:
        return jsonify({'error': error}), 400
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            return make_response(jsonify({"error": "Movie ID already exists."}), 409)
    movies.append(req)
    write(movies)

    response = make_response(jsonify({'message': 'Movie added.'}), 201)
    return response


@app.route("/movies/<movieid>/<rate>", methods=['PUT'])
def update_movie_rating(movieid, rate):
    """Met à jour une note (200), ou retourne 400 si invalide et 404 si film absent."""
    try:
        rating = float(rate)
    except ValueError:
        return jsonify({'error': 'Movie rating must be a number between 0 and 10.'}), 400
    if not valid_rating(rating):
        return jsonify({'error': 'Movie rating must be a number between 0 and 10.'}), 400
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movie["rating"] = rating
            res = make_response(jsonify(movie), 200)
            write(movies)
            return res

    res = make_response(jsonify({"error": "Movie ID not found."}), 404)
    return res


@app.route("/movies/<movieid>", methods=['DELETE'])
def del_movie(movieid):
    """Supprime et retourne un film (200), ou une erreur si absent (404)."""
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movies.remove(movie)
            write(movies)
            return make_response(jsonify(movie), 200)

    res = make_response(jsonify({"error": "Movie ID not found."}), 404)
    return res


if __name__ == "__main__":
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
