import sys

import numpy as np
sys.path.append("..")
import unittest
import json
from CortexEng.data.loader import load_data
from CortexEng.data.preprocessing import normalize_ratings
from CortexEng.recommendation_engine.collaborative_filtering import UserBasedCF
from CortexEng.api.app import app

class TestEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        # Load sample data (ratings.csv)
        self.ratings = load_data('data/ratings.csv')
        self.normalized_ratings = normalize_ratings(self.ratings)
        self.model = UserBasedCF(self.normalized_ratings.fillna(0).values)
        self.model.fit()
        self.valid_user_ids = self.ratings['userId']
        self.valid_movie_ids = self.ratings['movieId']

    def test_valid_prediction(self):
        user_id = 1
        movie_id = 1

        # Ensure user_id and movie_id are within the valid range
        max_user_id = self.ratings['userId'].max()
        max_movie_id = self.ratings['movieId'].max()
        self.assertTrue(user_id <= max_user_id)
        self.assertTrue(movie_id <= max_movie_id)

        payload = {'userId': int(user_id), 'movieId': int(movie_id)}
        response = self.app.post('/api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertIn('predicted_rating', data)
        self.assertIsInstance(data['predicted_rating'], float)

    def test_invalid_user(self):
        payload = {'userId': 999999, 'movieId': 31}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_missing_user(self):
        payload = {'movieId': 31}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_missing_movie(self):
        payload = {'userId': 1}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_string_user_id(self):
        payload = {'userId': 'invalid', 'movieId': 31}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data, {'userId': ['Not a valid integer.']})

    def test_invalid_string_user_id(self):
        payload = {'userId': 'invalid', 'movieId': 31}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {'userId': ['Not a valid integer.']})


    def test_invalid_string_movie_id(self):
        payload = {'userId': 1, 'movieId': 'invalid'}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_negative_user_id(self):
        payload = {'userId': -1, 'movieId': 31}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_empty_payload(self):
        payload = {}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_extra_fields_in_payload(self):
        user_id = np.random.choice(self.valid_user_ids)
        movie_id = np.random.choice(self.valid_movie_ids)
        payload = {'userId': int(user_id), 'movieId': int(movie_id), 'extraField': 'extraValue'}
        response = self.app.post('api/v1/predict', data=json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_non_json_payload(self):
        payload = "This is not a JSON string"
        response = self.app.post('api/v1/predict', data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 400)

