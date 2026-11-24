import json
import os

import requests
from graphql import GraphQLError

MOVIE_URL = os.environ.get('MOVIE_URL', 'http://localhost:3200/graphql')
SCHEDULE_URL = os.environ.get('SCHEDULE_URL', 'http://localhost:3202')
TIMEOUT = 5

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
    with open('{}/data/bookings.json'.format("."), "r") as file:
        bookings = json.load(file)
        return bookings['bookings']


def booking_by_user(_, info, userid):
    with open('{}/data/bookings.json'.format("."), "r") as file:
        bookings = json.load(file)
        for booking in bookings['bookings']:
            if booking['userid'] == userid:
                return booking


def add_booking(_, info, userid, date, movieid):
    if not userid.strip():
        raise booking_error('A non-empty userid is required.', 'BAD_REQUEST')
    if get_movie(movieid) is None:
        raise booking_error('Movie ID not found.', 'BAD_REQUEST')
    if movieid not in get_scheduled_movies(date):
        raise booking_error('This movie is not scheduled on this date.', 'BAD_REQUEST')

    with open('{}/data/bookings.json'.format("."), "r") as rfile:
        bookings = json.load(rfile)

    user_booking = next((b for b in bookings['bookings'] if b['userid'] == userid), None)
    if user_booking is None:
        user_booking = {'userid': userid, 'dates': []}
        bookings['bookings'].append(user_booking)

    date_booking = next((d for d in user_booking['dates'] if d['date'] == date), None)
    if date_booking is None:
        date_booking = {'date': date, 'movies': []}
        user_booking['dates'].append(date_booking)

    if movieid in date_booking['movies']:
        raise booking_error('This booking already exists.', 'CONFLICT')
    date_booking['movies'].append(movieid)

    with open('{}/data/bookings.json'.format("."), "w") as wfile:
        json.dump(bookings, wfile, indent=2)
    return user_booking


def delete_booking(_, info, userid):
    with open('{}/data/bookings.json'.format("."), "r") as rfile:
        bookings = json.load(rfile)
        for booking in bookings['bookings']:
            if booking['userid'] == userid:
                bookings['bookings'].remove(booking)
                with open('{}/data/bookings.json'.format("."), "w") as wfile:
                    json.dump(bookings, wfile, indent=2)
                return booking
    raise booking_error('No booking found for this user.', 'NOT_FOUND')


def resolve_movies_details(date_booking, info):
    return [get_movie(movieid) for movieid in date_booking['movies']]
