import json


def movies(_, info):
    with open('{}/data/movies.json'.format("."), "r") as file:
        movies = json.load(file)
        return movies['movies']


def movie_with_id(_, info, _id):
    with open('{}/data/movies.json'.format("."), "r") as file:
        movies = json.load(file)
        for movie in movies['movies']:
            if movie['id'] == _id:
                return movie


def movie_by_title(_, info, title):
    if not title.strip():
        raise ValueError('A non-empty title is required.')

    with open('{}/data/movies.json'.format("."), "r") as file:
        movies = json.load(file)
        for movie in movies['movies']:
            if movie['title'] == title:
                return movie


def add_movie(_, info, _id, title, director, rating):
    if not title.strip():
        raise ValueError('A non-empty title is required.')
    if rating < 0 or rating > 10:
        raise ValueError('Movie rating must be a number between 0 and 10.')

    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                raise ValueError('Movie ID already exists.')

        newmovie = {
            'id': _id,
            'title': title,
            'director': director,
            'rating': rating
        }
        movies['movies'].append(newmovie)

    with open('{}/data/movies.json'.format("."), "w") as wfile:
        json.dump(movies, wfile, indent=2)
    return newmovie


def resolve_actors_in_movie(movie, info):
    with open('{}/data/actors.json'.format("."), "r") as file:
        actors = json.load(file)
        result = [actor for actor in actors['actors'] if movie['id'] in actor['films']]
        return result


def update_movie_rate(_, info, _id, _rate):
    if _rate < 0 or _rate > 10:
        raise ValueError('Movie rating must be a number between 0 and 10.')

    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                movie['rating'] = _rate
                with open('{}/data/movies.json'.format("."), "w") as wfile:
                    json.dump(movies, wfile, indent=2)
                return movie
    raise ValueError('Movie ID not found.')


def delete_movie(_, info, _id):
    with open('{}/data/movies.json'.format("."), "r") as rfile:
        movies = json.load(rfile)
        for movie in movies['movies']:
            if movie['id'] == _id:
                movies['movies'].remove(movie)
                with open('{}/data/movies.json'.format("."), "w") as wfile:
                    json.dump(movies, wfile, indent=2)
                return movie
    raise ValueError('Movie ID not found.')
