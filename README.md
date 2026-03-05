# SOS Angola Backend

API FastAPI para o sistema SOS Angola: alertas de emergência, autoridades, chat e notícias.

## Tecnologias

- **FastAPI** – API REST
- **PostgreSQL** – Base de dados
- **SQLAlchemy** – ORM
- **Pydantic** – Validação e schemas
- **JWT** – Autenticação (cidadão e autoridade)
- **WebSocket** – Alertas em tempo real para o dashboard

## Estrutura

```
Sos_Angola_backend/
├── main.py                 # Entrada da aplicação
├── requirements.txt
├── .env.example
├── app/
│   ├── config.py            # Configurações (pydantic-settings)
│   ├── database.py          # Engine e sessão SQLAlchemy
│   ├── dependencies/        # Dependências (auth: cidadão vs autoridade)
│   ├── middleware/          # Exception handlers
│   ├── models/              # Modelos SQLAlchemy
│   ├── schemas/             # Schemas Pydantic
│   ├── services/            # Lógica de negócio
│   ├── controllers/         # Rotas (auth, alertas, autoridades, etc.)
│   └── utils/               # JWT, password, ws_manager
└── scripts/
    └── criar_usuario_autoridade.py  # Seed primeiro usuário dashboard
```

## Configuração

1. **Copiar `.env.example` para `.env`** e ajustar (PostgreSQL, SECRET_KEY, etc.).

2. **Configurar o ambiente virtual (venv) e instalar dependências:**
   - **PowerShell:** `.\scripts\setup_venv.ps1`
   - **CMD:** `scripts\setup_venv.bat`
   - Ou manualmente:
     ```bash
     python -m venv .venv
     .venv\Scripts\activate   # Windows
     pip install -r requirements.txt
     ```

3. **Criar o banco de dados e as tabelas no PostgreSQL:**
   - Garanta que o PostgreSQL está a correr e que o utilizador em `.env` tem permissão para criar bases.
   - Execute: `python -m scripts.create_database`
   - O script cria a base `sos_angola` (ou o nome em `DB_NAME`) se não existir e cria todas as tabelas.

4. **Iniciar a API:** `uvicorn main:app --reload`

5. **Criar primeiro usuário autoridade (dashboard):**
   - `python -m scripts.criar_usuario_autoridade`
   - Ou definir `SOS_ADMIN_EMAIL` e `SOS_ADMIN_PASSWORD` no ambiente.

## Principais endpoints

### Público / App (sem login ou com login cidadão)

- `POST /api/v1/auth/cidadao/registro` – Registo cidadão
- `POST /api/v1/auth/cidadao/login` – Login cidadão
- `POST /api/v1/alertas/sos-rapido` – SOS rápido (só localização; pode ser anónimo)
- `GET /api/v1/noticias/` – Listar notícias publicadas

### Cidadão logado (Bearer token com role cidadao)

- `GET/PATCH /api/v1/cidadao/perfil` – Perfil (nome, idade) e contactos de emergência
- `POST /api/v1/alertas/sos-formulario` – Alerta com formulário + localização
- `POST /api/v1/alertas/alerta-familiar` – Enviar alerta a familiar com localização
- `GET /api/v1/alertas/meus` – Meus alertas
- `GET/POST /api/v1/chat/conversas` – Chat com autoridades

### Dashboard autoridades (Bearer token com role autoridade)

- `POST /api/v1/auth/autoridade/login` – Login autoridade
- `GET /api/v1/alertas/` – Listar alertas (filtros: estado, tipo)
- `GET /api/v1/alertas/{id}` – Detalhe alerta
- `PATCH /api/v1/alertas/{id}/atribuir` – Atribuir autoridade ao alerta
- `PATCH /api/v1/alertas/{id}/estado` – Atualizar estado (pendente, em_atendimento, resolvido)
- `GET /api/v1/autoridades/` – CRUD autoridades
- `GET /api/v1/autoridades/proximas?latitude=&longitude=&tipo=` – Autoridades mais próximas
- `GET/POST/PATCH/DELETE /api/v1/noticias/admin/` – CRUD notícias
- `POST /api/v1/chat/admin/conversas/{id}/mensagens` – Enviar mensagem no chat

### WebSocket

- `WS /api/v1/ws/alertas?token=` – Canal de alertas em tempo real (dashboard). Ao criar um SOS (rápido ou formulário), o backend emite `{ "evento": "novo_alerta", "alerta": {...} }`.

## Documentação

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Próximos passos sugeridos

- Upload de fotos/vídeos de ocorrências (endpoint de upload + tabela `midia_ocorrencia`)
- Acompanhamento (pacientes/idosos): notificações “está tudo bem?” e última localização
- Push (FCM) para notificações no telemóvel
- Províncias e municípios: seed de dados de Angola
