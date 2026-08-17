from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User
from app.forms import LoginForm, RegisterForm

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if usuario and usuario.ativo and usuario.checar_senha(form.senha.data):
            login_user(usuario, remember=form.lembrar.data)
            destino = request.args.get("next")
            return redirect(destino or url_for("main.dashboard"))
        flash("E-mail ou senha inválidos.", "erro")

    return render_template("auth/login.html", form=form)


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("Já existe uma conta com este e-mail.", "erro")
            return render_template("auth/cadastro.html", form=form)

        usuario = User(nome=form.nome.data.strip(), email=email, matricula=form.matricula.data or None)
        usuario.set_senha(form.senha.data)

        # Primeiro usuário cadastrado no sistema vira administrador automaticamente
        if User.query.count() == 0:
            usuario.is_admin = True

        db.session.add(usuario)
        db.session.commit()
        flash("Conta criada com sucesso. Faça login para continuar.", "sucesso")
        return redirect(url_for("auth.login"))

    return render_template("auth/cadastro.html", form=form)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("auth.login"))
