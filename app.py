"""Pagrindinis Flask aplikacijos failas - čia paleidžiama programa."""
import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
from routes.parents import parents_bp
from routes.security import security_bp
from routes.api import api_bp
from routes.calendar import calendar_bp
from routes.audit import audit_bp
from routes.notifications import notifications_bp
from routes.api_docs import api_docs_bp


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["500 per hour"],
    storage_uri="memory://",
    strategy="fixed-window",
)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)

    if not app.config.get("TESTING"):
        limiter.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Prašome prisijungti, kad galėtumėte tęsti."
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.after_request
    def prideti_apsaugos_antrastes(atsakymas):
        """Prideda turinio apsaugos antraštes (CSP + kitos)."""
        atsakymas.headers["X-Content-Type-Options"] = "nosniff"
        atsakymas.headers["X-Frame-Options"] = "DENY"
        atsakymas.headers["Referrer-Policy"] = "same-origin"
        atsakymas.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com "
            "https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        atsakymas.headers["Content-Security-Policy"] = csp
        return atsakymas

    app.register_blueprint(auth_bp)
    if not app.config.get("TESTING"):
        limiter.limit("10 per minute")(app.view_functions["auth.login"])
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(classes_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(diplomas_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(announcements_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(parents_bp)
    app.register_blueprint(security_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(notifications_bp)
    app.register_blueprint(api_docs_bp)

    @app.errorhandler(404)
    def handle_404(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(403)
    def handle_403(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(429)
    def handle_429(e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def handle_500(e):
        return render_template("errors/500.html"), 500

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=5000)
