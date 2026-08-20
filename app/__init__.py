from flask import Flask

from config import Config
from app.extensions import db, login_manager, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        # user_id vem no formato "<id>:<pedaço do hash da senha>" (ver User.get_id).
        # Se não bater com o usuário atual no banco, a sessão é tratada como inválida —
        # evita que um cookie antigo "reconecte" a uma conta recriada com o mesmo ID.
        try:
            id_puro, assinatura = user_id.split(":", 1)
            usuario = User.query.get(int(id_puro))
        except (ValueError, AttributeError):
            return None
        if usuario and usuario.senha_hash[-12:] == assinatura:
            return usuario
        return None

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

    from app.models import formatar_timedelta as _fmt_td, formatar_duracao as _fmt_dur

    @app.template_filter("fmt_saldo")
    def fmt_saldo(td):
        return _fmt_td(td)

    @app.template_filter("fmt_duracao")
    def fmt_duracao(td):
        return _fmt_dur(td)

    @app.after_request
    def cabecalhos_seguranca(resp):
        # Cabeçalhos básicos de segurança (defesa em profundidade, não substituem HTTPS/Talisman).
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        return resp

    with app.app_context():
        db.create_all()

    return app
