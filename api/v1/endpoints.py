from flask import Blueprint, request, jsonify
from marshmallow import EXCLUDE, Schema, fields, ValidationError
from recommendation_engine.collaborative_filtering import UserBasedCF
from data.loader import load_data
from data.preprocessing import normalize_ratings
import numpy as np


from functools import lru_cache

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

class PredictionRequestSchema(Schema):
    userId = fields.Integer(required=True)
    movieId = fields.Integer(required=True)

    class Meta:
        unknown = EXCLUDE
@lru_cache(maxsize=1)
def get_ratings_matrix():
    ratings = load_data('data/ratings.csv')
    normalized_ratings = normalize_ratings(ratings)
    ratings_matrix = normalized_ratings.fillna(0).values
    return ratings_matrix

@api_v1.route('/predict', methods=['POST'])
def predict():
    # ... (API key validation)
    try:
        data = PredictionRequestSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    

    user_id = int(request.json['userId'])
    movie_id = int(request.json['movieId'])
    
    # Check if user_id and movie_id are positive
    if user_id <= 0 or movie_id <= 0:
        return jsonify({'error': 'User ID and Movie ID must be positive integers'}), 400

    ratings_matrix = get_ratings_matrix()

    # Check if user_id and movie_id are within range
    if user_id  - 1 >= ratings_matrix.shape[0] or movie_id - 1 >= ratings_matrix.shape[1]:
        return jsonify({'error': 'User ID or Movie ID is out of bounds'}), 400

    model = UserBasedCF(ratings_matrix)
    model.fit()
    # Substract 1 from user_id and item_id to match the index
    # in the ratings matrix
    prediction = model.predict(user_id - 1, movie_id - 1)

    # Ensure the prediction is a float
    if np.isnan(prediction):
        prediction = None # Handle case where prediction might not be possible

    return jsonify({'predicted_rating': prediction})
