import json
import os

import requests

MOVIE_URL = os.environ.get('MOVIE_URL', 'http://localhost:3200/graphql')

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


def get_movie(movieid):
    """Récupère un film auprès du service Movie via une requête GraphQL."""
    response = requests.post(MOVIE_URL, json={'query': MOVIE_QUERY, 'variables': {'id': movieid}})
    response.raise_for_status()
    return response.json()['data']['movie_with_id']


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
        raise ValueError('A non-empty userid is required.')
    if get_movie(movieid) is None:
        raise ValueError('Movie ID not found.')

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
        raise ValueError('This booking already exists.')
    date_booking['movies'].append(movieid)

    with open('{}/data/bookings.json'.format("."), "w") as wfile:
        json.dump(bookings, wfile)
    return user_booking


def delete_booking(_, info, userid):
    with open('{}/data/bookings.json'.format("."), "r") as rfile:
        bookings = json.load(rfile)
        for booking in bookings['bookings']:
            if booking['userid'] == userid:
                bookings['bookings'].remove(booking)
                with open('{}/data/bookings.json'.format("."), "w") as wfile:
                    json.dump(bookings, wfile)
                return booking


def resolve_movies_details(date_booking, info):
    return [get_movie(movieid) for movieid in date_booking['movies']]
