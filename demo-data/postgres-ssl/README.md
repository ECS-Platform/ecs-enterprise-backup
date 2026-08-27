# postgres-demo TLS

The `postgres-demo` (and `pq-postgres-demo`) containers start with `ssl=on`.
They need a self-signed cert/key pair in `./certs/` (git-ignored).

## One-time cert generation

```bash
mkdir -p demo-data/postgres-ssl/certs
openssl req -new -x509 -days 3650 -nodes \
  -keyout demo-data/postgres-ssl/certs/server.key \
  -out    demo-data/postgres-ssl/certs/server.crt \
  -subj "/CN=postgres-demo"
chmod 600 demo-data/postgres-ssl/certs/server.key
```

`ssl-entrypoint.sh` runs as root inside the container, copies these into
`/var/lib/postgresql/ssl/` as the `postgres` user with `0600` on the key
(postgres refuses to start otherwise), then execs the stock entrypoint.

## Apply

```bash
docker compose up -d --force-recreate postgres-demo
docker exec -it postgres-demo psql -U ecs_user -d ecs_demo -c "SHOW ssl;"
```
