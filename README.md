## Run

Build the image:

```sh
docker build -t markitdown-api .
```

Run the container on port 29999:

```sh
docker run --rm -p 29999:29999 markitdown-api
```

Example request:

```sh
curl -X POST http://localhost:29999/convert \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/file.pdf"}'
```
