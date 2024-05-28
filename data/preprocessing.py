
def normalize_ratings(ratings):
    """
    Normalize the ratings matrix.
    Args:
        ratings (pd.DataFrame): DataFrame containing the ratings data.
    Returns:
        pd.DataFrame: DataFrame containing the normalized ratings data.
    """
    ratings_matrix = ratings.pivot(index='userId',
                                   columns='movieId',
                                   values='rating')
    # Impute missing values with the users's mean rating
    ratings_matrix = ratings_matrix.fillna(ratings_matrix.mean(axis=1))
    
    # Mean centering
    ratings_matrix = ratings_matrix.sub(ratings_matrix.mean(axis=1), axis=0)
    return ratings_matrix
