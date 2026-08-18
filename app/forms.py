from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, DateField, TimeField, SelectField, TextAreaField, FloatField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, NumberRange


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    lembrar = BooleanField("Manter conectado")


class RegisterForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=160)])
    matricula = StringField("Matrícula (opcional)", validators=[Optional(), Length(max=40)])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=8, message="Mínimo de 8 caracteres.")])
    confirmar_senha = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", message="As senhas não coincidem.")],
    )


class LancamentoCompletoForm(FlaskForm):
    """Lançar um dia inteiro de uma vez (usado quando a pessoa registra depois do ocorrido)."""
    data = DateField("Data", validators=[DataRequired()], render_kw={"type": "date"})
    hora_entrada = TimeField("Horário de entrada", validators=[DataRequired()], render_kw={"type": "time"})
    pausa1_saida = TimeField("Pausa - saiu às", validators=[Optional()], render_kw={"type": "time"})
    pausa1_retorno = TimeField("Pausa - retornou às", validators=[Optional()], render_kw={"type": "time"})
    pausa2_saida = TimeField("2ª pausa - saiu às", validators=[Optional()], render_kw={"type": "time"})
    pausa2_retorno = TimeField("2ª pausa - retornou às", validators=[Optional()], render_kw={"type": "time"})
    hora_saida = TimeField("Horário de saída", validators=[Optional()], render_kw={"type": "time"})
    observacao = StringField("Observação (opcional)", validators=[Optional(), Length(max=255)])


class PerfilForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(max=120)])
    jornada_diaria_horas = FloatField(
        "Jornada diária (horas)", validators=[Optional(), NumberRange(min=1, max=16)]
    )
    almoco_padrao_minutos = IntegerField(
        "Pausa de almoço tolerada (minutos)",
        validators=[Optional(), NumberRange(min=0, max=240, message="Entre 0 e 240 minutos.")],
    )
    pausas_padrao_minutos = IntegerField(
        "Outras pausas toleradas por dia (minutos)",
        validators=[Optional(), NumberRange(min=0, max=120, message="Entre 0 e 120 minutos.")],
    )
    foto = FileField("Foto de perfil", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png"], "Apenas imagens JPG ou PNG.")])


class RelatorioForm(FlaskForm):
    periodo = SelectField(
        "Período",
        choices=[("semanal", "Semanal"), ("mensal", "Mensal"), ("anual", "Anual")],
        validators=[DataRequired()],
    )
    data_referencia = DateField("Data de referência", validators=[DataRequired()], render_kw={"type": "date"})
    formato = SelectField(
        "Formato",
        choices=[("pdf", "PDF"), ("csv", "CSV / Excel")],
        validators=[DataRequired()],
    )
