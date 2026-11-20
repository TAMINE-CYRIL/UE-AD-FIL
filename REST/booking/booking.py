from flask import Flask, render_template, request, jsonify, make_response
import requests
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]

#schedule = requests.get("http://127.0.0.1:3202/schedule")
#movie = requests.get("http://127.0.0.1:3200/movies")


@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

@app.route("/booking", methods=['GET'])
def get_booking():
   return make_response(jsonify(bookings), 200)


@app.route("/booking/<userid>", methods=['GET'])
def get_booking_byuserid(userid):
   for booking in bookings:
      if str(booking["userid"]) == str(userid):
         return make_response(jsonify(booking), 200)
      
   return make_response(jsonify({"error" : "user not found."}),404)

@app.route("/booking/<userid>", methods=['POST'])
def add_booking(userid):
   for booking in bookings:
      if booking["userid"] == str(userid):
         return make_response(jsonify({"error" : "user already exists"}))

if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   print(app.url_map)
   app.run(host=HOST, port=PORT)
