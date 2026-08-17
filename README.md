# Extrato · Horas

Sistema web para lançamento de ponto e consulta de banco de horas, feito em Flask.

## O que o sistema faz

- Login e cadastro de usuários (senha com hash, sessão via Flask-Login).
- Cada usuário só enxerga seus próprios lançamentos.
- Lançamento de ponto: entrada, pausas (almoço/lanche, com saída e retorno) e saída —
  pode ser feito depois do expediente ou durante, e editado a qualquer momento.
- Cálculo automático de horas trabalhadas por dia e saldo (positivo/negativo) em
  relação à jornada padrão (configurável globalmente e por usuário).
- Dashboard com saldo total do banco de horas, saldo da semana/mês e extrato dos
  últimos lançamentos.
- Relatórios semanais, mensais ou anuais, exportáveis em PDF ou CSV — prontos para
  entregar ao gestor.
- Foto de perfil (armazenada como base64 no banco, para não depender de disco
  persistente no Railway).

## Rodando localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ajuste SECRET_KEY; sem DATABASE_URL ele usa SQLite local
python wsgi.py
```

Acesse `http://localhost:5000`. O primeiro usuário cadastrado vira administrador
automaticamente (útil se no futuro você quiser uma área de gestão de usuários).

## Deploy no Railway

1. Suba este projeto num repositório Git (GitHub, por exemplo) e conecte no Railway
   (**New Project → Deploy from GitHub repo**).
2. No projeto do Railway, adicione um plugin **PostgreSQL** (`New → Database →
   PostgreSQL`). O Railway cria automaticamente a variável `DATABASE_URL` e a
   injeta no seu serviço web — não precisa copiar/colar nada manualmente.
3. No serviço web, defina as variáveis de ambiente:
   - `SECRET_KEY` — uma string aleatória longa (gere com `python -c "import secrets; print(secrets.token_hex(32))"`).
   - `JORNADA_PADRAO_HORAS` — opcional, padrão `8`.
4. O Railway detecta o `Procfile` (`web: gunicorn wsgi:app`) e o `requirements.txt`
   automaticamente via Nixpacks — não é necessário Dockerfile.
5. No primeiro deploy, as tabelas são criadas automaticamente (`db.create_all()`
   é chamado na inicialização da aplicação).
6. Gere um domínio público em **Settings → Networking → Generate Domain**.

### Observação sobre a foto de perfil

O sistema de arquivos do Railway não é persistente entre deploys, por isso a foto
de perfil é salva como base64 diretamente no banco de dados (funciona bem para
fotos pequenas). Se o time crescer muito ou as fotos ficarem pesadas, o próximo
passo natural é migrar para um storage externo (Cloudinary, S3, Railway Volumes).

## Estrutura do projeto

```
app/
  __init__.py       -> application factory
  extensions.py     -> db, login_manager
  models.py         -> User, TimeEntry, BreakEntry
  calculations.py   -> cálculo de horas trabalhadas e banco de horas
  forms.py           -> formulários (Flask-WTF)
  auth.py            -> blueprint de login/cadastro
  main.py             -> blueprint de dashboard/lançamento/histórico/perfil
  reports.py          -> blueprint de relatórios (PDF/CSV)
  templates/
  static/css/style.css
config.py
wsgi.py
Procfile
requirements.txt
```

## Próximos passos sugeridos

- Painel de administrador para o gestor ver o saldo de todos os funcionários
  numa tela só (hoje cada um só vê o próprio).
- Aprovação de horas extras/compensação por um superior.
- Notificação por e-mail quando o saldo negativo passar de um limite.
