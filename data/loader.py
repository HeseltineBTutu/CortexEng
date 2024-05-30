"""
This module contains a function to load data from a database into a
pandas DataFrame.

Functions:
    load_data(): Load the data from the database table.
"""

from flask import Flask
import pandas as pd

from models.models import Rating


def load_data():
    """
    Load data from the ratings table in the database.

    Returns:
        pandas.DataFrame: The loaded data from the ratings table.
    """
    ratings = Rating.query.all()

    # Convert SQLAlchemy result to pandas DataFrame
    ratings_df = pd.DataFrame([(r.userId, r.movieId, r.rating, r.timestamp) for r in ratings],
                              columns=['userId', 'movieId', 'rating', 'timestamp'])
    return ratings_df
