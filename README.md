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
- `POST /people/{person_id}/photo`
- `POST /recognize`
- `POST /checkin-face`
- `POST /checkin-manual`
- `GET /checkins`
- `DELETE /checkins/{checkin_id}`
- `GET /checkins/export`
- `GET /logs`

As mesmas rotas também respondem com prefixo `/api`, por exemplo `POST /api/checkin-face`.

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
