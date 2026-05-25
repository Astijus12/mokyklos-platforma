"""Pagrindinis Flask aplikacijos failas - čia paleidžiama programa."""
import os
from flask import Flask
from flask_login import LoginManager

from config import Config
from models import db, User
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.classes import classes_bp
from routes.students import students_bp
from routes.diplomas import diplomas_bp
from routes.users import users_bp
from routes.announcements import announcements_bp
from routes.profile import profile_bp
from routes.search import search_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Prašome prisijungti, kad galėtumėte tęsti."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(diplomas_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)
