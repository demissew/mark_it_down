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


class ConvertRequest(BaseModel):
    url: HttpUrl


@app.post("/convert")
async def convert(req: ConvertRequest) -> dict:
    url_path = urlparse(str(req.url)).path
    ext = Path(url_path).suffix or ".bin"
    tmp_path = os.path.join("/tmp", f"markitdown-{uuid.uuid4()}{ext}")
    try:
        logger.info("download start url=%s tmp=%s", req.url, tmp_path)
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            try:
                resp = await client.get(str(req.url))
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
            with open(tmp_path, "wb") as f:
                f.write(resp.content)
            mime_type = (
                resp.headers.get("content-type") or mimetypes.guess_type(tmp_path)[0]
            )
            if not mime_type:
                mime_type = "application/octet-stream"
            logger.info(
                "download complete url=%s status=%s bytes=%s",
                req.url,
                resp.status_code,
                len(resp.content),
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
            "convert failed url=%s tmp=%s error=%s", req.url, tmp_path, exc
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(tmp_path)
            logger.info("cleanup complete tmp=%s", tmp_path)
        except FileNotFoundError:
            pass
