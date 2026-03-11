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
- `WS /api/v1/ws/live/{alerta_id}?role=citizen|autoridade&token=` (ou `&device_id=` para anónimos) – **Signaling WebRTC** para transmissão em direto (câmara+mic do cidadão para as autoridades). Mensagens: `offer`, `answer`, `ice`.

### Gravação e transmissão em direto da ocorrência

- **Relatório vídeo:** Enquanto o cidadão tem uma ocorrência ativa, o app grava vídeo+áudio. Ao cancelar ou concluir, o ficheiro é enviado para o backend.
- `POST /api/v1/alertas/{id}/relatorio-video` – Upload do vídeo-relatório (multipart: `file`, opcional `device_id` para anónimos). Guardado em `uploads/relatorios/{id}/` e registado em `midia_ocorrencia`.
- **Ver em direto (autoridade):** Abrir no browser `GET /api/v1/live-viewer?alerta_id=1&token=JWT` (token de autoridade). A página conecta ao WebSocket de signaling e recebe o stream WebRTC do cidadão (quando o app publicar o stream; no mobile isso requer **development build** e `react-native-webrtc`).
- Ficheiros de upload servidos em `/api/v1/uploads/` (ex.: `/api/v1/uploads/relatorios/1/xxx.mp4`).

## Documentação

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Notificações WhatsApp (cuidador) – QuePasa

O backend pode enviar mensagens WhatsApp ao **contacto de emergência tipo cuidador** através do [QuePasa](https://github.com/nocodeleaks/quepasa):

1. **Horários de medicação** – Sempre que o cidadão adiciona um medicamento em Cuidados especiais, o cuidador recebe uma mensagem com a lista de medicamentos e horários.
2. **Alerta após 3 doses ignoradas** – Quando o cidadão não toma a medicação 3 vezes seguidas, as autoridades são notificadas e o cuidador recebe um WhatsApp a avisar que as autoridades foram notificadas e que deve preocupar-se.

### Configuração

1. **Instalar e correr o QuePasa (Docker)**  
   No seu computador (com Docker instalado):
   ```bash
   git clone https://github.com/nocodeleaks/quepasa.git
   cd quepasa/docker
   ```
   Se não existir ficheiro `.env`, crie um com as variáveis necessárias (ex.: `DOCKER_NETWORK=quepasa_network`, `QUEPASA_EXTERNAL_PORT=31000`, `QUEPASA_INTERNAL_PORT=31000`, `DOMAIN=localhost`, `DBDATABASE=quepasa_whatsmeow`, `DBUSER=quepasa`, `DBPASSWORD=...`, `MASTERKEY=...`, `SIGNING_SECRET=...`, `ACCOUNTSETUP=true`, `DBDRIVER=postgres`, `DBHOST=postgres`, `DBPORT=5432`). Pode usar como referência o `.env.example` em `quepasa/src/` ou a documentação em `quepasa/docker/docker.md`.
   ```bash
   docker compose up -d
   # ou: docker-compose up -d
   ```
2. **Ligar uma conta WhatsApp**  
   Abra no browser `http://localhost:31000` (ou o URL do seu QuePasa), faça login se for pedido, escaneie o QR Code com o WhatsApp e, após ligar, copie o **token** da sessão (na interface do QuePasa).
3. **Configurar o backend**  
   No `.env` do **Sos_Angola_backend** defina:
   - `QUEPASA_BASE_URL=http://localhost:31000` (ou o URL onde o QuePasa está a correr)
   - `QUEPASA_TOKEN=<token que copiou do QuePasa>`

Se `QUEPASA_BASE_URL` ou `QUEPASA_TOKEN` estiverem vazios, as notificações WhatsApp ao cuidador são ignoradas (o resto da app funciona normalmente).

## Próximos passos sugeridos

- Upload de fotos/vídeos de ocorrências (endpoint de upload + tabela `midia_ocorrencia`)
- Acompanhamento (pacientes/idosos): notificações “está tudo bem?” e última localização
- Push (FCM) para notificações no telemóvel
- Províncias e municípios: seed de dados de Angola
