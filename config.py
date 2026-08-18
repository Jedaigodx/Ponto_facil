import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

    # Railway injeta DATABASE_URL automaticamente ao adicionar um plugin Postgres.
    # SQLAlchemy exige o prefixo "postgresql://" (Railway às vezes fornece "postgres://").
    _db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'dev.db')}")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Jornada padrão diária usada para calcular o banco de horas (em horas decimais).
    # Pode ser sobrescrita por usuário na página de Perfil.
    JORNADA_PADRAO_HORAS = float(os.environ.get("JORNADA_PADRAO_HORAS", "8"))

    # Tempo de pausa (em minutos) tolerado sem descontar do banco de horas.
    # Só o que ultrapassar esses valores e descontado do saldo.
    ALMOCO_PADRAO_MINUTOS = int(os.environ.get("ALMOCO_PADRAO_MINUTOS", "60"))
    PAUSAS_PADRAO_MINUTOS = int(os.environ.get("PAUSAS_PADRAO_MINUTOS", "15"))

    # Sessao de login
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Em producao (Railway serve via HTTPS) o cookie de sessao so deve trafegar por HTTPS.
    # Defina SESSION_COOKIE_SECURE=1 (padrao) nas variaveis do Railway; use 0 apenas em dev http local.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") == "1"

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB, limite de upload (foto de perfil)

    # Debug NUNCA deve ficar ligado em producao (exposicao do werkzeug debugger = RCE).
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
