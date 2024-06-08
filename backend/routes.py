from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

######################################################################
# RETURN HEALTH OF THE APP
######################################################################


@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200


######################################################################
# COUNT THE NUMBER OF SONGS
######################################################################


@app.route("/count")
def count():
    """Return the number of documents."""
    try:
        count = db.songs.count_documents({})
        return jsonify(count=count), 200
    except Exception as e:
        # Log the exception for debugging
        app.logger.error(f"Error counting documents: {e}")
        return jsonify(message="Internal server error"), 500

@app.route("/song")
def songs():
   """Return All documents."""
   try:
        songs_cursor = db.songs.find({})
        # Convert cursor to list of dictionaries and then serialize
        songs_list = [song for song in songs_cursor]
        json_docs = json_util.dumps(songs_list)
        return json_docs, 200
   except Exception as e:
       # Log the exception for debugging
       app.logger.error(f"Error give all documents: {e}")
       return jsonify(message=f"Internal server error {e}"), 500

@app.route("/song/<int:id>")  # Use id for clarity
def get_song(id):
    """Return the song document matching the given ID."""
    try:
        song = db.songs.find_one({"id": id})
        if song:
            song_json = json_util.dumps(song)
            return song_json, 200
        else:
            return jsonify(message="Song not found"), 404
    except Exception as e:
        app.logger.error(f"Error retrieving song with ID {song_id}: {e}")
        return jsonify(message="Internal server error"), 500

@app.route("/song", methods=["POST"])
def insert_song():
    """Return INSERT documents."""
    try:
        # 1. Get JSON data from the request and convert it into a dictionary:
        data = request.get_json()

        # 2. Validate if all required data is present:
        required_keys = ['id', 'lyrics', 'title']
        if not all(key in data for key in required_keys):
            return jsonify(message="Missing required fields"), 400

        # 3. Valid exist id
        if db.songs.count_documents({"id": data["id"]}):
            return jsonify(message=f"song with id {data['id']} already present"), 302

        # 4. Insert song into MongoDB
        result = db.songs.insert_one(data)

        # 5. Return the result with success code 201
        return jsonify(message="Song inserted successfully", inserted_id=str(result.inserted_id)), 201

    except Exception as e:
        app.logger.error(f"Error inserting song: {e}")
        return jsonify(message="Internal server error"), 500

@app.route('/song/<int:id>', methods=['PUT'])
def update_song(id):
    """Updates a song by ID.

    Expects JSON data in the request body with 'title' and 'lyrics' fields.
    """

    try:
        new_data = request.get_json()

        if not new_data or "title" not in new_data or "lyrics" not in new_data:
            return jsonify({"error": "Invalid song data"}), 400  # Bad Request

        # Find and update the song
        result = db.songs.update_one(
            {"id": id}, 
            {"$set": new_data}
        )

        if result.modified_count > 0:
            # Construct a custom response with the updated song data
            updated_song = db.songs.find_one({"id": id})  # Fetch the updated song
            return json_util.dumps(updated_song), 200  # Use json_util for serialization
        else:
            return jsonify({"message": "Song not found"}), 404

    except Exception as e:
        # Handle any unexpected errors gracefully
        return jsonify({"error": "Internal server error", "details": str(e)}), 500



@app.route('/song/<int:id>', methods=['DELETE'])
def DELETE_song(id):
    """Delete a song by ID."""

    try:
        # 1. Search document by ID (usando count_documents)
        if db.songs.count_documents({"id": id}) > 0: 
            # Delete the song and return 204 No Content
            db.songs.delete_one({"id": id})  # También cambié remove por delete_one
            return jsonify(), 204
        else:
            # Song not found, return 404 Not Found
            return jsonify({"message": "Song not found"}), 404

    except Exception as e:
        # Handle any unexpected errors
        return jsonify({"error": "Internal server error", "details": str(e)}), 500