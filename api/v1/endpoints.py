from flask import Blueprint, request, url_for, redirect, jsonify, current_app as app, render_template, current_app
from marshmallow import EXCLUDE, Schema, fields, ValidationError
from recommendation_engine.collaborative_filtering import UserBasedCF
from data.loader import load_data
from data.preprocessing import normalize_ratings
import numpy as np
import os
from functools import lru_cache, wraps
from models.models import Movie, Rating, User, initialize_model
from api.database import db
from api.utils import generate_confirmation_token, confirm_token, send_confirmation_email
from sqlalchemy.exc import IntegrityError
import logging
from dotenv import load_dotenv
from okta.client import Client as OktaClient
from okta.models.user import User as OktaUser
from okta.models.user_profile import UserProfile
from okta.models.user_credentials import UserCredentials
from okta.models.password_credential import PasswordCredential
from datetime import datetime
from flask_oidc import OpenIDConnect
import aiohttp
import asyncio
from typing import Union, Tuple
from okta.errors.okta_api_error import OktaAPIError
from jose import jwt, JWTError
from urllib.parse import urlencode
from api.extensions import bcrypt
from sqlalchemy.exc import SQLAlchemyError
from flask_login import current_user
from sqlalchemy import and_
from flask_login import login_required
from api.app import login_manager
from flask_login import login_user, logout_user, login_required, current_user
import requests
from sklearn.metrics.pairwise import cosine_similarity
from flask import flash


api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')
oidc = OpenIDConnect()


# Setup logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Get Okta configuration from environment variables
OKTA_ORG_URL = os.getenv("OKTA_ORG_URL")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET")
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID")
OKTA_API_TOKEN = os.getenv("OKTA_API_TOKEN")
API_KEY = os.getenv("API_KEY")


# Create the Okta Client configuration
config = {
    'orgUrl': OKTA_ORG_URL,
    'token': OKTA_CLIENT_SECRET,
    'clientId': OKTA_CLIENT_ID,
    'issuer': f'{OKTA_ORG_URL}/oauth2/default',
}
okta_client = OktaClient(config)  # Create the OktaClient instance


class MovieSchema(Schema):
    id = fields.Int()
    movie_id = fields.Int()
    title = fields.Str()
    genres = fields.Str()
    imdb_id = fields.Str()
    tmdb_id = fields.Str()

    class Meta:
        unknown = EXCLUDE


class PredictionRequestSchema(Schema):
    userId = fields.Integer(required=True)
    movieId = fields.Integer(required=True)

    class Meta:
        unknown = EXCLUDE


class RecommendationRequestSchema(Schema):
    userId = fields.Integer(required=True, validate=lambda val: val > 0)
    num_recommendations = fields.Int(required=True, validate=lambda n: n > 0)

    class Meta:
        unknown = EXCLUDE


class MovieDetailsSchema(Schema):
    movie_id = fields.Int(required=True)
    title = fields.Str()
    genres = fields.Str()
    imdb_id = fields.Str(allow_none=True)
    tmdb_id = fields.Str(allow_none=True)
    average_rating = fields.Float(allow_none=True)

    class Meta:
        unknown = EXCLUDE


class RatingSchema(Schema):
    userId = fields.Int(required=True)
    movieId = fields.Int(required=True)
    rating = fields.Float(required=True, validate=lambda val: 1 <= val <= 5)

    class Meta:
        unknown = EXCLUDE


class UserSchema(Schema):
    id = fields.Int(required=True)
    email = fields.Email(required=True)
    password = fields.Str(required=True)
    firstName = fields.Str()
    lastName = fields.Str()
    genres = fields.List(fields.Str())
    ratings = fields.Dict(keys=fields.Int(), values=fields.Float())

    class Meta:
        unknown = EXCLUDE


class OnboardingSchema(Schema):
    id = fields.Integer(required=True)
    genres = fields.List(fields.String(), required=True)
    ratings = fields.Dict(
        keys=fields.Integer(),
        values=fields.Float(),
        required=True)

    class Meta:
        unknown = EXCLUDE


@lru_cache(maxsize=1)
def get_ratings_matrix():
    ratings = load_data()
    normalized_ratings = normalize_ratings(ratings)
    ratings_matrix = normalized_ratings.fillna(0).values
    return ratings_matrix


def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        if not provided_key or provided_key != os.getenv('API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return view_function(*args, **kwargs)
    return decorated_function


@api_v1.route('/')
def index():
    try:
        return render_template('index.html')
    except TemplateNotFound:
        return jsonify({"error": "Template not found"}), 500


@api_v1.route('/predict', methods=['POST'])
@require_api_key
def predict(user_id=None, movie_id=None):
    model_instance = current_app.config.get('MODEL_INSTANCE')
    if user_id is None or movie_id is None:
        try:
            data = PredictionRequestSchema().load(request.json)
            user_id = data['userId']
            movie_id = data['movieId']
        except ValidationError as err:
            return jsonify(err.messages), 400

    if user_id <= 0 or movie_id <= 0:
        return jsonify(
            {'error': 'User ID and Movie ID must be positive integers'}), 400

    ratings_matrix = get_ratings_matrix()

    if user_id > ratings_matrix.shape[0] or movie_id > ratings_matrix.shape[1]:
        return jsonify({'error': 'User ID or Movie ID is out of bounds'}), 400

    try:
        prediction = model_instance.predict(user_id - 1, movie_id - 1)
        if np.isnan(prediction):
            prediction = None
        return prediction  # Return just the prediction value
    except Exception as e:
        raise Exception(f"Prediction error: {str(e)}")


@api_v1.route('/recommendations', methods=['POST'])
@require_api_key
def get_recommendations():
    logging.debug("Entering get_recommendations endpoint")

    model_instance, known_user_ids = current_app.config.get(
        'MODEL_INSTANCE'), current_app.config.get('KNOWN_USER_IDS')

    if model_instance is None or known_user_ids is None:
        logging.warning(
            "Recommendation model or known user IDs are not initialized.")
        return jsonify(
            {"error": "Recommendation model or known user IDs are not initialized."}), 500

    try:
        data = RecommendationRequestSchema().load(request.json)
    except ValidationError as err:
        logging.error(f"Validation error: {err.messages}")
        return jsonify(err.messages), 400

    logging.debug(f"Request data for recommendations: {data}")

    user_id = data["userId"]
    num_recommendations = request.json.get('num_recommendations', 10)

    logging.debug(f"Fetching user with ID: {user_id}")
    user = User.query.get(user_id)
    if not user:
        logging.error(f"User ID {user_id} not found")
        return jsonify({"error": "User not found"}), 404

    if user_id not in known_user_ids:
        logging.warning(
            f"User ID {user_id} is new and not in the known range.")
        return jsonify(
            {"error": "User is new and no recommendations available yet."}), 404

    preferred_genres = user.preferences.split(",") if user.preferences else []
    logging.debug(f"Preferred genres: {preferred_genres}")

    user_rated_movies = db.session.query(
        Rating.movie_id).filter_by(
        user_id=user_id).all()
    rated_movie_ids = [r[0] for r in user_rated_movies]

    logging.debug(f"User Rated movie IDs: {rated_movie_ids}")

    logging.debug("Fetching unrated movies based on user preferences")
    unrated_movies = (
        db.session.query(Movie) .filter(
            ~Movie.movie_id.in_(rated_movie_ids),
            Movie.genres.op("SIMILAR TO")(f"%{preferred_genres[0]}%") if preferred_genres else True,
        ) .all())

    top_recommendations_with_details = []
    logging.debug(f"Unrated movies count: {len(unrated_movies)}")
    for unrated_movie in unrated_movies:
        try:
            if user_id in model_instance.user_index and unrated_movie.movie_id in model_instance.movie_index:
                predicted_rating = model_instance.predict(
                    user_id, unrated_movie.movie_id)
                logging.debug(
                    f"Predicted rating for movie {unrated_movie.movie_id}: {predicted_rating}")
                if not np.isnan(predicted_rating):
                    movie_details = {
                        "movieId": unrated_movie.movie_id,
                        "title": unrated_movie.title,
                        "genres": unrated_movie.genres,
                        "predictedRating": float(predicted_rating)
                    }
                    top_recommendations_with_details.append(movie_details)
                else:
                    logging.warning(
                        f"Predicted rating for movie {unrated_movie.movie_id} is NaN. Skipping this movie.")
            else:
                logging.error(
                    f"User ID {user_id} or movie ID {unrated_movie.movie_id} out of range")
        except Exception as e:
            logging.error(
                f"Error processing movie {unrated_movie.movie_id}: {str(e)}")
            continue

    if not top_recommendations_with_details:
        logging.debug("No valid recommendations found.")
        return jsonify({"error": "No valid recommendations found."}), 404

    top_recommendations_with_details = sorted(
        top_recommendations_with_details,
        key=lambda x: x["predictedRating"],
        reverse=True)
    top_recommendations_with_details = top_recommendations_with_details[:num_recommendations]

    logging.debug(f"Top recommendations: {top_recommendations_with_details}")

    response = jsonify({'recommendations': top_recommendations_with_details})
    logging.debug(f"Response: {response.get_json()}")

    logging.debug("Exiting get_recommendations endpoint")

    return response


@api_v1.route('/movies', methods=['GET'])
def get_movies():
    try:
        # Get page number, default to 1
        page = request.args.get('page', 1, type=int)
        # Items per page, default to 10
        per_page = request.args.get('per_page', 10, type=int)

        movies = Movie.query.paginate(
            page=page, per_page=per_page, error_out=False)

        movie_schema = MovieSchema(many=True)
        # Serialize only the items for the current page
        result = movie_schema.dump(movies.items)

        # Add pagination information to the response
        return jsonify({
            'movies': result,
            'total': movies.total,
            'page': movies.page,
            'per_page': movies.per_page,
            'has_next': movies.has_next,
            'has_prev': movies.has_prev
        }), 200
    except SQLAlchemyError as e:
        return jsonify({'error': 'Database error'}), 500

    except ValidationError as e:
        return jsonify({'error': 'Validation error',
                       'details': e.messages}), 400

    except Exception as e:
        logging.exception('An error occurred while fetching movies')
        return jsonify({'error': str(e)}), 500


@api_v1.route('/movies/<int:movie_id>', methods=['GET'])
@require_api_key
def get_movie_details(movie_id):
    movie = Movie.query.filter_by(movie_id=movie_id).first()
    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    avg_rating = (
        db.session.query(db.func.avg(Rating.rating))
        .filter_by(movie_id=movie_id)
        .scalar()
    )

    movie_details = MovieDetailsSchema().dump({
        "movie_id": movie.movie_id,
        "title": movie.title,
        "genres": movie.genres,
        "imdb_id": movie.imdb_id,
        "tmdb_id": movie.tmdb_id,
        "average_rating": round(avg_rating, 2) if avg_rating is not None else None
    })
    return jsonify(movie_details), 200


@api_v1.route('/rate', methods=['POST'])
@require_api_key
def rate_movie():
    try:
        data = RatingSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400

    user_id = data['userId']
    movie_id = data['movieId']
    rating = data['rating']

    movie = Movie.query.filter_by(movie_id=movie_id).first()
    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    existing_rating = Rating.query.filter_by(
        user_id=user_id, movie_id=movie_id).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.timestamp = datetime.utcnow()
    else:
        new_rating = Rating(user_id=user_id, movie_id=movie_id, rating=rating)
        db.session.add(new_rating)

    db.session.commit()
    return jsonify({"message": "Rating updated/added successfully"}), 200


@api_v1.route('/similar/<int:movie_id>', methods=['GET'])
@require_api_key
def get_similar_movies(movie_id):
    try:
        ratings_matrix = get_ratings_matrix()
        model = app.config['MODEL']
        similar_items = model.get_similar_items(movie_id - 1)
        if not similar_items:
            return jsonify({"error": "No similar movies found"}), 400
        return jsonify(similar_items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_v1.route("/genres")
def get_genres():
    """
    Endpoint for getting the list of available genres.

    ---
    responses:
      200:
        description: A list of genres.
        schema:
          type: array
          items:
            type: string
    """
    all_genres = set()
    for movie in Movie.query.all():
        all_genres.update(movie.genres.split("|"))

    # Convert each genre to a dictionary with id and label
    genre_list = [{"id": genre, "label": genre}
                  for genre in sorted(list(all_genres))]

    return jsonify(genre_list)  # Return the list of genre dictionaries


@api_v1.route('/popular_movies')
@require_api_key
def get_popular_movies():
    try:
        count = request.args.get('count', 5, type=int)
        popular_movies = (
            db.session.query(
                Movie,
                db.func.avg(
                    Rating.rating).label('avg_rating'),
                db.func.count(
                    Rating.rating).label('num_ratings')) .join(
                Rating,
                Movie.movie_id == Rating.movie_id) .group_by(
                        Movie.movie_id,
                        Movie.id) .order_by(
                            db.desc('avg_rating'),
                db.desc('num_ratings')) .limit(count) .all())
        response = [{'movieId': movie.movie_id, 'title': movie.title}
                    for movie, _, _ in popular_movies]
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error getting popular movies: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


def get_authorization_url():
    authorization_url = f"{os.getenv('OKTA_ORG_URL')}/oauth2/v1/authorize"
    params = {
        "client_id": os.getenv('OKTA_CLIENT_ID'),
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": os.getenv('OKTA_REDIRECT_URI'),
        "state": "some_random_state",
    }
    return f"{authorization_url}?{urlencode(params)}"


async def exchange_code_for_token(code):
    token_url = f"{os.getenv('OKTA_ORG_URL')}/oauth2/v1/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv('OKTA_REDIRECT_URI'),
        "client_id": os.getenv('OKTA_CLIENT_ID'),
        "client_secret": os.getenv('OKTA_CLIENT_SECRET'),
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(token_url, headers=headers, data=data) as response:
            return await response.json()


@login_manager.user_loader
def load_user(user_id):
    """User loader callback for Flask-Login."""
    return User.query.get(int(user_id))


@api_v1.route("/signup", methods=["GET", "POST"])
async def signup():
    if request.method == "GET":
        return render_template("signup.html")

    if request.method == "POST":
        data = request.get_json()
        logging.debug(f"Received signup data: {data}")

        try:
            validated_data = UserSchema(
                only=["email", "password", "firstName", "lastName"]
            ).load(data)
            logging.debug(f"Validated data: {validated_data}")
        except ValidationError as err:
            logging.error(f"Validation error: {err.messages}")
            return jsonify(err.messages), 400

        email = validated_data["email"]
        password = validated_data["password"]
        first_name = validated_data["firstName"]
        last_name = validated_data["lastName"]

        # Check if user already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"error": "User already exists"}), 400

        hashed_password = bcrypt.generate_password_hash(
            password).decode('utf-8')
        new_user = User(
            email=email,
            password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            confirmed=False
        )
        db.session.add(new_user)
        db.session.commit()
        logging.debug(
            f"New user created in local database with ID: {new_user.id}")
        print("new user id", new_user.id)

        token = generate_confirmation_token(email)
        confirm_url = url_for(
            'api_v1.confirm_email',
            token=token,
            _external=True)
        send_confirmation_email(email, confirm_url)

        return jsonify(
            {"message": "Signup successful! Please check your email to confirm your registration.", "user_id": new_user.id}), 200


@api_v1.route('/confirm/<token>', methods=['GET'])
def confirm_email(token):
    try:
        email = confirm_token(token)
    except SignatureExpired:
        return render_template('expired_link.html')
    except BadTimeSignature:
        return render_template('invalid_link.html')

    user = User.query.filter_by(email=email).first_or_404()

    if user.confirmed:
        return render_template('already_confirmed.html'), 400
    else:
        user.confirmed = True
        user.confirmed_on = datetime.utcnow()
        db.session.add(user)
        db.session.commit()

        return redirect(url_for("api_v1.onboarding"))


@api_v1.route("/login", methods=["GET", "POST"])
def login():
    """Handles user login."""

    if request.method == "POST":
        email = request.json.get("email")
        password = request.json.get("password")

        if not email or not password:
            return jsonify({"success": False,
                            "error": "Email and password are required."})

        user = User.query.filter_by(email=email).first()
        if user:
            if bcrypt.check_password_hash(user.password, password):
                if user.confirmed:
                    login_user(user)
                    return jsonify(
                        {"success": True, "redirect_url": url_for("api_v1.dashboard_data")})
                else:
                    return jsonify(
                        {"success": False, "error": "Please confirm your email before logging in."})
            else:
                return jsonify(
                    {"success": False, "error": "Invalid password."})
        else:
            return jsonify({"success": False, "error": "Invalid email."})

    return render_template("login.html")


@api_v1.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("api_v1.index"))


@api_v1.route('/check_email_confirmation', methods=['POST'])
def check_email_confirmation():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    is_confirmed = user.confirmed

    return jsonify({'confirmed': is_confirmed}), 200


@api_v1.route('/onboarding', methods=['GET', 'POST'])
def save_preferences():
    model_instance = current_app.config['MODEL_INSTANCE']
    known_user_ids = current_app.config['KNOWN_USER_IDS']

    if request.method == 'GET':
        return render_template("onboarding.html")

    try:
        request_data = request.json
        logging.info(f"Received onboarding data: {request_data}")

        onboarding_data = OnboardingSchema().load(request_data)
        user_id = onboarding_data['id']
        genres = onboarding_data['genres']
        ratings = onboarding_data['ratings']

        user = User.query.get(user_id)
        if not user:
            logging.error(f"User not found: {user_id}")
            return jsonify({"error": "User not found"}), 404

        user.preferences = ','.join(genres)

        valid_movie_ids = {movie.movie_id for movie in Movie.query.all()}
        logging.debug(f"Valid movie IDs: {valid_movie_ids}")

        valid_ratings = [(user_id, int(movie_id), rating_value)
                         for movie_id, rating_value in ratings.items()
                         if int(movie_id) in valid_movie_ids]

        if not valid_ratings:
            logging.warning("No valid movie IDs found in the ratings.")
            return jsonify(
                {"error": "No valid movie IDs found in the ratings."}), 400

        for user_id, movie_id, rating_value in valid_ratings:
            rating = Rating(
                user_id=user_id,
                movie_id=movie_id,
                rating=rating_value)
            db.session.add(rating)

        db.session.commit()

        # Update the recommendation model with new user data
        if user_id not in known_user_ids:
            known_user_ids.add(user_id)
            new_ratings = {
                movie_id: rating_value for _,
                movie_id,
                rating_value in valid_ratings}
            model_instance.update_rating_matrix(user_id, new_ratings)
            model_instance.update_user_similarity()
            logging.info(f"Model updated for new user: {user_id}")

        return jsonify({"message": "Preferences saved successfully"}), 200

    except ValidationError as e:
        logging.error(f"Validation Error: {str(e)}")
        return jsonify({"error": e.messages}), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Database Error: {str(e)}")
        return jsonify({"error": "Database error occurred"}), 500
    except Exception as e:
        logging.error(f"Unexpected Error: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500


@api_v1.route("/dashboard", methods=["GET"])
@login_required
def dashboard_data():
    """
    Endpoint for getting data for the user dashboard.
    """
    try:
        user_id = current_user.id

        # 1. Get Personalized Recommendations
        try:
            data = {"userId": user_id,
                    "num_recommendations": 10}
            app.logger.debug(f"Request data for recommendations: {data}")
            recommendations_response = requests.post(
                f"{request.url_root}api/v1/recommendations",
                json=data,
                headers={"X-API-Key": API_KEY}
            )
            recommendations_response.raise_for_status()
            recommendations_data = recommendations_response.json()
            print(
                "Recommendation data sent to the front end",
                recommendations_data)
        except requests.RequestException as e:
            app.logger.error(f"Error fetching recommendations: {e}")
            recommendations_data = {"recommendations": []}

        # 2. Get Trending Movies
        try:
            trending_movies_response = requests.get(
                f"{request.url_root}api/v1/popular_movies?count=10",
                headers={"X-API-Key": API_KEY}
            )
            trending_movies_response.raise_for_status()
            trending_movies_data = trending_movies_response.json()
        except requests.RequestException as e:
            app.logger.error(f"Error fetching trending movies: {e}")
            trending_movies_data = []

        # 3. Get the User's Rated Movies
        try:
            rated_movies = Rating.query.filter_by(user_id=user_id).all()
            rated_movie_ids = [rating.movie_id for rating in rated_movies]

            rated_movies_data = []
            movies = Movie.query.filter(
                Movie.movie_id.in_(rated_movie_ids)).all()
            for movie in movies:
                user_rating = next(
                    (rating.rating for rating in rated_movies if rating.movie_id == movie.movie_id),
                    None)
                rated_movies_data.append({
                    "movieId": movie.movie_id,
                    "title": movie.title,
                    "genres": movie.genres,
                    "userRating": user_rating
                })
        except Exception as e:
            app.logger.error(f"Error fetching rated movies: {e}")
            rated_movies_data = []

        # 4. Get User Information
        user_info = {
            "id": user_id,
            "firstName": current_user.first_name,
            "lastName": current_user.last_name,
            "email": current_user.email,
            "preferences": current_user.preferences.split(",") if current_user.preferences else []
        }

        return render_template(
            "dashboard.html",
            user_info=user_info,
            recommendations=recommendations_data["recommendations"],
            trending_movies=trending_movies_data,
            rated_movies=rated_movies_data)

    except Exception as e:
        app.logger.error(f"Error fetching dashboard data: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
