import argparse
from recommendation_engine.collaborative_filtering import UserBasedCF
from data.loader import load_data
from data.preprocessing import normalize_ratings
import numpy as np
from api.app import app


def main():
    parser = argparse.ArgumentParser(description="CortexEng Recomemender")
    parser.add_argument("userId", type=int,
                        help="The user ID to generate recommendations for.")
    parser.add_argument("--num_recommendations", "-n", type=int, default=10,
                        help="Number of recommendations to return "
                        "(default: 10)")
    args = parser.parse_args()
    user_id = args.userId
    num_recommendations = args.num_recommendations

    # Load and preprocess data
    ratings = load_data()
    normalized_ratings = normalize_ratings(ratings)
    ratings_matrix = normalized_ratings.fillna(0).values

    model = UserBasedCF(ratings_matrix)
    model.fit()

    all_movie_ids = range(ratings_matrix.shape[1])

    # Get all movie IDs the user has NOT rated
    user_rated_movies = ratings_matrix[user_id].nonzero()[0]
    unrated_movie_ids = np.setdiff1d(all_movie_ids, user_rated_movies)

    # Predict ratings for unrated movies
    predictions = [
        (movieId, model.predict(user_id, movieId))
        for movieId in unrated_movie_ids
    ]
    # Sort predictions by predicted rating (descending)
    predictions = sorted(predictions, key=lambda x: x[1], reverse=True)

    # Get top-N recommendations
    top_recommendations = [
        {"movieId": int(movie_id), "predictedRating": round(score, 2)}
        for movie_id, score in predictions[:num_recommendations]
        if not np.isnan(score)
    ]
    print("Top Recommendation for User", user_id, ":")
    for recommendation in top_recommendations:
        print(
            f"- Movie ID: {recommendation['movieId']}, Predicted Rating: {recommendation['predictedRating']}")


if __name__ == "__main__":
    with app.app_context():
        main()
