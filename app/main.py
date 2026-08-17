import base64
from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import TimeEntry, BreakEntry, formatar_timedelta
from app.forms import LancamentoCompletoForm, PerfilForm
from app.calculations import banco_de_horas_total, resumo_periodo, limites_semana, limites_mes

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    jornada_padrao = current_app.config["JORNADA_PADRAO_HORAS"]
    hoje = date.today()

    saldo_total = banco_de_horas_total(current_user, jornada_padrao)
    resumo_semana = resumo_periodo(current_user, jornada_padrao, *limites_semana(hoje))
    resumo_mes = resumo_periodo(current_user, jornada_padrao, *limites_mes(hoje))

    lancamento_hoje = TimeEntry.query.filter_by(user_id=current_user.id, data=hoje).first()
    ultimos = (
        current_user.lancamentos.order_by(TimeEntry.data.desc()).limit(7).all()
    )

    return render_template(
        "main/dashboard.html",
        saldo_total=saldo_total,
        saldo_total_fmt=formatar_timedelta(saldo_total),
        resumo_semana=resumo_semana,
        resumo_mes=resumo_mes,
        lancamento_hoje=lancamento_hoje,
        ultimos=ultimos,
        hoje=hoje,
    )


@bp.route("/lancar", methods=["GET", "POST"])
@login_required
def lancar():
    form = LancamentoCompletoForm()
    if request.method == "GET":
        form.data.data = date.today()
    if form.validate_on_submit():
        existente = TimeEntry.query.filter_by(user_id=current_user.id, data=form.data.data).first()
        if existente:
            flash("Já existe um lançamento para esta data. Edite o lançamento existente.", "erro")
            return redirect(url_for("main.editar_lancamento", entry_id=existente.id))

        lancamento = TimeEntry(
            user_id=current_user.id,
            data=form.data.data,
            hora_entrada=form.hora_entrada.data,
            hora_saida=form.hora_saida.data or None,
            observacao=form.observacao.data or None,
        )
        db.session.add(lancamento)
        db.session.flush()

        if form.pausa1_saida.data:
            db.session.add(BreakEntry(
                time_entry_id=lancamento.id, tipo="almoco",
                saida=form.pausa1_saida.data, retorno=form.pausa1_retorno.data or None,
            ))
        if form.pausa2_saida.data:
            db.session.add(BreakEntry(
                time_entry_id=lancamento.id, tipo="lanche",
                saida=form.pausa2_saida.data, retorno=form.pausa2_retorno.data or None,
            ))

        db.session.commit()
        flash("Ponto lançado com sucesso.", "sucesso")
        return redirect(url_for("main.dashboard"))

    return render_template("main/lancar.html", form=form)


@bp.route("/lancamento/<int:entry_id>/editar", methods=["GET", "POST"])
@login_required
def editar_lancamento(entry_id):
    lancamento = TimeEntry.query.get_or_404(entry_id)
    if lancamento.user_id != current_user.id:
        abort(403)

    pausa_almoco = next((p for p in lancamento.pausas if p.tipo == "almoco"), None)
    pausa_lanche = next((p for p in lancamento.pausas if p.tipo == "lanche"), None)

    form = LancamentoCompletoForm(obj=lancamento)
    if request.method == "GET":
        if pausa_almoco:
            form.pausa1_saida.data = pausa_almoco.saida
            form.pausa1_retorno.data = pausa_almoco.retorno
        if pausa_lanche:
            form.pausa2_saida.data = pausa_lanche.saida
            form.pausa2_retorno.data = pausa_lanche.retorno

    if form.validate_on_submit():
        lancamento.hora_entrada = form.hora_entrada.data
        lancamento.hora_saida = form.hora_saida.data or None
        lancamento.observacao = form.observacao.data or None

        # Recria as pausas do zero (mais simples e evita inconsistência)
        BreakEntry.query.filter_by(time_entry_id=lancamento.id).delete()
        if form.pausa1_saida.data:
            db.session.add(BreakEntry(
                time_entry_id=lancamento.id, tipo="almoco",
                saida=form.pausa1_saida.data, retorno=form.pausa1_retorno.data or None,
            ))
        if form.pausa2_saida.data:
            db.session.add(BreakEntry(
                time_entry_id=lancamento.id, tipo="lanche",
                saida=form.pausa2_saida.data, retorno=form.pausa2_retorno.data or None,
            ))

        db.session.commit()
        flash("Lançamento atualizado.", "sucesso")
        return redirect(url_for("main.historico"))

    return render_template("main/lancar.html", form=form, editando=True, entry_id=entry_id)


@bp.route("/lancamento/<int:entry_id>/excluir", methods=["POST"])
@login_required
def excluir_lancamento(entry_id):
    lancamento = TimeEntry.query.get_or_404(entry_id)
    if lancamento.user_id != current_user.id:
        abort(403)
    db.session.delete(lancamento)
    db.session.commit()
    flash("Lançamento excluído.", "info")
    return redirect(url_for("main.historico"))


@bp.route("/historico")
@login_required
def historico():
    pagina = request.args.get("pagina", 1, type=int)
    paginacao = (
        current_user.lancamentos.order_by(TimeEntry.data.desc())
        .paginate(page=pagina, per_page=20, error_out=False)
    )
    jornada_padrao = current_app.config["JORNADA_PADRAO_HORAS"]
    return render_template("main/historico.html", paginacao=paginacao, jornada_padrao=jornada_padrao)


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    form = PerfilForm(obj=current_user)
    if form.validate_on_submit():
        current_user.nome = form.nome.data.strip()
        current_user.jornada_diaria_horas = form.jornada_diaria_horas.data or None

        arquivo = form.foto.data
        if arquivo:
            conteudo = arquivo.read()
            mime = arquivo.mimetype
            current_user.foto_perfil = f"data:{mime};base64,{base64.b64encode(conteudo).decode()}"

        db.session.commit()
        flash("Perfil atualizado.", "sucesso")
        return redirect(url_for("main.perfil"))

    return render_template("main/perfil.html", form=form)
