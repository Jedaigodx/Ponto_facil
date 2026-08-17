from flask import Flask

from config import Config
from app.extensions import db, login_manager


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(reports_bp)

    DIAS_SEMANA = ["SEG", "TER", "QUA", "QUI", "SEX", "SAB", "DOM"]

    @app.template_filter("dia_semana")
    def dia_semana(data):
        return DIAS_SEMANA[data.weekday()]

    @app.template_filter("data_br")
    def data_br(data):
        return data.strftime("%d/%m")

    from app.models import formatar_timedelta as _fmt_td

    @app.template_filter("fmt_saldo")
    def fmt_saldo(td):
        return _fmt_td(td)

    with app.app_context():
        db.create_all()

    return app
