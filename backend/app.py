import asyncio
import csv
import io
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from backend import store
from backend.catalog import CATALOG, MODULES, MUNICIPALITY, SOURCES
from backend.ingest import refresh

load_dotenv()


async def scheduler():
    hours = max(1, float(os.getenv("REFRESH_HOURS", "24")))
    while True:
        with store.connection() as db:
            last = db.execute("SELECT started_at FROM runs ORDER BY id DESC LIMIT 1").fetchone()
        age = float("inf") if not last else (datetime.now(UTC) - datetime.fromisoformat(last[0])).total_seconds()
        if age >= hours * 3600:
            await refresh()
        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Observatório Municipal de Turvo/PR", version="1.0.0", lifespan=lifespan)
cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None
if cors_origins or cors_origin_regex:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=cors_origin_regex,
        allow_methods=["GET", "HEAD"],
        allow_headers=["Accept", "Content-Type"],
        allow_credentials=False,
    )


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"
    )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "public, max-age=60"
    return response


@app.get("/api/health")
def health():
    with store.connection() as db:
        last = db.execute("SELECT started_at,finished_at,status FROM runs ORDER BY id DESC LIMIT 1").fetchone()
    return {"status": "ok", "lastRun": dict(last) if last else None}


@app.get("/api/sources")
def sources():
    return {
        "sources": SOURCES,
        "catalog": CATALOG,
        "municipality": MUNICIPALITY,
        "mcpRevision": "2efb258370b125bbf190884283ae10f209b9d335",
    }


@app.get("/api/indicators")
def indicators():
    cache = store.read_all()
    data = []
    ttl = max(1, float(os.getenv("REFRESH_HOURS", "24"))) * 3600
    for item in CATALOG:
        saved = cache.get(item["id"], {})
        payload = json.loads(saved["payload"]) if saved.get("payload") else {}
        success = saved.get("success_at")
        age = (datetime.now(UTC) - datetime.fromisoformat(success)).total_seconds() if success else None
        state = "pending" if not item["tool"] and not success else "unavailable"
        if success:
            state = "stale" if saved.get("error") or age > ttl else "available"
        data.append(
            {
                **item,
                **payload,
                "status": state,
                "sourceInfo": SOURCES[item["source"]],
                "updatedAt": success,
                "attemptedAt": saved.get("attempt_at"),
                "error": saved.get("error"),
                "value": payload.get("value"),
                "period": payload.get("period"),
                "points": payload.get("points", []),
                "rows": payload.get("rows", []),
            }
        )
    return {"municipality": MUNICIPALITY, "modules": MODULES, "indicators": data, "generatedAt": store.now()}


@app.get("/api/comparison")
def comparison():
    row = store.read_all().get("comparison", {})
    payload = json.loads(row["payload"]) if row.get("payload") else {}
    success = row.get("success_at")
    expired = (
        success
        and (datetime.now(UTC) - datetime.fromisoformat(success)).total_seconds()
        > max(1, float(os.getenv("REFRESH_HOURS", "24"))) * 3600
    )
    return {
        **payload,
        "updatedAt": success,
        "status": ("stale" if row.get("error") or expired else "available") if payload else "unavailable",
    }


@app.get("/api/export/{indicator_id}")
def export(indicator_id: str):
    item = next((x for x in indicators()["indicators"] if x["id"] == indicator_id), None)
    if not item:
        raise HTTPException(404, "Indicador não encontrado")
    if not item.get("updatedAt"):
        raise HTTPException(503, "Nenhum dado validado disponível")
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(["municipio_ibge", "indicador", "periodo", "valor", "unidade", "fonte", "coletado_em", "status"])
    for point in item["points"]:
        writer.writerow(
            [
                "4127965",
                item["title"],
                point["period"],
                point["value"],
                item["unit"],
                item["sourceInfo"]["url"],
                item["updatedAt"],
                item["status"],
            ]
        )
    return Response(
        "\ufeff" + stream.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{indicator_id}.csv"'},
    )


# A API sempre precede os arquivos do dashboard; não aceita escritas públicas.
build = Path(__file__).resolve().parent.parent / "dist"
if build.exists():
    app.mount("/", StaticFiles(directory=build, html=True), name="dashboard")
