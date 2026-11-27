import json
import os
from pathlib import Path

import requests
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException
from graphql import GraphQLError
from jwt.exceptions import PyJWTError

MOVIE_URL = os.environ.get('MOVIE_URL', 'http://localhost:3200/graphql')
SCHEDULE_URL = os.environ.get('SCHEDULE_URL', 'http://localhost:3202')
TIMEOUT = 5

BOOKINGS_PATH = Path(__file__).resolve().parent / 'data' / 'bookings.json'

MOVIE_QUERY = """
query($id: String!) {
    movie_with_id(_id: $id) {
        id
        title
        director
        rating
    }
}
"""


def booking_error(message, code):
    """Erreur GraphQL avec un code machine dans 'extensions' (BAD_REQUEST, NOT_FOUND, CONFLICT,
    SERVICE_UNAVAILABLE), pour que les clients n'aient pas à analyser le texte du message."""
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
        raise booking_error('Authentication required.', 'UNAUTHENTICATED')
    # Si le champ "admin" n'est pas dans le token, l'utilisateur n'est pas admin
    if not claims.get('admin', False):
        raise booking_error('Admin rights required.', 'FORBIDDEN')


def check_self_or_admin(userid):
    """Lève une erreur si l'appelant n'est pas connecté, ou s'il n'est ni `userid` ni admin."""
    claims = get_claims()
    if claims is None:
        raise booking_error('Authentication required.', 'UNAUTHENTICATED')
    if get_jwt_identity() != userid and not claims.get('admin', False):
        raise booking_error('You can only access your own bookings.', 'FORBIDDEN')


def get_movie(movieid):
    """Récupère un film auprès du service Movie via une requête GraphQL (None si inconnu)."""
    try:
        response = requests.post(MOVIE_URL, json={'query': MOVIE_QUERY, 'variables': {'id': movieid}},
                                 timeout=TIMEOUT)
        response.raise_for_status()
        return response.json()['data']['movie_with_id']
    except (requests.RequestException, ValueError, KeyError, TypeError):
        raise booking_error('Movie service unavailable.', 'SERVICE_UNAVAILABLE')


def get_scheduled_movies(date):
    """Renvoie la liste des films programmés à une date (service Schedule, REST), ou [] si la date est inconnue."""
    try:
        response = requests.get('{}/schedule/{}'.format(SCHEDULE_URL, date), timeout=TIMEOUT)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return response.json()['movies']
    except (requests.RequestException, ValueError, KeyError):
        raise booking_error('Schedule service unavailable.', 'SERVICE_UNAVAILABLE')


def bookings(_, info):
    check_admin()
    with BOOKINGS_PATH.open(encoding='utf-8') as file:
        bookings = json.load(file)
        return bookings['bookings']


def booking_by_user(_, info, userid):
    check_self_or_admin(userid)
    with BOOKINGS_PATH.open(encoding='utf-8') as file:
        bookings = json.load(file)
        for booking in bookings['bookings']:
            if booking['userid'] == userid:
                return booking


def add_booking(_, info, userid, date, movieid):
    check_self_or_admin(userid)
    if not userid.strip():
        raise booking_error('A non-empty userid is required.', 'BAD_REQUEST')
    if get_movie(movieid) is None:
        raise booking_error('Movie ID not found.', 'BAD_REQUEST')
    if movieid not in get_scheduled_movies(date):
        raise booking_error('This movie is not scheduled on this date.', 'BAD_REQUEST')

    with BOOKINGS_PATH.open(encoding='utf-8') as rfile:
        bookings = json.load(rfile)

    # Recherche des réservations de l'utilisateur (création si absentes)
    user_booking = None
    for booking in bookings['bookings']:
        if booking['userid'] == userid:
            user_booking = booking
            break
    if user_booking is None:
        user_booking = {'userid': userid, 'dates': []}
        bookings['bookings'].append(user_booking)

    # Recherche de la date dans ses réservations (création si absente)
    date_booking = None
    for day in user_booking['dates']:
        if day['date'] == date:
            date_booking = day
            break
    if date_booking is None:
        date_booking = {'date': date, 'movies': []}
        user_booking['dates'].append(date_booking)

    if movieid in date_booking['movies']:
        raise booking_error('This booking already exists.', 'CONFLICT')
    date_booking['movies'].append(movieid)

    with BOOKINGS_PATH.open('w', encoding='utf-8') as wfile:
        json.dump(bookings, wfile, indent=2)
    return user_booking


def delete_booking(_, info, userid):
    check_self_or_admin(userid)
    with BOOKINGS_PATH.open(encoding='utf-8') as rfile:
        bookings = json.load(rfile)
        for booking in bookings['bookings']:
            if booking['userid'] == userid:
                bookings['bookings'].remove(booking)
                with BOOKINGS_PATH.open('w', encoding='utf-8') as wfile:
                    json.dump(bookings, wfile, indent=2)
                return booking
    raise booking_error('No booking found for this user.', 'NOT_FOUND')


def delete_booking_movie(_, info, userid, date, movieid):
    """Retire une seule réservation (un film à une date). Les dates vides, puis l'utilisateur sans
    réservation, sont retirés du fichier. Renvoie la réservation mise à jour de l'utilisateur."""
    check_self_or_admin(userid)
    with BOOKINGS_PATH.open(encoding='utf-8') as rfile:
        bookings = json.load(rfile)

    # Recherche des réservations de l'utilisateur
    user_booking = None
    for booking in bookings['bookings']:
        if booking['userid'] == userid:
            user_booking = booking
            break

    # Recherche de la date dans ses réservations
    date_booking = None
    if user_booking is not None:
        for day in user_booking['dates']:
            if day['date'] == date:
                date_booking = day
                break
    if date_booking is None or movieid not in date_booking['movies']:
        raise booking_error('This booking does not exist.', 'NOT_FOUND')

    date_booking['movies'].remove(movieid)
    if not date_booking['movies']:
        user_booking['dates'].remove(date_booking)
    if not user_booking['dates']:
        bookings['bookings'].remove(user_booking)

    with BOOKINGS_PATH.open('w', encoding='utf-8') as wfile:
        json.dump(bookings, wfile, indent=2)
    return user_booking


def resolve_movies_details(date_booking, info):
    return [get_movie(movieid) for movieid in date_booking['movies']]
