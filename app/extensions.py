from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para continuar."
login_manager.login_message_category = "info"

# Protecao CSRF global: qualquer POST/PUT/DELETE sem token valido e rejeitado (400),
# nao apenas os formularios construidos com Flask-WTF.
csrf = CSRFProtect()
