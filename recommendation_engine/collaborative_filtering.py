"""
This module implements a user-based collaborative filtering algorithm for movie
recommendations.

The UserBasedCF class takes a ratings matrix, user and movie indices,
and other parameters
to train a nearest neighbors model and make predictions for user-movie pairs.

Example:
    >>> ratings_matrix = ...  # Load your ratings matrix
    >>> user_index = ...  # Load user index
    >>> movie_index = ...  # Load movie index
    >>> cf = UserBasedCF(ratings_matrix, user_index, movie_index)
    >>> cf.fit()
    >>> prediction = cf.predict(user_id, movie_id)
"""

import logging
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances
from sklearn.neighbors import NearestNeighbors
import random
from datetime import datetime


class UserBasedCF:
    """
    User-based collaborative filtering algorithm for movie recommendations.

    Attributes:
        ratings_matrix (scipy.sparse.csr_matrix): Sparse matrix of user-movie
        ratings.
        user_index (dict): Mapping of user IDs to row indices in the ratings
        matrix.
        movie_index (dict): Mapping of movie IDs to column indices in the
        ratings matrix.
        similarity_metric (str): Metric to use for computing user
        similarity (default: 'cosine').
        k (int): Number of nearest neighbors to consider (default: 30).
        sim_threshold (float): Minimum similarity score threshold for
        valid neighbors (default: 0.2).
        nearest_neighbors (sklearn.neighbors.NearestNeighbors): Fitted
        nearest neighbors model.
    """

    def __init__(
            self,
            ratings_matrix,
            user_index,
            movie_index,
            similarity_metric='cosine',
            k=30,
            sim_threshold=0.2):
        """
        Initialize the UserBasedCF object.

        Args:
            ratings_matrix (numpy.ndarray): Matrix of user-movie ratings.
            user_index (dict): Mapping of user IDs to row indices in the
            ratings
            matrix.
            movie_index (dict): Mapping of movie IDs to column indices in
            the
            ratings matrix.
            similarity_metric (str, optional): Metric to use for computing
            user
            similarity (default: 'cosine').
            k (int, optional): Number of nearest neighbors to consider
            (default: 30).
            sim_threshold (float, optional): Minimum similarity score threshold
            for
            valid neighbors (default: 0.2).
        """
        if ratings_matrix is None:
            raise ValueError("Rating matrix cannot be None.")
        # Convert to sparse matrix here
        self.ratings_matrix = csr_matrix(ratings_matrix)
        self.user_index = user_index
        self.movie_index = movie_index
        self.similarity_metric = similarity_metric
        self.k = k
        self.sim_threshold = sim_threshold
        self.nearest_neighbors = None

    def fit(self):
        """
        Fit the nearest neighbors model on the ratings matrix.

        This method converts the ratings matrix to a sparse matrix and
        computes
        the nearest neighbors for each user based on the specified similarity metric.
        """
        if self.ratings_matrix is None:
            logging.error("Ratings matrix is None. Cannot proceed with fit.")
            return

        try:
            logging.debug(
                "Converting the rating matrix to a sparse matrix for efficiency.")
            self.ratings_matrix = csr_matrix(self.ratings_matrix)

            logging.debug("Computing the nearest neighbors for users.")
            self.nearest_neighbors = NearestNeighbors(
                metric=self.similarity_metric, algorithm='auto', n_neighbors=self.k + 1)
            self.nearest_neighbors.fit(self.ratings_matrix)
            logging.debug("Nearest neighbors model fitted successfully.")
        except Exception as e:
            logging.error(f"Error in fit method: {e}")
            self.nearest_neighbors = None

    def predict(self, user_id, movie_id) -> float:
        """
        Predict the rating for a given user-movie pair.

        Args:
        user_id (int): ID of the user.
        movie_id (int): ID of the movie.

        Returns:
            float: Predicted rating for the user-movie pair, or
            NaN if prediction is not possible.
        """
        try:
            if user_id not in self.user_index or movie_id not in self.movie_index:
                logging.error(
                    f"User ID {user_id} or movie ID {movie_id} out of range")
                return self.get_fallback_rating(movie_id)

            user_idx = self.user_index[user_id]
            movie_idx = self.movie_index[movie_id]

            if self.nearest_neighbors is None:
                logging.error(
                    "Nearest neighbors model is None. Cannot make predictions.")
                return np.nan

            user_ratings = self.ratings_matrix[user_idx].toarray()[0]
            if user_ratings[movie_idx] > 0:
                return user_ratings[movie_idx]

            distances, indices = self.nearest_neighbors.kneighbors(
                self.ratings_matrix[user_idx], n_neighbors=self.k + 1)
            similarity_scores = 1 - distances.flatten()
            indices = indices.flatten()

            logging.debug(
                f"Similarity scores for user {user_id}: {similarity_scores}")
            logging.debug(
                f"Indices of neighbors for user {user_id}: {indices}")

            rated_users_mask = self.ratings_matrix[indices, movie_idx].toarray(
            ).flatten() > 0
            rated_users = indices[rated_users_mask]

            logging.debug(f"Rated users for movie {movie_id}: {rated_users}")

            valid_users_mask = similarity_scores[rated_users_mask] > self.sim_threshold
            valid_rated_users = rated_users[valid_users_mask]

            logging.debug(
                f"Valid rated users for movie {movie_id}: {valid_rated_users}")

            if len(valid_rated_users) == 0:
                logging.debug(
                    f"No valid rated users found for movie {movie_id} and user {user_id}")
                return self.get_fallback_rating(movie_id)

            top_k_users = valid_rated_users[np.argsort(
                -similarity_scores[rated_users_mask][valid_users_mask])[:self.k]]
            ratings = self.ratings_matrix[top_k_users,
                                          movie_idx].toarray().flatten()
            sim_scores = similarity_scores[top_k_users]

            logging.debug(f"Top K users: {top_k_users}")
            logging.debug(f"Ratings from top K users: {ratings}")
            logging.debug(f"Similarity scores of top K users: {sim_scores}")

            if sim_scores.sum() == 0:
                logging.debug(
                    f"Sum of similarity scores is zero for user {user_id} and movie {movie_id}")
                return np.nan

            prediction = np.dot(sim_scores, ratings) / sim_scores.sum()
            return np.clip(prediction, 1, 5)
        except Exception as e:
            logging.error(
                f"Error predicting rating for user {user_id} and movie {movie_id}: {e}")
            return self.get_fallback_rating(movie_id)

    def get_fallback_rating(self, movie_id) -> float:
        """
        Get a fallback rating for a movie when no valid neighbors are found.

        Args:
            movie_id (int): ID of the movie.

        Returns:
            float: Fallback rating for the movie, based on the movie's average rating
            or genre-based average rating.
        """
        try:
            # First, try to use the average rating for the movie
            movie_ratings = self.ratings_matrix[:,
                                                self.movie_index[movie_id]].data
            if len(movie_ratings) > 0:
                base_rating = float(np.mean(movie_ratings))
            else:
                # If no ratings available, use genre-based average
                movie = Movie.query.get(movie_id)
                if movie and movie.genres:
                    genre_ratings = Rating.query.join(Movie).filter(
                        Movie.genres.contains(
                            movie.genres)).with_entities(
                        Rating.rating).all()
                    if genre_ratings:
                        base_rating = float(
                            np.mean([r.rating for r in genre_ratings]))
                    else:
                        base_rating = 3.0  # Neutral rating if no genre data available
                else:
                    base_rating = 3.0  # Neutral rating if no movie or genre data

            # Add some randomness, but keep the rating between 1 and 5
            return max(1.0, min(5.0, base_rating + random.uniform(-0.5, 0.5)))

        except Exception as e:
            logging.error(
                f"Error in get_fallback_rating for movie {movie_id}: {str(e)}")
            return 3.0  # Return neutral rating in case of any error

    def rank_recommendations(self, recommendations) -> list:
        """
        Rank a list of movie recommendations based on predicted rating and recency.

        Args:
            recommendations (list): List of dictionaries containing 'movieId' and
            'predictedRating' keys.

        Returns:
            list: Sorted list of recommendations, with an additional 'score' key that combines
                the predicted rating and a recency boost for newer movies.
        """
        current_year = datetime.now().year
        for rec in recommendations:
            movie = Movie.query.get(rec['movieId'])
            if movie and movie.year:
                years_old = current_year - movie.year
                # Boost for movies less than 10 years old
                recency_boost = max(0, 1 - (years_old / 10))
                rec['score'] = rec['predictedRating'] + recency_boost
            else:
                rec['score'] = rec['predictedRating']

        return sorted(recommendations, key=lambda x: x['score'], reverse=True)

    def update_rating_matrix(self, user_id, movie_ids, ratings):
        """
            Update the ratings matrix with new user-movie ratings.

        Args:
            user_id (int): ID of the user.
            movie_ids (list): List of movie IDs.
            ratings (list): List of corresponding ratings for the movies.

        This method resizes the ratings matrix if necessary to accommodate new users or movies,
        updates the specified ratings, and refits the nearest neighbors model.
        """
        self.ratings_matrix = self.ratings_matrix.tolil()

        # Check if the user ID is out of range
        if user_id >= self.ratings_matrix.shape[0]:
            # Resize the matrix to accommodate the new user
            new_rows = user_id - self.ratings_matrix.shape[0] + 1
            self.ratings_matrix = scipy.sparse.vstack(
                [self.ratings_matrix, scipy.sparse.lil_matrix((new_rows, self.ratings_matrix.shape[1]))])

        # Check if any movie IDs are out of range
        max_movie_id = max(movie_ids)
        if max_movie_id >= self.ratings_matrix.shape[1]:
            # Resize the matrix to accommodate the new movie
            new_cols = max_movie_id - self.ratings_matrix.shape[1] + 1
            self.ratings_matrix = scipy.sparse.hstack(
                [self.ratings_matrix, scipy.sparse.lil_matrix((self.ratings_matrix.shape[0], new_cols))])

        # Update the ratings for the specified user and movies
        for movie_id, rating in zip(movie_ids, ratings):
            self.ratings_matrix[user_id, movie_id] = rating

        self.ratings_matrix = self.ratings_matrix.tocsr()
        self.fit()

    def update_user_similarity(self):
        """
        Update the user similarity matrix based on the current ratings matrix.

        This method computes the cosine similarity between all pairs of users
        and stores the result in the `similarity_matrix` attribute.
        """
        self.similarity_matrix = cosine_similarity(self.ratings_matrix)
