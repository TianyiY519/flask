import os

from flask import Blueprint
from flask.json import jsonify
from flask import request
from collections import OrderedDict
import json
import requests

movies = Blueprint('movies', __name__)  # pylint: disable=C0103

API_KEY = os.environ['API_KEY']

genres_data = {'28': "Action", '12': "Adventure", '16': "Animation", '35': "Comedy", '80': "Crime", '99': "Documentary",
        '18': "Drama", '10751': "Family", '14': "Fantasy", '36': "History", '27': "Horror", '10402': "Music",
        '9648': "Mystery", '10749': "Romance", '878': "Science Fiction", '10770': "TV Movie", '53': "Thriller",
        '10752': "War", '37': "Western"}
sorting_keys = ['original_title', 'release_date', 'vote_average:']


def handle_broken_image_url(j_data):
    if 'results' in j_data:
        for i in j_data['results']:
            if 'backdrop_path' in i and i['backdrop_path'] is not None:
                i['backdrop_path'] = f'https://image.tmdb.org/t/p/w500{i["backdrop_path"]}'
            if 'poster_path' in i and i['poster_path'] is not None:
                i['poster_path'] = f'https://image.tmdb.org/t/p/w500{i["poster_path"]}'
    else:
        if 'poster_path' in j_data and j_data['poster_path'] is not None:
            j_data['poster_path'] = f'https://image.tmdb.org/t/p/w500{j_data["poster_path"]}'


def translate_genre_id_to_name(j_data):
    for i in j_data['results']:
        i['genre_ids'] = [genres_data[str(j)] for j in i['genre_ids']]

@movies.route('search', methods=['GET'])
def get_movies():
    # query_parameters = dict(request.args)
    # query_parameters['api_key'] = API_KEY
    # response = requests.get('https://api.themoviedb.org/3/search/movie', params=query_parameters)
    # if response.status_code == 200:
    #     json_response = response.json()
    #     ls = []
    #     for i in json_response['results']:
    #         i['backdrop_path'] = f'https://image.tmdb.org/t/p/w500{i["backdrop_path"]}' if i['backdrop_path'] is not None else None
    #         i['poster_path'] = f'https://image.tmdb.org/t/p/w500{i["poster_path"]}' if i['poster_path'] is not None else None
    #         i['genre_ids'] = [genres_data[str(j)] for j in i['genre_ids']]
    #         ls.append(i)
    #     json_response['results'] = ls
    #     return jsonify(json_response)
    # else:
    #     return jsonify(success=False, ), response.status_code
    requested_page = int(request.args.get('page', 1))
    requested_page_0 = requested_page - 1
    sort = request.args.get('sort')
    args = OrderedDict(api_key=API_KEY)
    for k, v in request.args.items():
        if k == 'page':
            continue
        elif k == 'sort':
            continue
        elif k == 'api_key':
            continue
        args[k] = v

    # sorting page
    _parts = []  # to keep all sorting keys, with leading +/-, "+" indicates ascending, "-" indicates descending.
    _ratios = []  # to keep +1/-1
    if sort is not None:
        for p in sort.split(','):
            _p = p.strip('-+')
            if _p not in sorting_keys:  # skip invalid sorting keys
                continue
            if p.startswith('-'):  # descending
                _parts.append(p)
                _ratios.append(-1)
            else:  # ascending
                _parts.append(f'+{_p}')
                _ratios.append(1)

    def get_data(_args):
        r = requests.get('https://api.themoviedb.org/3/search/movie', params=_args)
        print(r.request.url)
        return r

    if len(_parts) == 0:
        args['page'] = requested_page
        response = get_data(args)
        json_data = response.json()
        handle_broken_image_url(json_data)
        translate_genre_id_to_name(json_data)
        return jsonify(json_data), response.status_code

    page = 0
    total_pages = 1
    total_results = 0
    per_page = 1
    all_results = []

    while page < total_pages:
        page += 1
        args['page'] = page
        response = get_data(args)
        if response.status_code == 200:
            json_response = response.json()
            if page == 1:
                total_pages = json_response['total_pages']
                total_results = json_response['total_results']
                per_page = len(json_response['results'])

            handle_broken_image_url(json_response)
            translate_genre_id_to_name(json_response)
            all_results.extend(json_response['results'])

        else:
            return jsonify(response.json()), response.status_code

    # the following codes turn sort of each key into number
    for r, p in enumerate(_parts):
        all_values = [item[p[1:]] for item in all_results]
        all_values = sorted(list(set(all_values)))  # all unique values on ascending order

        for item in all_results:
            item[p] = all_values.index(item[p[1:]]) * _ratios[r]  # mark the above sorting with number

    # sort according to all sorting keys
    all_results = sorted(all_results, key=lambda x: [x[_] for _ in _parts])

    # slice the results by per_page and user requested page no.
    results = all_results[requested_page_0 * per_page:requested_page * per_page]

    # get rid of extra fields
    [item.pop(p) for item in results for p in _parts]

    return jsonify(page=requested_page, results=results, total_pages=total_pages, total_results=total_results, )

@movies.route('<string:movie_id>/details', methods=['GET'])
def get_movie(movie_id):
    query_parameters = dict(request.args)
    query_parameters['api_key'] = API_KEY
    response = requests.get('https://api.themoviedb.org/3/movie/{}'.format(movie_id), params=query_parameters)

    json_response = response.json()
    return jsonify(json_response)

@movies.route('<string:movie_id>/rating', methods=['GET'])
def rate_movie(movie_id):
    """
    the doc:
    https://developers.themoviedb.org/3/movies/rate-movie
    """
    query_parameters = dict(request.args)
    query_parameters['api_key'] = API_KEY
    try:
        value = query_parameters.pop('value')
    except KeyError:
        return jsonify(success=False, error_msg='pleas pass your rating'), 400

    try:
        value = float(value)
    except (TypeError, ValueError):
        return jsonify(success=False, error_msg='rating expected as number'), 400

    response = requests.post('https://api.themoviedb.org/3/movie/{}/rating'.format(movie_id), params=query_parameters,
                             json={'value': value})
    json_response = response.json()
    return jsonify(json_response), response.status_code



