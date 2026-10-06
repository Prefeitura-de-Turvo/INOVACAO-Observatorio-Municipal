"""Importa pontuações anuais do IDAN-M extraídas de publicação/extrato oficial do Sebrae/PR.

Uso: uv run python -m backend.import_idan_m arquivo.csv --source-url URL_SEBRAE --sha256 HASH
O layout aceito é CSV UTF-8 delimitado por ; com colunas codigo_ibge, ano, pontuacao.
O arquivo de origem deve conter a série oficial de Turvo; não estima notas nem eixos.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlparse

from backend import store


def parse(stream):
    reader = csv.DictReader(stream, delimiter=";")
    required = {"codigo_ibge", "ano", "pontuacao"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("Layout IDAN-M não homologado: exige codigo_ibge;ano;pontuacao")
    points = {}
    scanned = 0
    for row in reader:
        scanned += 1
        code = (row.get("codigo_ibge") or "").strip()
        if code not in {"4127965", "412796"}:
            continue
        try:
            year = int(row["ano"])
            value = float((row["pontuacao"] or "").replace(",", "."))
        except (TypeError, ValueError) as error:
            raise ValueError("Ano ou pontuação inválidos na linha de Turvo") from error
        if not 1985 <= year <= 2100 or not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError("Ano ou pontuação fora do domínio esperado (0–100)")
        if year in points:
            raise ValueError(f"Pontuação duplicada para Turvo no ano {year}")
        points[year] = value
    if scanned == 0 or not points:
        raise ValueError("O arquivo não contém pontuações anuais de Turvo (IBGE 4127965)")
    return [{"period": str(year), "value": points[year]} for year in sorted(points)], scanned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    parsed = urlparse(args.source_url)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not (host == "sebraepr.com.br" or host.endswith(".sebraepr.com.br") or host == "agenciasebrae.com.br" or host.endswith(".agenciasebrae.com.br")):
        raise ValueError("A proveniência deve apontar a uma publicação oficial do Sebrae/PR")
    digest = hashlib.sha256()
    with args.file.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != args.sha256.lower():
        raise ValueError("Hash divergente: publicação bloqueada")
    with args.file.open(encoding="utf-8-sig", newline="") as stream:
        points, scanned = parse(stream)
    previous = store.read_all().get("idan_m", {})
    if previous.get("payload"):
        old_payload = json.loads(previous["payload"])
        merged = {point["period"]: point["value"] for point in old_payload.get("points", [])}
        merged.update({point["period"]: point["value"] for point in points})
        points = [{"period": year, "value": merged[year]} for year in sorted(merged)]
    rows = [{"Ano": point["period"], "Pontuação IDAN-M": point["value"]} for point in points]
    store.save(
        "idan_m",
        {
            "value": points[-1]["value"],
            "period": points[-1]["period"],
            "points": points,
            "rows": rows,
            "endpoint": args.source_url,
            "origin": "Publicação/extrato oficial Sebrae/PR importado localmente",
            "note": "Pontuações anuais do IDAN-M para Turvo (IBGE 4127965); origem e arquivo registrados para auditoria.",
        },
        {
            "sourceUrl": args.source_url,
            "sha256": digest.hexdigest(),
            "scanned": scanned,
            "municipality": "4127965",
            "method": "Importação de pontuações anuais IDAN-M de publicação/extrato oficial Sebrae/PR.",
        },
    )
    print(f"IDAN-M: {len(points)} pontuações anuais de Turvo validadas e armazenadas.")


if __name__ == "__main__":
    main()
