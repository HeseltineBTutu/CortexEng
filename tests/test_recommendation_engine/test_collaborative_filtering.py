import unittest
import numpy as np
from recommendation_engine.collaborative_filtering import UserBasedCF

class TestUserBasedCF(unittest.TestCase):
    def setUp(self):
        # Create a small sample ratings matrix
        self.ratings_matrix = np.array([
            [5, 3, 0, 1],
            [4, 0, 3, 1],
            [1, 1, 0, 5],
            [1, 0, 0, 4],
            [0, 1, 5, 4],
        ])

        self.cf_model = UserBasedCF(self.ratings_matrix)
        self.cf_model.fit()  # Precompute similarities

    def test_fit_creates_similarity_matrix(self):
        self.assertIsNotNone(self.cf_model.similarity_matrix)
        self.assertEqual(self.cf_model.similarity_matrix.shape, (5, 5))

    def test_predict_with_similar_users(self):
        # User 0 and User 1 have similar ratings
        prediction = self.cf_model.predict(0, 2)  # Item 2 not rated by User 0
        self.assertAlmostEqual(prediction, 3, delta=0.5)  # Expect around 3

    def test_predict_with_no_similar_users(self):
        # User 3 has no similar users who rated item 1
        prediction = self.cf_model.predict(3, 1)
        self.assertTrue(np.isnan(prediction))

    def test_predict_with_all_zero_similarity(self):
        # Simulate a user with zero similarity to everyone
        zero_sim_user = np.zeros(self.ratings_matrix.shape[1])
        cf_model = UserBasedCF(np.vstack([self.ratings_matrix, zero_sim_user]))
        cf_model.fit()
        prediction = cf_model.predict(5, 0)  # Predict for new user
        self.assertTrue(np.isnan(prediction))

    def test_predict_for_rated_item(self):
        # Prediction for item already rated by the user should return the actual rating
        prediction = self.cf_model.predict(0, 0)  # User 0 has rated item 0 with 5
        self.assertEqual(prediction, 5)