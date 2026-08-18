import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")

 
    _db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'dev.db')}")
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

 
    JORNADA_PADRAO_HORAS = float(os.environ.get("JORNADA_PADRAO_HORAS", "8"))

 
    ALMOCO_PADRAO_MINUTOS = int(os.environ.get("ALMOCO_PADRAO_MINUTOS", "60"))
    PAUSAS_PADRAO_MINUTOS = int(os.environ.get("PAUSAS_PADRAO_MINUTOS", "15"))

   
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "1") == "1"

    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  
  
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
