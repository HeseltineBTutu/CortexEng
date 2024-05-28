"""
This module contains a function to load data from a file into a
pandas DataFrame.

Functions:
    load_data(file_path): Load the data from a file path.
"""

import pandas as pd
import os


def load_data(file_path='data/ratings.csv'):
    """
    Load the data from a file path into a pandas DataFrame.

    This function reads a comma separated values (csv) file, where each row
    represents a rating.
    Each row in the file should have the following columns: 'user_id',
    'item_id', 'rating', 'timestamp'.
    Any additional columns in the file will be ignored.

    Args:
        file_path: str, the path to the file.
    Returns:
        rating: pd.DataFrame, the data loaded from the file. The DataFrame has
        the following columns:
        - user_id: int, the ID of the user.
        - item_id: int, the ID of the item.
        - rating: int, the rating given by the user to the item.
        - timestamp: int, the timestamp of the rating.
    """
    delimiter = ','  # Define the delimiter variable
    encoding = 'utf-8'  # Define the encoding variable
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    dtypes = {'userId': int, 'movieId': int, 'rating': float}

    column_names = ['userId', 'movieId', 'rating', 'timestamp']
    ratings = pd.read_csv(file_path, sep=delimiter, encoding=encoding,
                          names=column_names, dtype=dtypes,
                          usecols=['userId', 'movieId', 'rating', 'timestamp'], skiprows=1)

    # Drop rows with missing values in key columns
    ratings.dropna(subset=['userId', 'movieId', 'rating'], inplace=True)
    # Convert timestamp to datetime format
    ratings['timestamp'] = pd.to_datetime(ratings['timestamp'])


    return ratings
