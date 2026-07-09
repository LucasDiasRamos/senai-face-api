# Senai Face API

API local de reconhecimento facial com FastAPI, SQLite e InsightFace.

## Rodando com Docker

Suba tudo com:

```bash
docker compose up -d --build
```

A API fica exposta pelo Nginx em:

- `http://localhost:8080/health`
- `http://localhost:8080/api/health`
- `http://localhost:8080/docs`
- `http://localhost:8080/frontend`
- `http://localhost:8080/`

## Endpoints principais

- `POST /people`
- `PUT /people/{person_id}`
- `DELETE /people/{person_id}`
- `GET /units`
- `POST /people/{person_id}/photo`
- `POST /recognize`
- `POST /checkin-face`
- `POST /checkin-manual`
- `GET /checkins`
- `DELETE /checkins/{checkin_id}`
- `GET /checkins/export`
- `GET /logs`

As mesmas rotas também respondem com prefixo `/api`, por exemplo `POST /api/checkin-face`.

## Unidades

As unidades são carregadas do arquivo `unidades.txt` na raiz do projeto e sincronizadas com a tabela `units` no startup da aplicação.

- `GET /units` lista as unidades oficiais
- `POST /people` aceita `unit_id` no formulário
- `POST /enroll` aceita `unit_id` no formulário
- `POST /checkin-face` aceita `unit_id` no formulário multipart
- `POST /checkin-manual` aceita `unit_id` no formulário

Para trocar a porta pública, copie o exemplo de ambiente e ajuste `NGINX_PORT`:

```bash
cp .env.example .env
```

Depois edite `.env` e suba novamente:

```bash
docker compose up -d
```

## Persistência

O banco SQLite fica em `./data/faces.db`, montado dentro do container em `/app/data/faces.db`.

Os modelos do InsightFace ficam no volume Docker `senai-face-api_insightface-cache`. No primeiro start a aplicação pode demorar um pouco porque baixa o modelo `buffalo_l`.

## Comandos úteis

```bash
docker compose ps
docker compose logs -f
docker compose down
```
