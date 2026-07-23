import os

from flask import Flask
from extensions import db


def _obter_uri_banco_dados():
    """Usa Postgres (DATABASE_URL) se existir; caso contrário cai para SQLite local.

    Isto permite continuar a desenvolver localmente com SQLite (sem precisar
    de Postgres instalado na máquina) e usar Postgres persistente em produção
    (Render, etc.), bastando definir a variável de ambiente DATABASE_URL.
    """
    url = os.environ.get("DATABASE_URL")

    if url:
        # O Render/Heroku fornecem a URL como "postgres://...", mas o
        # SQLAlchemy 1.4+/2.x exige o esquema "postgresql://...".
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    basedir = os.path.abspath(os.path.dirname(__file__))
    return "sqlite:///" + os.path.join(basedir, "cuide.db")


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-cuide-mais-secret")

    app.config["SQLALCHEMY_DATABASE_URI"] = _obter_uri_banco_dados()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

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
