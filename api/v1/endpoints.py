from flask import Blueprint, request, jsonify
from marshmallow import EXCLUDE, Schema, fields, ValidationError
from recommendation_engine.collaborative_filtering import UserBasedCF
from data.loader import load_data
from data.preprocessing import normalize_ratings
import numpy as np
import os


from functools import lru_cache, wraps

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')


class PredictionRequestSchema(Schema):
    userId = fields.Integer(required=True)
    movieId = fields.Integer(required=True)


class RecommendationRequestSchema(Schema):
    userId = fields.Integer(required=True, validate=lambda val: val > 0)
    num_recommendations = fields.Integer(
        missing=10,
        validate=lambda val: val > 0
        )


class Meta:
    unknown = EXCLUDE


# Caching the ratings matrix for better performance.
@lru_cache(maxsize=1)
def get_ratings_matrix():
    ratings = load_data('data/ratings.csv')
    normalized_ratings = normalize_ratings(ratings)
    ratings_matrix = normalized_ratings.fillna(0).values
    return ratings_matrix


# API key authentication decorator
def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-KEY')
        if not provided_key or provided_key != os.getenv('API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401
        return view_function(*args, **kwargs)
    return decorated_function


@api_v1.route('/predict', methods=['POST'])
@require_api_key
def predict():
    try:
        data = PredictionRequestSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    user_id = data['userId']
    movie_id = data['movieId']
    # Check if user_id and movie_id are positive
    if user_id <= 0 or movie_id <= 0:
        return jsonify(
            {'error': 'User ID and Movie ID must be positive integers'}
            ), 400

    # Input validation (Check if the user ID is valid)
    ratings_matrix = get_ratings_matrix()

    # Check if user_id and movie_id are within range
    if (user_id - 1 >= ratings_matrix.shape[0] or
       movie_id - 1 >= ratings_matrix.shape[1]):
        return jsonify({'error': 'User ID or Movie ID is out of bounds'}), 400

    model = UserBasedCF(ratings_matrix)
    model.fit()
    # Substract 1 from user_id and item_id to match the index
    # in the ratings matrix
    prediction = model.predict(user_id - 1, movie_id - 1)

    # Ensure the prediction is a float
    if np.isnan(prediction):
        prediction = None

    return jsonify({'predicted_rating': prediction})


@api_v1.route('/recommendations', methods=['POST'])
@require_api_key
def get_recommendations():
    """
    Endpoint for getting movie recommendations.

    ___
    parameters:
        - name: userId
          in: body
          type: integer
          required: true
          description: The ID of the user.
        - name: num_recommendations
          in : body
          type: integer
          required: false
          description: The number of recommendations to return. Default to 10.
    responses:
       200:
        description: A list of recommended movie IDs.
        schema:
            type: object
            properties:
                recommendations:
                    type: array
                    items:
                        type: object
                        poperties:
                            movieId:
                                type: integer
                            predictedRating:
                                type: number
      400:
        description: Invalid user ID or missing data.
      500:
        description: Internal server error.

    """
    # Get user id from request body
    try:
        data = RecommendationRequestSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    userId = data['userId']
    # Get number of recommendations (with a default value)
    num_recommendations = request.json.get('num_recommendations', 10)

    # Input validation (Check if the user ID is valid)
    ratings_matrix = get_ratings_matrix()

    if userId < 0 or userId >= ratings_matrix.shape[0]:
        return jsonify({'error': f"Invalid user ID: {userId}"}), 400
    model = UserBasedCF(ratings_matrix)
    model.fit()

    # Get all the movie IDs the user has not rated
    all_movie_ids = range(ratings_matrix.shape[1])
    # Get indices of rated movies
    user_rated_movies = ratings_matrix[userId].nonzero()[0]
    # Filter out rated movies
    unrated_movie_ids = np.setdiff1d(all_movie_ids, user_rated_movies)

    # Predict ratings for unrated movies
    predictions = [
        (movieId, model.predict(userId, movieId))
        for movieId in unrated_movie_ids
        ]

    # Sort predictions by predicted rating (descending)
    predictions.sort(key=lambda x: x[1], reverse=True)
    # Get top-N recommendations
    top_recommendations = [
        {"movieId": int(movieId), "predictedRating": round(score, 2)}
        for movieId, score in predictions[:num_recommendations]
        if not np.isnan(score)
    ]
    return jsonify({'recommendations': top_recommendations})
