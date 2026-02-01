## Run

Build the image:

```sh
docker build -t mark_it_down .
```

Run the container on port 29999:

```sh
docker run --rm -p 29999:29999 \
  -e MAX_FILE_BYTES=20971520 \
  mark_it_down
```

Example request:

```sh
curl -X POST http://localhost:29999/convert \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/file.pdf"}'
```

## Update the Docker Image

Rebuild after code changes:

```sh
docker build -t mark_it_down .
```

Stop and replace the running container:

```sh
docker stop mark_it_down || true
docker run -d --name mark_it_down -p 29999:29999 \
  -e MAX_FILE_BYTES=20971520 \
  mark_it_down
```

## Health Check

```sh
curl http://localhost:29999/health
```
