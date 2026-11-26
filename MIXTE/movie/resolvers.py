import json
from pathlib import Path

from flask_jwt_extended import get_jwt, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from graphql import GraphQLError
from jwt.exceptions import PyJWTError

MOVIES_PATH = Path(__file__).resolve().parent / 'data' / 'movies.json'
ACTORS_PATH = Path(__file__).resolve().parent / 'data' / 'actors.json'


def movie_error(message, code):
    """Erreur GraphQL avec un code machine dans 'extensions' (BAD_REQUEST, NOT_FOUND, CONFLICT,
    UNAUTHENTICATED, FORBIDDEN), pour que les clients n'aient pas à analyser le texte du message."""
    return GraphQLError(message, extensions={'code': code})


def get_claims():
    """Vérifie le token JWT de la requête (en-tête ou cookie) et renvoie son contenu,
    ou None si le token est absent, invalide ou expiré."""
    try:
        verify_jwt_in_request()
    except (JWTExtendedException, PyJWTError):
        return None
    return get_jwt()


def check_admin():
    """Lève une erreur si l'appelant n'est pas connecté (UNAUTHENTICATED) ou n'est pas admin (FORBIDDEN)."""
    claims = get_claims()
    if claims is None:
        raise movie_error('Authentication required.', 'UNAUTHENTICATED')
    # Si le champ "admin" n'est pas dans le token, l'utilisateur n'est pas admin
    if not claims.get('admin', False):
        raise movie_error('Admin rights required.', 'FORBIDDEN')


def movies(_, info):
    with MOVIES_PATH.open(encoding='utf-8') as file:
        movies = json.load(file)
        return movies['movies']


def movie_with_id(_, info, _id):
    with MOVIES_PATH.open(encoding='utf-8') as file:
        movies = json.load(file)
        for movie in movies['movies']:
            if movie['id'] == _id:
                return movie


def movie_by_title(_, info, title):
    if not title.strip():
        raise movie_error('A non-empty title is required.', 'BAD_REQUEST')

    with MOVIES_PATH.open(encoding='utf-8') as file:
        movies = json.load(file)
        for movie in movies['movies']:
            if movie['title'] == title:
                return movie


def add_movie(_, info, _id, title, director, rating):
    check_admin()
    if not title.strip():
        raise movie_error('A non-empty title is required.', 'BAD_REQUEST')
    if rating < 0 or rating > 10:
        raise movie_error('Movie rating must be a number between 0 and 10.', 'BAD_REQUEST')

    with MOVIES_PATH.open(encoding='utf-8') as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                raise movie_error('Movie ID already exists.', 'CONFLICT')

        newmovie = {
            'id': _id,
            'title': title,
            'director': director,
            'rating': rating
        }
        movies['movies'].append(newmovie)

    with MOVIES_PATH.open('w', encoding='utf-8') as wfile:
        json.dump(movies, wfile, indent=2)
    return newmovie


def resolve_actors_in_movie(movie, info):
    with ACTORS_PATH.open(encoding='utf-8') as file:
        actors = json.load(file)
        result = [actor for actor in actors['actors'] if movie['id'] in actor['films']]
        return result


def update_movie_rate(_, info, _id, _rate):
    check_admin()
    if _rate < 0 or _rate > 10:
        raise movie_error('Movie rating must be a number between 0 and 10.', 'BAD_REQUEST')

    with MOVIES_PATH.open(encoding='utf-8') as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                movie['rating'] = _rate
                with MOVIES_PATH.open('w', encoding='utf-8') as wfile:
                    json.dump(movies, wfile, indent=2)
                return movie
    raise movie_error('Movie ID not found.', 'NOT_FOUND')


def delete_movie(_, info, _id):
    check_admin()
    with MOVIES_PATH.open(encoding='utf-8') as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                movies['movies'].remove(movie)
                with MOVIES_PATH.open('w', encoding='utf-8') as wfile:
                    json.dump(movies, wfile, indent=2)
                return movie
    raise movie_error('Movie ID not found.', 'NOT_FOUND')
