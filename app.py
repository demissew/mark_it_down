import logging
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException
from markitdown import MarkItDown
from pydantic import BaseModel, HttpUrl

app = FastAPI()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mark_it_down")
ALLOWED_EXTS = {".pdf", ".docx", ".pptx"}
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_BYTES", str(20 * 1024 * 1024)))
READ_CHUNK_BYTES = int(os.getenv("READ_CHUNK_BYTES", str(1024 * 1024)))


class ConvertRequest(BaseModel):
    url: HttpUrl


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/convert")
async def convert(req: ConvertRequest) -> dict:
    url_path = urlparse(str(req.url)).path
    ext = Path(url_path).suffix or ".bin"
    if ext.lower() not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"unsupported file extension: {ext}",
        )
    tmp_path = os.path.join("/tmp", f"markitdown-{uuid.uuid4()}{ext}")
    try:
        logger.info("download start url=%s tmp=%s", req.url, tmp_path)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            try:
                resp = await client.get(str(req.url), follow_redirects=True)
            except httpx.RequestError as exc:
                logger.error("download error url=%s error=%s", req.url, exc)
                raise HTTPException(
                    status_code=502,
                    detail="download failed: connection error",
                ) from exc
            if resp.status_code != 200:
                logger.error(
                    "download failed url=%s status=%s",
                    req.url,
                    resp.status_code,
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"download failed: status {resp.status_code}",
                )
            content_length = resp.headers.get("content-length")
            if content_length and int(content_length) > MAX_FILE_BYTES:
                raise HTTPException(status_code=413, detail="file too large")

            total = 0
            with open(tmp_path, "wb") as f:
                async for chunk in resp.aiter_bytes(READ_CHUNK_BYTES):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise HTTPException(status_code=413, detail="file too large")
                    f.write(chunk)
            mime_type = (
                resp.headers.get("content-type") or mimetypes.guess_type(tmp_path)[0]
            )
            if not mime_type:
                mime_type = "application/octet-stream"
            logger.info(
                "download complete url=%s status=%s bytes=%s",
                req.url,
                resp.status_code,
                total,
            )

        logger.info("convert start tmp=%s", tmp_path)
        md = MarkItDown()
        result = md.convert(tmp_path)
        logger.info(
            "convert complete tmp=%s chars=%s", tmp_path, len(result.text_content)
        )
        return {"mime_type": mime_type, "markdown": result.text_content}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "convert failed url=%s tmp=%s error=%r", req.url, tmp_path, exc
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(tmp_path)
            logger.info("cleanup complete tmp=%s", tmp_path)
        except FileNotFoundError:
            pass
