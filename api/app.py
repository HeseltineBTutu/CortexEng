from api.v1.endpoints import api_v1
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_v1)
    return app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
