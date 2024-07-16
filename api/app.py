from flask import Flask, g, jsonify
from flask_oidc import OpenIDConnect
from okta.client import Client as OktaClient
from dotenv import find_dotenv, load_dotenv
from flask_migrate import Migrate
from models.models import initialize_model
from api.database import db
from api.extensions import bcrypt, mail, login_manager
import os
import uuid
import logging


# Generate and store API key if not already present
def generate_api_key():
    return str(uuid.uuid4())


def configure_api_key():
    api_key = os.getenv("API_KEY")
    if not api_key:
        api_key = generate_api_key()
        os.environ["API_KEY"] = api_key
        with open('.env', 'a') as f:
            f.write(f"API_KEY={api_key}\n")
        print(f"Generated and stored API key: {api_key}")


configure_api_key()

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv()

logging.basicConfig(level=logging.DEBUG)


def create_app():
    app = Flask(
        __name__,
        template_folder="../frontend/templates",
        static_folder="../frontend/static")

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT=os.getenv("SECURITY_PASSWORD_SALT"),
        MAIL_SERVER=os.getenv("MAIL_SERVER"),
        MAIL_PORT=int(
            os.getenv("MAIL_PORT")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS") == 'True',
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER"),
        OIDC_CLIENT_SECRETS={
            "web": {
                "client_id": os.getenv("OKTA_CLIENT_ID"),
                "client_secret": os.getenv("OKTA_CLIENT_SECRET"),
                "auth_uri": f"{os.getenv('OKTA_ORG_URL')}/oauth2/default/v1/authorize",
                "token_uri": f"{os.getenv('OKTA_ORG_URL')}/oauth2/default/v1/token",
                "userinfo_uri": f"{os.getenv('OKTA_ORG_URL')}/oauth2/default/v1/userinfo",
                "issuer": f"{os.getenv('OKTA_ORG_URL')}/oauth2/default",
            }},
        OIDC_COOKIE_SECURE=False,
        OIDC_CALLBACK_ROUTE="/oidc/callback",
        OIDC_SCOPES=[
            "openid",
            "email",
            "profile"],
        API_KEY=os.getenv("API_KEY"),
        SECRET_KEY=os.getenv('SECRET_KEY'),
        BCRYPT_LOG_ROUNDS=13)

    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate = Migrate(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "api_v1.login"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    oidc = OpenIDConnect(app, OktaClient({
        "orgUrl": os.getenv("OKTA_ORG_URL"),
        "token": os.getenv("OKTA_CLIENT_SECRET")
    }))

    @app.before_request
    async def before_request():
        g.user = oidc.user_getfield("email") if oidc.user_loggedin else None

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401

    from api.v1.endpoints import api_v1
    app.register_blueprint(api_v1)

    @app.route("/oidc/callback")
    def oidc_callback():
        return oidc.callback_to()

    with app.app_context():
        logging.debug("Entering app context to initialize the model.")
        # Capture the returned model instance and known user IDs
        model_instance, known_user_ids = initialize_model()
        logging.debug("Model initialization function called.")

        if model_instance is None or known_user_ids is None:
            logging.error(
                "Failed to initialize the recommendation model or known user IDs.")
        else:
            logging.info(
                "Recommendation model and known user IDs initialized and ready for use.")
            app.config['MODEL_INSTANCE'] = model_instance
            app.config['KNOWN_USER_IDS'] = known_user_ids

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
