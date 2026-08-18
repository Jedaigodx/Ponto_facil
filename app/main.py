import base64
import io
from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import TimeEntry, BreakEntry, formatar_timedelta
from app.forms import LancamentoCompletoForm, PerfilForm
from app.calculations import banco_de_horas_total, resumo_periodo, limites_semana, limites_mes

bp = Blueprint("main", __name__)

TAMANHO_MAX_FOTO_PX = 512  # redimensiona fotos grandes para economizar espaço no banco


@bp.route("/")
@login_required
def dashboard():
    jornada = current_user.parametros_jornada(current_app.config)
    hoje = date.today()

    saldo_total = banco_de_horas_total(current_user, jornada)
    resumo_semana = resumo_periodo(current_user, jornada, *limites_semana(hoje))
    resumo_mes = resumo_periodo(current_user, jornada, *limites_mes(hoje))

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
        jornada=jornada,
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
    jornada = current_user.parametros_jornada(current_app.config)
    return render_template("main/historico.html", paginacao=paginacao, jornada=jornada)


@bp.route("/perfil", methods=["GET", "POST"])
@login_required
def perfil():
    form = PerfilForm(obj=current_user)
    if request.method == "GET":
        form.almoco_padrao_minutos.data = current_user.almoco_padrao_minutos
        form.pausas_padrao_minutos.data = current_user.pausas_padrao_minutos

    if form.validate_on_submit():
        current_user.nome = form.nome.data.strip()
        current_user.jornada_diaria_horas = form.jornada_diaria_horas.data or None
        current_user.almoco_padrao_minutos = (
            int(form.almoco_padrao_minutos.data) if form.almoco_padrao_minutos.data is not None else None
        )
        current_user.pausas_padrao_minutos = (
            int(form.pausas_padrao_minutos.data) if form.pausas_padrao_minutos.data is not None else None
        )

        arquivo = form.foto.data
        if arquivo:
            resultado = _processar_foto(arquivo)
            if resultado is None:
                flash("O arquivo enviado não parece ser uma imagem válida.", "erro")
                return render_template("main/perfil.html", form=form)
            current_user.foto_perfil = resultado

        db.session.commit()
        flash("Perfil atualizado.", "sucesso")
        return redirect(url_for("main.perfil"))

    return render_template("main/perfil.html", form=form)


def _processar_foto(arquivo):
    """Valida que o upload é realmente uma imagem, redimensiona e remove metadados
    (EXIF pode conter geolocalização), antes de guardar como base64."""
    from PIL import Image, UnidentifiedImageError

    conteudo = arquivo.read()
    try:
        img = Image.open(io.BytesIO(conteudo))
        img.verify()  # levanta exceção se não for uma imagem válida
        img = Image.open(io.BytesIO(conteudo))  # verify() invalida o objeto; reabrir para uso
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None

    img.thumbnail((TAMANHO_MAX_FOTO_PX, TAMANHO_MAX_FOTO_PX))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)  # re-salvar descarta EXIF/metadados originais
    codificado = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{codificado}"
