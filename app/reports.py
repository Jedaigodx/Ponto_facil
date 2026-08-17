import csv
import io
from datetime import date

from flask import Blueprint, render_template, request, send_file, current_app
from flask_login import login_required, current_user

from app.calculations import resumo_periodo, limites_semana, limites_mes, limites_ano
from app.forms import RelatorioForm

bp = Blueprint("reports", __name__, url_prefix="/relatorios")

NOMES_PERIODO = {"semanal": "Semanal", "mensal": "Mensal", "anual": "Anual"}


def _limites(periodo, referencia):
    if periodo == "semanal":
        return limites_semana(referencia)
    if periodo == "mensal":
        return limites_mes(referencia)
    return limites_ano(referencia)


@bp.route("/", methods=["GET", "POST"])
@login_required
def relatorios():
    form = RelatorioForm(data_referencia=date.today(), periodo="mensal", formato="pdf")
    resumo = None
    if form.validate_on_submit():
        inicio, fim = _limites(form.periodo.data, form.data_referencia.data)
        jornada_padrao = current_app.config["JORNADA_PADRAO_HORAS"]
        resumo = resumo_periodo(current_user, jornada_padrao, inicio, fim)

        if request.form.get("exportar") == "1":
            if form.formato.data == "csv":
                return _exportar_csv(resumo, inicio, fim)
            return _exportar_pdf(resumo, inicio, fim, form.periodo.data)

    return render_template("reports/relatorios.html", form=form, resumo=resumo)


def _exportar_csv(resumo, inicio, fim):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Relatório de Banco de Horas"])
    writer.writerow([current_user.nome, current_user.email])
    writer.writerow([f"Período: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}"])
    writer.writerow([])
    writer.writerow(["Data", "Entrada", "Saída", "Horas trabalhadas", "Saldo do dia", "Observação"])

    for linha in resumo["linhas"]:
        lanc = linha["lancamento"]
        writer.writerow([
            lanc.data.strftime("%d/%m/%Y"),
            lanc.hora_entrada.strftime("%H:%M"),
            lanc.hora_saida.strftime("%H:%M") if lanc.hora_saida else "em aberto",
            linha["trabalhado_fmt"],
            linha["saldo_fmt"],
            lanc.observacao or "",
        ])

    writer.writerow([])
    writer.writerow(["Total trabalhado", resumo["total_trabalhado_fmt"]])
    writer.writerow(["Saldo do período", resumo["total_saldo_fmt"]])

    mem = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
    nome_arquivo = f"relatorio_{current_user.id}_{inicio}_{fim}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=nome_arquivo)


def _exportar_pdf(resumo, inicio, fim, periodo):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()
    elementos = []

    titulo = f"Relatório {NOMES_PERIODO.get(periodo, '')} de Banco de Horas"
    elementos.append(Paragraph(titulo, estilos["Title"]))
    elementos.append(Paragraph(f"{current_user.nome} — {current_user.email}", estilos["Normal"]))
    elementos.append(Paragraph(f"Período: {inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}", estilos["Normal"]))
    elementos.append(Spacer(1, 0.6 * cm))

    dados = [["Data", "Entrada", "Saída", "Horas trabalhadas", "Saldo do dia"]]
    for linha in resumo["linhas"]:
        lanc = linha["lancamento"]
        dados.append([
            lanc.data.strftime("%d/%m/%Y"),
            lanc.hora_entrada.strftime("%H:%M"),
            lanc.hora_saida.strftime("%H:%M") if lanc.hora_saida else "em aberto",
            linha["trabalhado_fmt"],
            linha["saldo_fmt"],
        ])

    tabela = Table(dados, repeatRows=1, colWidths=[3 * cm, 2.8 * cm, 2.8 * cm, 4 * cm, 3.5 * cm])
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1C2333")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DBE2")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F8FA")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(Paragraph(f"<b>Total trabalhado:</b> {resumo['total_trabalhado_fmt']}", estilos["Normal"]))
    elementos.append(Paragraph(f"<b>Saldo do período:</b> {resumo['total_saldo_fmt']}", estilos["Normal"]))

    doc.build(elementos)
    buffer.seek(0)
    nome_arquivo = f"relatorio_{current_user.id}_{inicio}_{fim}.pdf"
    return send_file(buffer, mimetype="application/pdf", as_attachment=True, download_name=nome_arquivo)
