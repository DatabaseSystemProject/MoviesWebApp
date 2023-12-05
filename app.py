'''
Database System Design Project Demo Using MongoDB Atlas
Members:
Carlos Sac
Senait Gebreamlak
'''
from flask import Flask, abort, request, render_template, session
from flask import redirect, make_response, jsonify
from functools import wraps
import os

from flask_restful import Resource, Api
from flask_jwt_extended import create_access_token
from flask_jwt_extended import jwt_required, verify_jwt_in_request
from flask_jwt_extended import JWTManager, get_jwt_identity, get_jwt
from flask_jwt_extended import set_access_cookies

#imported for mongodb
from dotenv import load_dotenv 
from flask import Flask, render_template, request
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

# access your MongoDB Atlas cluster
load_dotenv()
connection_string: str = os.environ.get("CONNECTION_STRING")
mongo_client: MongoClient = MongoClient(connection_string)

database: Database = mongo_client.get_database('MoviesWebApp')
user_collection: Collection = database.get_collection('users')
movies_collection: Collection = database.get_collection('movies')

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "secretkey"
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False
jwt = JWTManager(app)
jwt.init_app(app)
app = Flask(__name__)
app.secret_key = "secretkey"
app.config["UPLOADED_PHOTOS_DEST"] = "static"
app.config["JWT_SECRET_KEY"] = "secretkey"
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False
app.config["JWT_COOKIE_CSRF_PROTECT"] = False

jwt = JWTManager(app)
jwt.init_app(app)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()

        # Query the 'users' collection for a user with the same 'sub' claim
        user = user_collection.find_one({'username': claims['sub']})

        if user is None:
            abort(404, description='User not found')
        elif user['role'] != 'admin':
            abort(403, description='Admins only')
        else:
            return fn(*args, **kwargs)

    return wrapper


def checkUser(username, password):
    # Query the 'users' collection for a user with the same username and password
    user = user_collection.find_one({'username': username, 'password': password})

    if user is not None:
        print(user)
        return {"username": user["username"], "role": user["role"]}
    return None


@app.route("/", methods=["GET"])
def firstRoute():
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        validUser = checkUser(username, password)
        if validUser != None:
            # set JWT token

            user_claims = {"role": validUser["role"]}
            #access_token = create_access_token(username, user_claims=user_claims)
            access_token = create_access_token(username, user_claims)
            all_movies = list(movies_collection.find({}))
            response = make_response(
                render_template(
                    
                    "index.html", title="movies", username=username, movies=all_movies
                )
            )
            response.status_code = 200
            # add jwt-token to response headers
            # response.headers.extend({"jwt-token": access_token})
            set_access_cookies(response, access_token)
            return response

    return render_template("register.html")


@app.route("/logout")
def logout():
    # invalidate the JWT token

    return "Logged Out of My Movies"


@app.route("/movies", methods=["GET"])
@jwt_required()
def getMovies():
    try:
        username = get_jwt_identity()
        all_movies = list(movies_collection.find({}))

        return render_template("movies.html", username=username, movies=all_movies)
    except:
        return render_template("register.html")


@app.route("/addmovie", methods=["GET", "POST"])
@jwt_required()
@admin_required
def addMovie():
    username = get_jwt_identity()
    if request.method == "GET":
        return render_template("addMovie.html", username=username)
    if request.method == "POST":
        # expects pure json with quotes everywhere
        title = request.form.get("title")
        year = request.form.get("year")

        # Find the movie with the highest id
        last_movie = movies_collection.find_one(sort=[("id", -1)])

        # If there are no movies in the collection, start with id 0
        if last_movie is None:
            next_id = 0
        else:
            next_id = last_movie["id"] + 1

        # Insert the new movie into the 'movies' collection
        newmovie = {"id": next_id, "title": title, "year": year}
        movies_collection.insert_one(newmovie)

        # Get all movies from the 'movies' collection
        all_movies = list(movies_collection.find({}))

        return render_template(
            "movies.html", movies=all_movies, username=username, title="movies"
        )
    else:
        return 400

@app.route("/addimage", methods=["GET", "POST"])
@jwt_required()
@admin_required
def addimage():
    if request.method == "GET":
        return render_template("addimage.html")
    elif request.method == "POST":
        image = request.files["image"]
        id = request.form.get("number")  # use id to number the image
        imagename = "image_" + id + ".png"
        image.save(os.path.join(app.config["UPLOADED_PHOTOS_DEST"], imagename))
        print(image.filename)
        return "image loaded"

    return "all done"

# Error Handling 403
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html', message=e.description), 403

# Error Handling 404
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html', message=e.description), 404

if __name__ == "__main__":
    #app.run(debug=True, host="0.0.0.0", port=5000)
    app.run(debug=True, host="127.0.0.1", port=5000)
