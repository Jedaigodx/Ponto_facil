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

    # Jornada padrão diária usada para calcular o banco de horas (em horas decimais)
    JORNADA_PADRAO_HORAS = float(os.environ.get("JORNADA_PADRAO_HORAS", "8"))

    # Sessão de login
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4MB, limite de upload (foto de perfil)
