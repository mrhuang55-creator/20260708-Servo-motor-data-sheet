import os
import sys
from flask import Flask, render_template, redirect, url_for, session

def create_app(config_class=None):
    if getattr(sys, 'frozen', False):
        template_dir = os.path.join(sys._MEIPASS, 'frontend', 'app', 'templates')
        app = Flask(__name__, template_folder=template_dir)
    else:
        app = Flask(__name__)

    if config_class is None:
        from .config import Config
        app.config.from_object(Config)
    else:
        app.config.from_object(config_class)

    # 註冊 Blueprints
    from .auth.routes import auth_bp
    from .operator.routes import operator_bp
    from .engineer.routes import engineer_bp
    from .admin.routes import admin_bp
    from .commands.routes import commands_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(operator_bp)
    app.register_blueprint(engineer_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(commands_bp)

    @app.route("/")
    def index():
        if "user" in session:
            role = str(session["user"].get("role", "")).strip()
            if role.lower() in ("administrator", "admin"):
                return redirect(url_for("admin.approvals"))
            elif role.lower() == "engineer":
                return redirect(url_for("engineer.health"))
            else:
                return redirect(url_for("operator.console"))
        return redirect(url_for("auth.login"))

    @app.after_request
    def disable_caching(response):
        """禁止瀏覽器暫存快取 (No-Store / No-Cache)，離開頁面或關閉後無法透過上一頁還原暫存"""
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("403.html", user=session.get("user")), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html", user=session.get("user")), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("500.html", user=session.get("user")), 500

    return app

