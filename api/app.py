"""
This module defines the Flask application and sets up the OpenID Connect
(OIDC) authentication with Okta.

Imports:
    - api.v1.endpoints: Blueprint for version 1 of the API.
    - flask: Flask web framework.
    - flask_oidc: Flask extension for OIDC authentication.
    - okta.client: Okta SDK for Python.
    - dotenv: Module to read .env files.
    - os: Module to interact with the operating system.

Functions:
    - create_app: Creates and configures the Flask application.
    - before_request: Hook that runs before each request. Checks
    if the user is logged in and sets g.user accordingly.
    - not_found: Error handler for 404 errors.
    - oidc_callback: Route for handling OIDC callbacks.

The application is configured with OIDC settings from environment variables.
The Okta client is initialized with these settings.
The application registers the API blueprint and sets up routes for
OIDC callbacks.

"""

from flask_sqlalchemy import SQLAlchemy
from .v1.endpoints import api_v1
from flask import Flask, g, jsonify
from flask_oidc import OpenIDConnect
from okta.client import Client as OktaClient
from dotenv import find_dotenv, load_dotenv
from flask_migrate import Migrate
from models.models import Rating
from .database import db

import uuid
import os


def generate_api_key():
    """
    Generates a random API key.

    Returns:
        str: A random API key.
    """
    return str(uuid.uuid4())


# Generate the API key
new_api_key = generate_api_key()

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv()

# Check if API_KEY already exist  in the environment
if os.getenv("API_KEY"):
    API_KEY = os.getenv("API_KEY")
    print("API_KEY already exists in .env file. Skip generation.")
else:
    # Store the API key in the environment variable.
    os.environ["API_KEY"] = new_api_key

    # Write the API key to the .env file.
    with open('.env', 'a') as f:
        f.write(f"API_KEY={new_api_key}\n")
    print(f"Generated and stored API key: {new_api_key}")


def create_app():
    """
    Creates and configures the Flask application.

    Returns:
        app (Flask): The configured Flask application.
    """
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    migrate = Migrate(app, db)

    # Okta Configuration
    app.config["OIDC_CLIENT_SECRETS"] = {
        "web": {
            "issuer": f"{os.getenv('OKTA_ORG_URL')}/oauth2/default",
            "client_id": os.getenv("OKTA_CLIENT_ID"),
            "client_secret": os.getenv("OKTA_CLIENT_SECRET"),
            "auth_uri": (
                f"{os.getenv('OKTA_ORG_URL')}"
                "/oauth2/default/v1/authorize"
            ),
            "token_uri": (
                f"{os.getenv('OKTA_ORG_URL')}"
                "/oauth2/default/v1/token"
            ),
            "userinfo_=uri": (
                f"{os.getenv('OKTA_ORG_URL')}"
                "/oauth2/default/v1/userinfo"
            ),
        }
    }
    app.config["OIDC_COOKIE_SECURE"] = False
    app.config["OIDC_CALLBACK_ROUTE"] = "/oidc/callback"
    app.config["OIDC_SCOPES"] = ["openid", "email", "profile"]
    app.config["API_KEY"] = os.getenv("API_KEY")

    # Initialize Okta Client
    okta_client = OktaClient({
        "orgUrl": os.getenv("OKTA_ORG_URL"),
        "token": os.getenv("OKTA_CLIENT_SECRET")
    },
    )
    oidc = OpenIDConnect(app, okta_client)
    # Before request Hook

    @app.before_request
    def before_request():
        """
        This function is executed before each request is processed.
        It checks if the user is logged in and sets the 'g.user'
        variable accordingly.
        """
        if oidc.user_loggedin:
            g.user = oidc.user_getfield("email")
        else:
            g.user = None

    @app.errorhandler(404)
    def not_found(error):
        """
        Handle the 404 error.

        Args:
            error: The error message.

        Returns:
            A JSON response with the error message and a 404 status code.
        """
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(401)
    def unauthorized(error):
        """
        Handle the 401 error.

        Args:
            error: The error message.

        Returns:
            A JSON response with the error message and a 401 status code.
        """
        return jsonify({"error": "Unauthorized"}), 401

    app.register_blueprint(api_v1)

    # Okta Callback Route
    @app.route("/oidc/callback")
    def oidc_callback():
        """
        Callback function for OIDC authentication.

        Returns:
            The callback response from the OIDC provider.
        """
        return oidc.callback_to()
    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
