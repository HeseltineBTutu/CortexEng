import logging
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from api.database import db
from flask_login import UserMixin
import numpy as np
from recommendation_engine.collaborative_filtering import UserBasedCF
import scipy.sparse as sparse


def initialize_model():
    logging.basicConfig(level=logging.DEBUG)
    model = None
    known_user_ids = set()

    try:
        # Fetch all registered users from the database
        all_users = db.session.query(User).all()
        all_user_ids = [user.id for user in all_users]

        # Fetch all ratings from the database
        ratings = db.session.query(Rating).all()
        logging.debug(f"Fetched {len(ratings)} ratings from the database.")

        if not ratings:
            logging.warning(
                "Warning: No ratings found. The model will not be able to make predictions.")
            return None, None

        user_ids = [rating.user_id for rating in ratings]
        movie_ids = [rating.movie_id for rating in ratings]

        known_user_ids.update(user_ids)

        unique_user_ids = list(set(all_user_ids))
        unique_movie_ids = list(set(movie_ids))

        logging.debug(
            f"Unique user IDs: {len(unique_user_ids)}, Unique movie IDs: {len(unique_movie_ids)}")

        # Create mappings for user IDs and movie IDs
        user_index = {
            user_id: idx for idx,
            user_id in enumerate(unique_user_ids)}
        movie_index = {movie_id: idx for idx,
                       movie_id in enumerate(unique_movie_ids)}

        # Create a sparse matrix for ratings
        rating_matrix = sparse.lil_matrix(
            (len(unique_user_ids), len(unique_movie_ids)))
        logging.debug(f"Rating matrix shape: {rating_matrix.shape}")

        for rating in ratings:
            user_idx = user_index.get(rating.user_id)
            movie_idx = movie_index.get(rating.movie_id)

            if user_idx is None or movie_idx is None:
                logging.warning(
                    f"Invalid user_id {rating.user_id} or movie_id {rating.movie_id} found in ratings. Skipping this entry.")
                continue

            rating_matrix[user_idx, movie_idx] = rating.rating

        logging.debug("Rating matrix populated")
        # Convert the space matrix to a CSR (Compressed Sparse Row) matrix for
        # efficient storage and computation
        rating_matrix = rating_matrix.tocsr()

        model = UserBasedCF(rating_matrix, user_index, movie_index)
        logging.debug(f"UserBasedCF model instance created: {model}")

        logging.debug("Starting to fit the UserBasedCF model")
        model.fit()
        logging.debug("UserBasedCF model fitting completed")

        logging.info("Model initialized successfully.")
    except Exception as e:
        logging.error(
            f"Exception type: {type(e).__name__}, Error message: {str(e)}")
        model = None

    return model, known_user_ids


class Movie(db.Model):
    __tablename__ = 'movies'
    __table_args__ = {'schema': 'public'}

    id = db.Column(Integer, primary_key=True)
    movie_id = db.Column(Integer, unique=True, nullable=False)
    title = db.Column(String(255), nullable=False)
    genres = db.Column(String(255), nullable=False)
    imdb_id = db.Column(String(255), nullable=True)
    tmdb_id = db.Column(String(255), nullable=True)

    ratings = relationship(
        'Rating',
        back_populates='movie',
        lazy=True,
        cascade="all, delete-orphan")
    tags = relationship(
        'Tag',
        back_populates='movie',
        lazy=True,
        cascade="all, delete-orphan")


class Tag(db.Model):
    __tablename__ = 'tags'
    __table_args__ = {'schema': 'public'}

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, nullable=False)
    movie_id = db.Column(
        Integer,
        ForeignKey('public.movies.movie_id'),
        nullable=False,
        index=True)
    tag = db.Column(String(255), nullable=False)
    # Set default to current timestamp
    timestamp = db.Column(DateTime, default=func.now())

    movie = relationship('Movie', back_populates='tags')


class Rating(db.Model):
    __tablename__ = 'ratings'
    __table_args__ = {'schema': 'public'}

    id = db.Column(Integer, primary_key=True)
    user_id = db.Column(Integer, ForeignKey('public.users.id'), nullable=False)
    movie_id = db.Column(
        Integer,
        ForeignKey('public.movies.movie_id'),
        nullable=False,
        index=True)
    rating = db.Column(Float, nullable=False)
    # Set default to current timestamp
    timestamp = db.Column(DateTime, default=func.now())

    movie = relationship('Movie', back_populates='ratings')
    user = relationship('User', back_populates='ratings')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    __table_args__ = (
        db.UniqueConstraint('email', name='uq_users_email'),
        {'schema': 'public'}
    )

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(
        db.String(255),
        nullable=False)  # Store hashed password
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))
    preferences = db.Column(db.String(255))
    confirmed = db.Column(db.Boolean, default=False)
    confirmation_token = db.Column(db.String(100), nullable=True)
    confirmed_on = db.Column(db.DateTime, nullable=True)
    bio = db.Column(db.String(500), nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True) 
    ratings = db.relationship('Rating', back_populates='user', lazy=True)
    

    def __repr__(self):
        return f"<User (id={self.id}, email={self.email})>"

    def is_active(self):
        """Return True if the user's account is active (email confirmed)."""
        return self.confirmed
