from ariadne import graphql_sync, make_executable_schema, load_schema_from_path, ObjectType, QueryType, MutationType
from flask import Flask, make_response, request, jsonify
from flask_jwt_extended import JWTManager

import os
from datetime import timedelta
from pathlib import Path

import resolvers as r

PORT = 3201
HOST = '0.0.0.0'
app = Flask(__name__)

# Initialisation de la partie JWT (même secret dans les 4 services, défini dans le .env)
app.config["JWT_SECRET_KEY"] = os.environ.get('JWT_SECRET', 'dev-secret-change-me')
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=1)
jwt = JWTManager(app)

type_defs = load_schema_from_path(str(Path(__file__).resolve().parent / 'booking.graphql'))
query = QueryType()
query.set_field('bookings', r.bookings)
query.set_field('booking_by_user', r.booking_by_user)

mutation = MutationType()
mutation.set_field('add_booking', r.add_booking)
mutation.set_field('delete_booking', r.delete_booking)
mutation.set_field('delete_booking_movie', r.delete_booking_movie)

date_booking = ObjectType('DateBooking')
date_booking.set_field('movies_details', r.resolve_movies_details)

schema = make_executable_schema(type_defs, date_booking, query, mutation)


# root message
@app.route("/", methods=['GET'])
def home():
    return make_response("<h1 style='color:blue'>Welcome to the Booking service!</h1>",200)


# graphql entry points
@app.route('/graphql', methods=['POST'])
def graphql_server():
    data = request.get_json()
    success, result = graphql_sync(
                        schema,
                        data,
                        context_value=None,
                        debug=app.debug
                    )
    status_code = 200 if success else 400
    return jsonify(result), status_code


if __name__ == "__main__":
    print("Server running in port %s"%(PORT))
    app.run(host=HOST, port=PORT)
