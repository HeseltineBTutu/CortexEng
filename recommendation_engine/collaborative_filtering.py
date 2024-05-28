import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity, pairwise_distances

class UserBasedCF:
    def __init__(self, ratings_matrix, similarity_metric='cosine', k=30, sim_threshold=0.3):
        """
        Initialize the UserBasedCF class.

        Parameters:
        - ratings_matrix (numpy.ndarray): User-item rating matrix.
        - k (int, optional): The number of top similar users to consider. Default is 30.
        - sim_threshold (float, optional): The similarity threshold to consider a user as similar. Default is 0.3.

        """
        self.ratings_matrix = ratings_matrix
        self.similarity_matrix = None
        self.similarity_metric = similarity_metric
        self.k = k
        self.sim_threshold = sim_threshold

    def fit(self):
        """
        Fit the user-based collaborative filtering model by calculating the similarity matrix.
        """
        # Convert the rating matrix to a sparse matrix for efficiency
        self.ratings_matrix = csr_matrix(self.ratings_matrix)
        if self.similarity_metric == 'cosine':
            # Compute the cosine similarity matrix for users
            self.similarity_matrix = cosine_similarity(self.ratings_matrix)
        else:
            self.similarity_matrix = 1 - pairwise_distances(self.ratings_matrix, metric=self.similarity_metric)

    def predict(self, userId, movieId):
        """
        Predict the rating for a given user and item using user-based CF.

        Parameters:
        - userId (int): The ID of the user for whom the prediction is made.
        - movieId (int): The ID of the movie for which the prediction is made.  

        Returns:
        - float: The predicted rating for the specified user and movie.
        """
        # Check if the user has already rated the item
        user_ratings = self.ratings_matrix[userId].toarray()[0]
        if user_ratings[movieId] > 0:
            return user_ratings[movieId]  # Return the actual rating if already rated

        # If the user hasn't rated the item, proceed with collaborative filtering
        similarity_scores = self.similarity_matrix[userId]
        rated_users_mask = self.ratings_matrix[:, movieId].toarray().flatten() > 0
        rated_users = np.where(rated_users_mask)[0]  # Indices of users who rated the item

        # Apply similarity threshold and get valid users
        valid_users_mask = similarity_scores[rated_users] > self.sim_threshold
        valid_rated_users = rated_users[valid_users_mask]  # Filtered rated users

        if len(valid_rated_users) == 0:
            return np.nan  # No similar users found

        # Get top-k similar users
        top_k_users = valid_rated_users[np.argsort(-similarity_scores[valid_rated_users])[:self.k]]

        # Ratings and similarity scores for top-k users
        ratings = self.ratings_matrix[top_k_users, movieId].toarray().flatten()
        sim_scores = similarity_scores[top_k_users]

        if sim_scores.sum() == 0:
            return np.nan  # Check for zero similarity scores

        # Calculate the weighted average prediction
        prediction = np.dot(sim_scores, ratings) / sim_scores.sum()
        return np.clip(prediction, 1, 5)  # Clip prediction to valid rating range (1 to 5)
