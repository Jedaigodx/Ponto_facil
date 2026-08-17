from datetime import timedelta, date
from calendar import monthrange

from app.models import TimeEntry, formatar_timedelta


def banco_de_horas_total(user, jornada_padrao_horas):
    """Soma o saldo (positivo/negativo) de TODOS os lançamentos fechados do usuário."""
    jornada = user.jornada_horas(jornada_padrao_horas)
    total = timedelta()
    for lanc in user.lancamentos.filter(TimeEntry.hora_saida.isnot(None)).all():
        total += lanc.saldo_dia(jornada)
    return total


def resumo_periodo(user, jornada_padrao_horas, data_inicio, data_fim):
    """Retorna lista de lançamentos no período + totais (trabalhado, saldo)."""
    jornada = user.jornada_horas(jornada_padrao_horas)
    lancamentos = (
        user.lancamentos
        .filter(TimeEntry.data >= data_inicio, TimeEntry.data <= data_fim)
        .order_by(TimeEntry.data.asc())
        .all()
    )

    total_trabalhado = timedelta()
    total_saldo = timedelta()
    linhas = []

    for lanc in lancamentos:
        trabalhado = lanc.horas_trabalhadas()
        saldo = lanc.saldo_dia(jornada) if trabalhado is not None else timedelta()
        if trabalhado is not None:
            total_trabalhado += trabalhado
            total_saldo += saldo
        linhas.append({
            "lancamento": lanc,
            "trabalhado": trabalhado,
            "trabalhado_fmt": formatar_timedelta(trabalhado) if trabalhado is not None else "em aberto",
            "saldo": saldo,
            "saldo_fmt": formatar_timedelta(saldo) if trabalhado is not None else "-",
        })

    return {
        "linhas": linhas,
        "total_trabalhado": total_trabalhado,
        "total_trabalhado_fmt": formatar_timedelta(total_trabalhado),
        "total_saldo": total_saldo,
        "total_saldo_fmt": formatar_timedelta(total_saldo),
        "jornada_padrao": jornada,
        "dias_uteis_considerados": len(lancamentos),
    }


def limites_semana(referencia: date):
    inicio = referencia - timedelta(days=referencia.weekday())  # segunda-feira
    fim = inicio + timedelta(days=6)
    return inicio, fim


def limites_mes(referencia: date):
    inicio = referencia.replace(day=1)
    ultimo_dia = monthrange(referencia.year, referencia.month)[1]
    fim = referencia.replace(day=ultimo_dia)
    return inicio, fim


def limites_ano(referencia: date):
    return date(referencia.year, 1, 1), date(referencia.year, 12, 31)
