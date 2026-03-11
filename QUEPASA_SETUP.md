# Configuração QuePasa (WhatsApp) para SOS Angola

Passo a passo para instalar o QuePasa, ligar uma conta WhatsApp e configurar o backend para enviar mensagens ao cuidador.

## 1. Instalar e correr o QuePasa

Requisito: **Docker** instalado (Docker Desktop no Windows ou `docker` + `docker compose` no Linux/Mac).

```bash
git clone https://github.com/nocodeleaks/quepasa.git
cd quepasa/docker
```

- Se na pasta `quepasa/docker` já existir um ficheiro **`.env`** (por exemplo criado com as variáveis necessárias), use-o.
- Caso contrário, crie um ficheiro `.env` nessa pasta com pelo menos:
  - `DOCKER_NETWORK=quepasa_network`
  - `QUEPASA_EXTERNAL_PORT=31000`
  - `QUEPASA_INTERNAL_PORT=31000`
  - `DOMAIN=localhost`
  - `DBDATABASE=quepasa_whatsmeow`
  - `DBUSER=quepasa`
  - `DBPASSWORD=<senha segura>`
  - `MASTERKEY=<chave mestra>`
  - `SIGNING_SECRET=<segredo para JWT>`
  - `ACCOUNTSETUP=true`
  - `DBDRIVER=postgres`
  - `DBHOST=postgres`
  - `DBPORT=5432`

Referência completa: `quepasa/src/.env.example` e `quepasa/docker/docker.md`.

Subir os contentores:

```bash
docker compose up -d
# ou, se tiver o binário antigo: docker-compose up -d
```

Verificar: `docker compose ps` (ou `docker-compose ps`). O QuePasa deve estar a escutar na porta **31000**.

## 2. Ligar uma conta WhatsApp e obter o token

1. Abra no browser: **http://localhost:31000** (ou o URL onde o QuePasa está).
2. Se for pedido, faça login (utilizador/senha definidos no `.env` do QuePasa, ex.: `USER`/`PASSWORD`).
3. Siga os passos na interface para **ligar uma conta WhatsApp** (escanear o QR Code com o telemóvel).
4. Após a ligação, na interface do QuePasa deve aparecer a **sessão** e o **token** dessa sessão. **Copie o token** (será usado no backend).

## 3. Configurar o .env do backend (Sos_Angola_backend)

No ficheiro **`.env`** na raiz do projeto **Sos_Angola_backend** (não só no `.env.example`), defina:

```env
QUEPASA_BASE_URL=http://localhost:31000
QUEPASA_TOKEN=<token que copiou do QuePasa>
```

- Se o QuePasa estiver noutro servidor ou porta, use esse URL em `QUEPASA_BASE_URL` (ex.: `http://192.168.1.10:31000`).
- Reinicie o backend após alterar o `.env`.

Se `QUEPASA_BASE_URL` ou `QUEPASA_TOKEN` estiverem vazios, o backend não envia mensagens WhatsApp (o resto da aplicação funciona normalmente).

## Resumo

| Passo | Onde | Ação |
|-------|------|------|
| 1 | `quepasa/docker` | `docker compose up -d` (ou `docker-compose up -d`) |
| 2 | Browser | Abrir http://localhost:31000 → ligar WhatsApp → copiar token |
| 3 | `Sos_Angola_backend/.env` | `QUEPASA_BASE_URL=http://localhost:31000` e `QUEPASA_TOKEN=<token>` |
