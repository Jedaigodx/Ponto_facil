from datetime import timedelta, date
from calendar import monthrange

from app.models import TimeEntry, formatar_timedelta, formatar_duracao


def banco_de_horas_total(user, jornada):
    """Soma o saldo (positivo/negativo) de TODOS os lançamentos fechados do usuário."""
    total = timedelta()
    for lanc in user.lancamentos.filter(TimeEntry.hora_saida.isnot(None)).all():
        total += lanc.saldo_dia(jornada)
    return total


def resumo_periodo(user, jornada, data_inicio, data_fim):
    """Retorna lista de lançamentos no período + totais (trabalhado, saldo, pausas)."""
    lancamentos = (
        user.lancamentos
        .filter(TimeEntry.data >= data_inicio, TimeEntry.data <= data_fim)
        .order_by(TimeEntry.data.asc())
        .all()
    )

    total_trabalhado = timedelta()
    total_saldo = timedelta()
    total_excesso_pausas = timedelta()
    linhas = []

    for lanc in lancamentos:
        trabalhado = lanc.horas_trabalhadas()
        saldo = lanc.saldo_dia(jornada)
        almoco_dur, outras_dur = lanc.duracao_pausas_por_tipo()
        excesso = lanc.excesso_pausas(jornada)

        if trabalhado is not None:
            total_trabalhado += trabalhado
            total_saldo += saldo
            total_excesso_pausas += excesso

        linhas.append({
            "lancamento": lanc,
            "trabalhado_fmt": formatar_duracao(trabalhado) if trabalhado is not None else "em aberto",
            "saldo": saldo,
            "saldo_fmt": formatar_timedelta(saldo) if trabalhado is not None else "-",
            "almoco_fmt": formatar_duracao(almoco_dur) if almoco_dur else "-",
            "outras_pausas_fmt": formatar_duracao(outras_dur) if outras_dur else "-",
            "excesso_fmt": formatar_duracao(excesso) if excesso else "-",
        })

    return {
        "linhas": linhas,
        "total_trabalhado": total_trabalhado,
        "total_trabalhado_fmt": formatar_duracao(total_trabalhado),
        "total_saldo": total_saldo,
        "total_saldo_fmt": formatar_timedelta(total_saldo),
        "total_excesso_pausas_fmt": formatar_duracao(total_excesso_pausas),
        "jornada": jornada,
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
