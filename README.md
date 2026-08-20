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

## Atualizando um banco já existente no Railway

Este pacote adicionou colunas novas na tabela `users` (jornada de almoço/pausas
configuráveis e proteção contra força bruta no login). O `db.create_all()` que
roda no boot só cria tabelas que não existem — ele **não** adiciona colunas em
tabelas já existentes. Se você já tinha feito o primeiro deploy antes dessas
mudanças, rode isto uma vez no seu Postgres do Railway (aba **Data → Query**,
ou `psql` conectado via `DATABASE_URL`):

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS almoco_padrao_minutos INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS pausas_padrao_minutos INTEGER;
ALTER TABLE users ADD COLUMN IF NOT EXISTS tentativas_falhas INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS bloqueado_ate TIMESTAMP;
```

Se o projeto ainda não tem nenhum dado real (fase de testes), o caminho mais
simples é apagar e recriar o banco Postgres no Railway e deixar o
`db.create_all()` criar tudo do zero no próximo deploy.

Se o projeto for crescer bastante, vale migrar para **Flask-Migrate/Alembic**
em vez de `db.create_all()`, para não depender de ALTER TABLE manual a cada
mudança de schema.

## Segurança — o que foi revisado e corrigido

- **CSRF**: proteção habilitada globalmente (`Flask-WTF CSRFProtect`). Antes,
  o formulário de exclusão de lançamento não tinha token CSRF — um site
  malicioso poderia induzir um usuário logado a excluir lançamentos sem saber.
  Corrigido.
- **Força bruta no login**: 5 tentativas erradas bloqueiam a conta por 15
  minutos. Antes não havia limite de tentativas.
- **Enumeração de contas**: as mensagens de erro no cadastro e no login não
  revelam mais se um e-mail específico já existe ou está bloqueado.
- **Open redirect**: o parâmetro `?next=` do login agora só aceita caminhos
  internos (`/...`), impedindo redirecionamento para sites externos.
- **Upload de foto**: o arquivo enviado é validado de verdade com Pillow (não
  só pela extensão), redimensionado e regravado como JPEG — isso descarta
  metadados EXIF (que podem conter geolocalização) e impede que um arquivo
  disfarçado de imagem seja armazenado.
- **Cookies de sessão**: `HttpOnly`, `SameSite=Lax` e `Secure` (exige HTTPS,
  que é o padrão no Railway) configurados explicitamente.
- **Debug mode**: antes o `wsgi.py` rodava com `debug=True` fixo — se alguém
  chamasse esse arquivo diretamente em produção, o depurador do Werkzeug fica
  exposto, o que permite execução remota de código. Agora é controlado por
  variável de ambiente (`FLASK_DEBUG`) e vem desligado por padrão.
- **Cabeçalhos de segurança básicos**: `X-Content-Type-Options`,
  `X-Frame-Options`, `Referrer-Policy` adicionados em todas as respostas.
- **IDOR**: já era tratado corretamente — editar/excluir lançamento sempre
  confere se o registro pertence ao usuário logado (`403` caso contrário).
- **SQL Injection / XSS**: não há SQL cru em lugar nenhum (tudo via ORM) e o
  Jinja2 escapa HTML automaticamente em todos os templates — nenhum filtro
  `|safe` é usado em conteúdo de usuário.
- **Senhas**: hash com `werkzeug.security` (PBKDF2), mínimo agora de 8
  caracteres (era 6).

### Recomendações que ficaram de fora desta rodada (próximos passos)

- **Rate limiting por IP** além do bloqueio por conta (ex.: `Flask-Limiter`),
  para dificultar ataques distribuídos entre várias contas.
- **Recuperação de senha** (fluxo de "esqueci minha senha" por e-mail) — hoje
  só um administrador poderia resetar manualmente no banco.
- **Flask-Talisman** para forçar HTTPS e um Content-Security-Policy mais
  completo (os cabeçalhos atuais são um começo, não uma CSP completa).
- **Auditoria de admin**: quando a tela de administrador existir, logar quem
  alterou o quê.



- Painel de administrador para o gestor ver o saldo de todos os funcionários
  numa tela só (hoje cada um só vê o próprio).
- Aprovação de horas extras/compensação por um superior.
- Notificação por e-mail quando o saldo negativo passar de um limite.
