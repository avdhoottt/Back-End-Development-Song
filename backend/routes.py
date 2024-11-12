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

mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
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
# GET ALL SONGS
######################################################################
@app.route("/song", methods=["GET"])
def songs():
    """
    Retrieve all songs from the MongoDB database
    Returns: List of all songs wrapped in a dictionary with HTTP 200
    """
    songs = list(db.songs.find({}, {'_id': False}))
    return jsonify({"songs": songs}), 200

######################################################################
# GET A SONG BY ID
######################################################################
@app.route("/song/<id>", methods=["GET"])
def get_song_by_id(id):
    """
    Retrieve a single song by its ID
    Args:
        id: The ID of the song to retrieve
    Returns:
        200: The song if found
        404: Error message if song not found
    """
    song = db.songs.find_one({"id": id}, {'_id': False})
    
    if not song:
        return {"message": "song with id not found"}, 404
    
    return jsonify(song), 200

######################################################################
# CREATE A SONG
######################################################################
@app.route("/song", methods=["POST"])
def create_song():
    """
    Create a new song
    Returns:
        201: Successfully created song with MongoDB ObjectId
        302: If song with ID already exists
    """
    song = request.get_json()
    
    existing_song = db.songs.find_one({"id": song["id"]})
    if existing_song:
        return {"Message": f"song with id {song['id']} already present"}, 302
    
    result = db.songs.insert_one(song)
    
    return jsonify({"inserted id": parse_json(result.inserted_id)}), 201

######################################################################
# UPDATE A SONG
######################################################################
@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """
    Update a song by ID
    Args:
        id: The ID of the song to update
    Returns:
        201: Successfully updated song
        200: Song found but no changes made
        404: Song not found
    """
    update_data = request.get_json()
    update_data['id'] = id
    
    existing_song = db.songs.find_one({"id": id})
    if not existing_song:
        return {"message": "song not found"}, 404
    
    result = db.songs.update_one(
        {"id": id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        updated_song = db.songs.find_one({"id": id})
        return jsonify(parse_json(updated_song)), 201
    
    return {"message": "song found, but nothing updated"}, 200

######################################################################
# DELETE A SONG
######################################################################
@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """
    Delete a song by ID
    Args:
        id: The ID of the song to delete
    Returns:
        204: Successfully deleted
        404: Song not found
    """
    # Delete the song from database
    result = db.songs.delete_one({"id": id})
    
    # Check if song was found and deleted
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    
    # Return empty response with 204 status
    return "", 204
