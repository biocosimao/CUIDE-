import os

from flask import Flask
from extensions import db


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-cuide-mais-secret")

    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(basedir, "cuide.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from blueprints.paciente.routes import paciente_bp
    from blueprints.dashboard.routes import dashboard_bp
    from blueprints.farmacia.routes import farmacia_bp

    app.register_blueprint(paciente_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(farmacia_bp, url_prefix="/farmacia")

    with app.app_context():
        import models  
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
