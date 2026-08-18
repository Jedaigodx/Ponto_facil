from datetime import datetime, date, time, timedelta
from collections import namedtuple

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db

# Parâmetros de jornada resolvidos (usuário -> sobrepõe padrão do sistema)
JornadaConfig = namedtuple("JornadaConfig", ["horas", "almoco_min", "pausas_min"])

MAX_TENTATIVAS_LOGIN = 5
BLOQUEIO_MINUTOS = 15


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
    # Tempo de pausa para almoço tolerado (minutos) sem descontar do banco de horas.
    almoco_padrao_minutos = db.Column(db.Integer, nullable=True)
    # Tempo total de outras pausas (lanche etc.) toleradas por dia (minutos).
    pausas_padrao_minutos = db.Column(db.Integer, nullable=True)

    # Foto de perfil armazenada como base64 (evita depender de disco persistente no Railway)
    foto_perfil = db.Column(db.Text, nullable=True)

    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Proteção contra força bruta no login
    tentativas_falhas = db.Column(db.Integer, default=0, nullable=False)
    bloqueado_ate = db.Column(db.DateTime, nullable=True)

    lancamentos = db.relationship(
        "TimeEntry", backref="usuario", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_senha(self, senha_texto):
        self.senha_hash = generate_password_hash(senha_texto)

    def checar_senha(self, senha_texto):
        return check_password_hash(self.senha_hash, senha_texto)

    def esta_bloqueado(self):
        return bool(self.bloqueado_ate and self.bloqueado_ate > datetime.utcnow())

    def registrar_falha_login(self):
        self.tentativas_falhas = (self.tentativas_falhas or 0) + 1
        if self.tentativas_falhas >= MAX_TENTATIVAS_LOGIN:
            self.bloqueado_ate = datetime.utcnow() + timedelta(minutes=BLOQUEIO_MINUTOS)

    def registrar_login_sucesso(self):
        self.tentativas_falhas = 0
        self.bloqueado_ate = None

    def parametros_jornada(self, app_config):
        """Resolve jornada/almoço/pausas do usuário, com fallback para o padrão do sistema."""
        horas = self.jornada_diaria_horas if self.jornada_diaria_horas else app_config["JORNADA_PADRAO_HORAS"]
        almoco = (
            self.almoco_padrao_minutos
            if self.almoco_padrao_minutos is not None
            else app_config["ALMOCO_PADRAO_MINUTOS"]
        )
        pausas = (
            self.pausas_padrao_minutos
            if self.pausas_padrao_minutos is not None
            else app_config["PAUSAS_PADRAO_MINUTOS"]
        )
        return JornadaConfig(horas=horas, almoco_min=almoco, pausas_min=pausas)

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

    def _bruto(self):
        """Timedelta entre entrada e saída (permanência total), ou None se em aberto."""
        if not self.hora_saida:
            return None
        bruto = datetime.combine(date.min, self.hora_saida) - datetime.combine(date.min, self.hora_entrada)
        if bruto.total_seconds() < 0:
            bruto += timedelta(days=1)  # cobre turno que vira a virada da meia-noite
        return bruto

    def duracao_pausas_por_tipo(self):
        """Retorna (duração almoço, duração outras pausas) somando apenas pausas concluídas."""
        almoco = timedelta()
        outras = timedelta()
        for pausa in self.pausas:
            if not pausa.retorno:
                continue
            duracao = datetime.combine(date.min, pausa.retorno) - datetime.combine(date.min, pausa.saida)
            if duracao.total_seconds() < 0:
                continue
            if pausa.tipo == "almoco":
                almoco += duracao
            else:
                outras += duracao
        return almoco, outras

    def duracao_pausas(self):
        almoco, outras = self.duracao_pausas_por_tipo()
        return almoco + outras

    def excesso_pausas(self, jornada: JornadaConfig):
        """Retorna o tempo de pausa que ultrapassou o tolerado (não conta a favor do funcionário)."""
        almoco_realizado, outras_realizado = self.duracao_pausas_por_tipo()
        excesso_almoco = max(timedelta(), almoco_realizado - timedelta(minutes=jornada.almoco_min))
        excesso_outras = max(timedelta(), outras_realizado - timedelta(minutes=jornada.pausas_min))
        return excesso_almoco + excesso_outras

    def horas_trabalhadas(self):
        """Tempo efetivamente trabalhado (permanência menos TODAS as pausas). Informativo."""
        bruto = self._bruto()
        if bruto is None:
            return None
        return bruto - self.duracao_pausas()

    def horas_creditadas(self, jornada: JornadaConfig):
        """Tempo considerado para o banco de horas: pausas dentro do tolerado não descontam,
        só o excesso é descontado."""
        bruto = self._bruto()
        if bruto is None:
            return None
        return bruto - self.excesso_pausas(jornada)

    def em_aberto(self):
        return self.hora_saida is None

    def saldo_dia(self, jornada: JornadaConfig):
        """Retorna timedelta de saldo (positivo ou negativo) em relação à jornada padrão."""
        creditadas = self.horas_creditadas(jornada)
        if creditadas is None:
            return timedelta()
        return creditadas - timedelta(hours=jornada.horas)

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


def formatar_duracao(td: timedelta) -> str:
    """Formata um timedelta positivo (duração simples) como 'HH:MM'."""
    total_minutos = int(td.total_seconds() // 60)
    horas, minutos = divmod(max(0, total_minutos), 60)
    return f"{horas:02d}:{minutos:02d}"
