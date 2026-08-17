from datetime import datetime, date, time, timedelta

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    matricula = db.Column(db.String(40), unique=True, nullable=True)
    senha_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Jornada diária específica do usuário (horas decimais). Se nulo, usa o padrão do sistema.
    jornada_diaria_horas = db.Column(db.Float, nullable=True)

    # Foto de perfil armazenada como base64 (evita depender de disco persistente no Railway)
    foto_perfil = db.Column(db.Text, nullable=True)

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    lancamentos = db.relationship(
        "TimeEntry", backref="usuario", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_senha(self, senha_texto):
        self.senha_hash = generate_password_hash(senha_texto)

    def checar_senha(self, senha_texto):
        return check_password_hash(self.senha_hash, senha_texto)

    def jornada_horas(self, jornada_padrao_sistema):
        return self.jornada_diaria_horas if self.jornada_diaria_horas else jornada_padrao_sistema

    def __repr__(self):
        return f"<User {self.email}>"


class TimeEntry(db.Model):
    """Um lançamento de ponto referente a um dia trabalhado."""

    __tablename__ = "time_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    data = db.Column(db.Date, nullable=False, default=date.today, index=True)
    hora_entrada = db.Column(db.Time, nullable=False)
    hora_saida = db.Column(db.Time, nullable=True)  # pode ficar em aberto até o lançamento da saída

    observacao = db.Column(db.String(255), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pausas = db.relationship(
        "BreakEntry", backref="lancamento", lazy="joined", cascade="all, delete-orphan",
        order_by="BreakEntry.saida"
    )

    __table_args__ = (
        db.UniqueConstraint("user_id", "data", name="uq_usuario_data"),
    )

    # ---- Cálculos ----

    def duracao_pausas(self):
        """Retorna timedelta somando todas as pausas concluídas (com retorno lançado)."""
        total = timedelta()
        for pausa in self.pausas:
            if pausa.retorno:
                total += datetime.combine(date.min, pausa.retorno) - datetime.combine(date.min, pausa.saida)
        return total

    def horas_trabalhadas(self):
        """Retorna timedelta de horas efetivamente trabalhadas no dia, ou None se ainda em aberto."""
        if not self.hora_saida:
            return None
        bruto = datetime.combine(date.min, self.hora_saida) - datetime.combine(date.min, self.hora_entrada)
        if bruto.total_seconds() < 0:
            bruto += timedelta(days=1)  # cobre turno que vira a virada da meia-noite
        return bruto - self.duracao_pausas()

    def em_aberto(self):
        return self.hora_saida is None

    def saldo_dia(self, jornada_padrao_horas):
        """Retorna timedelta de saldo (positivo ou negativo) em relação à jornada padrão."""
        trabalhado = self.horas_trabalhadas()
        if trabalhado is None:
            return timedelta()
        jornada = timedelta(hours=jornada_padrao_horas)
        return trabalhado - jornada

    def __repr__(self):
        return f"<TimeEntry {self.data} user={self.user_id}>"


class BreakEntry(db.Model):
    """Uma pausa (almoço, lanche, outro) dentro de um lançamento de ponto."""

    __tablename__ = "break_entries"

    id = db.Column(db.Integer, primary_key=True)
    time_entry_id = db.Column(db.Integer, db.ForeignKey("time_entries.id"), nullable=False, index=True)

    tipo = db.Column(db.String(20), nullable=False, default="almoco")  # almoco | lanche | outro
    saida = db.Column(db.Time, nullable=False)
    retorno = db.Column(db.Time, nullable=True)

    def __repr__(self):
        return f"<BreakEntry {self.tipo} {self.saida}-{self.retorno}>"


def formatar_timedelta(td: timedelta) -> str:
    """Formata um timedelta (pode ser negativo) como '+HH:MM' ou '-HH:MM'."""
    total_minutos = int(td.total_seconds() // 60)
    sinal = "-" if total_minutos < 0 else "+"
    total_minutos = abs(total_minutos)
    horas, minutos = divmod(total_minutos, 60)
    return f"{sinal}{horas:02d}:{minutos:02d}"
