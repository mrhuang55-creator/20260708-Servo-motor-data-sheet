import os
from flask import Flask, render_template, redirect, url_for, session

def create_app(config_class=None):
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
            role = session["user"].get("role")
            if role == "Administrator":
                return redirect(url_for("admin.approvals"))
            elif role == "Engineer":
                return redirect(url_for("engineer.health"))
            else:
                return redirect(url_for("operator.console"))
        return redirect(url_for("auth.login"))

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
