import jwt
import datetime
from flask import current_app, render_template
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from api.extensions import mail


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(
        email, salt=current_app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except BaseException:
        return False
    return email


def send_confirmation_email(to_email, confirm_url):
    subject = "Please confirm your email"
    sender = current_app.config['MAIL_DEFAULT_SENDER']
    recipients = [to_email]
    text_body = f'Please click the link to confirm your email: {confirm_url}'
    html_body = render_template('confirm_email.html', confirm_url=confirm_url)

    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    mail.send(msg)
