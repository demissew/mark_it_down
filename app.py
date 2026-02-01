import os
import uuid

import httpx
from fastapi import FastAPI, HTTPException
from markitdown import MarkItDown
from pydantic import BaseModel, HttpUrl

app = FastAPI()


class ConvertRequest(BaseModel):
    url: HttpUrl


@app.post("/convert")
async def convert(req: ConvertRequest) -> dict:
    tmp_path = os.path.join("/tmp", f"markitdown-{uuid.uuid4()}.pdf")
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(str(req.url))
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=400,
                    detail=f"download failed: status {resp.status_code}",
                )
            with open(tmp_path, "wb") as f:
                f.write(resp.content)

        md = MarkItDown()
        result = md.convert(tmp_path)
        return {"markdown": result.text_content}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            os.remove(tmp_path)
        except FileNotFoundError:
            pass
