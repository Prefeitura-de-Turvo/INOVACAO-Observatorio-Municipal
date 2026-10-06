import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import PythonStdioTransport, StreamableHttpTransport

from backend import store
from backend.catalog import CATALOG
from backend.normalize import normalize

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


def transport():
    if os.getenv("MCP_TRANSPORT", "stdio") == "http":
        headers = {"Authorization": "Bearer " + os.environ["MCP_TOKEN"]} if os.getenv("MCP_TOKEN") else None
        return StreamableHttpTransport(os.environ["MCP_URL"], headers=headers)
    return PythonStdioTransport(
        script_path=str(ROOT / "integration/bridge.py"), python_cmd=sys.executable, cwd=str(ROOT)
    )


async def call(client, tool, args):
    result = await client.call_tool(
        tool,
        args,
        timeout=max(300 if tool == "observatorio_pncp" else 90, float(os.getenv("MCP_TIMEOUT_SECONDS", "90"))),
    )
    if result.is_error:
        raise ValueError("MCP sinalizou erro da fonte")
    if isinstance(result.data, dict):
        return result.data
    for block in result.content:
        if getattr(block, "type", "") == "text":
            data = json.loads(block.text)
            return data.get("result", data)
    raise ValueError("MCP sem resposta estruturada")


async def refresh(only=None):
    with store.connection() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT until_at FROM locks WHERE name='ingest'").fetchone()
        if old and old[0] > time.time():
            return {"status": "already_running"}
        db.execute("INSERT OR REPLACE INTO locks VALUES('ingest',?)", (time.time() + 7200,))
        run = db.execute("INSERT INTO runs(started_at,status) VALUES(?,?)", (store.now(), "running")).lastrowid
    failures = {}
    year = int(time.strftime("%Y")) - 1
    try:
        async with Client(transport()) as client:
            tools = {t.name for t in await client.list_tools()}
            cnpj = os.getenv("MUNICIPAL_CNPJ", "")
            if not cnpj:
                try:
                    response = await call(client, "observatorio_entes", {})
                    cnpj = str(response["rows"][0].get("cnpj") or "").zfill(14)
                    if not cnpj.isdigit() or cnpj == "0" * 14:
                        cnpj = ""
                except Exception:
                    cnpj = ""
            for item in CATALOG:
                if only and item["id"] not in only:
                    continue
                if not item["tool"]:
                    continue
                try:
                    if item["tool"] not in tools:
                        raise ValueError("Extensão não disponível no servidor MCP configurado")
                    args = dict(item["args"])
                    if item["id"] in {
                        "rcl",
                        "procurement",
                        "procurement_contracts",
                        "transfers",
                        "agreements",
                        "signed_agreements",
                        "agreement_orders",
                    }:
                        args["ano"] = year
                    if item["id"] in {"procurement", "procurement_contracts", "transfers"}:
                        if len(cnpj) != 14:
                            raise ValueError("CNPJ municipal ainda não validado; configure MUNICIPAL_CNPJ")
                        args["cnpj"] = cnpj
                    response = await call(client, item["tool"], args)
                    payload = normalize(item, response)
                    store.save(item["id"], payload, response)
                except Exception as exc:
                    # Não publicar stack traces, tokens ou URLs privadas na API pública.
                    message = str(exc).split("\n")[0][:200]
                    failures[item["id"]] = message
                    store.fail(
                        item["id"], "Fonte indisponível ou resposta não homologada. Consulte o registro da execução."
                    )
            if not only or "comparison" in only:
                try:
                    response = await call(client, "observatorio_comparacao", {})
                    store.save("comparison", response, response)
                except Exception as exc:
                    failures["comparison"] = str(exc)[:200]
                    store.fail("comparison", "Comparação temporariamente indisponível")
    except Exception as exc:
        failures["mcp"] = str(exc)[:200]
        for item in CATALOG:
            if item["tool"] and (not only or item["id"] in only):
                store.fail(item["id"], "Servidor MCP indisponível")
    finally:
        with store.connection() as db:
            db.execute(
                "UPDATE runs SET finished_at=?,status=?,detail=? WHERE id=?",
                (store.now(), "partial" if failures else "success", json.dumps(failures, ensure_ascii=False), run),
            )
            db.execute("DELETE FROM locks WHERE name='ingest'")
    return {"run": run, "status": "partial" if failures else "success", "failures": failures}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(refresh(sys.argv[1:] or None)), ensure_ascii=False, indent=2))
