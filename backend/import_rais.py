"""RAIS suplementar: processa microdados oficiais locais sem publicar dados pessoais.

Uso: uv run python -m backend.import_rais arquivo.txt --year 2024
     --source-url URL_OFICIAL --sha256 HASH_PUBLICADO_OU_VERIFICADO
A obtenção do arquivo e a conferência do hash são responsabilidades do operador.
Detecta o layout legado (CSV ; separado) e o layout 2024+ (CSV , com nomes atualizados).
Não existe API RAIS no catálogo MCP inspecionado; não simulamos uma.
"""

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

from backend import store


def aggregate(stream):
    sample = stream.read(8192)
    stream.seek(0)
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=";,").delimiter
    except csv.Error as error:
        raise ValueError("Separador do arquivo RAIS não reconhecido") from error
    reader = csv.DictReader(stream, delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("Arquivo RAIS sem cabeçalho")

    def normalized(value):
        value = unicodedata.normalize("NFKD", value.casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]", "", value)

    fields = {normalized(name): name for name in reader.fieldnames}
    municipality_field = next(
        (name for key, name in fields.items() if "municipio" in key and ("codigo" in key or key == "municipio")),
        None,
    )
    active_field = next(
        (name for key, name in fields.items() if "vinculoativo3112" in key),
        None,
    )
    if not municipality_field or not active_field:
        raise ValueError("Layout RAIS não homologado: exige município e vínculo ativo em 31/12")
    count, scanned = 0, 0
    for row in reader:
        scanned += 1
        municipality = re.sub(r"\D", "", (row.get(municipality_field) or ""))
        active = (row.get(active_field) or "").strip().upper()
        if municipality.lstrip("0") in {"412796", "4127965"}:
            if active not in {"0", "1", "SIM", "NÃO", "NAO", "S", "N"}:
                raise ValueError("Código de vínculo ativo não reconhecido")
            count += int(active in {"1", "SIM", "S"})
    if not scanned:
        raise ValueError("Arquivo sem registros")
    return count, scanned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--encoding", default="auto", help="auto, utf-8-sig ou latin-1")
    args = parser.parse_args()
    source = urlparse(args.source_url)
    host = source.hostname or ""
    if source.scheme not in {"https", "ftp"} or not (host.endswith(".gov.br") or host == "gov.br"):
        raise ValueError("Proveniência deve apontar a uma fonte governamental oficial")
    if not 1985 <= args.year <= 2100:
        raise ValueError("Ano inválido")
    digest = hashlib.sha256()
    with args.file.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != args.sha256.lower():
        raise ValueError("Hash divergente: publicação bloqueada")
    encoding = args.encoding
    if encoding == "auto":
        with args.file.open("rb") as file:
            sample = file.read(8192)
        try:
            sample.decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            encoding = "latin-1"
    if encoding not in {"utf-8", "utf-8-sig", "latin-1", "cp1252"}:
        raise ValueError("Encoding não homologado")
    with args.file.open(encoding=encoding, newline="") as stream:
        value, scanned = aggregate(stream)
    period = str(args.year)
    previous = store.read_all().get("formal_jobs", {})
    points = {}
    if previous.get("payload"):
        points.update(
            {
                point["period"]: point["value"]
                for point in json.loads(previous["payload"]).get("points", [])
            }
        )
    points[period] = value
    series = [{"period": year, "value": points[year]} for year in sorted(points)]
    current = series[-1]
    evidence = {
        "sourceUrl": args.source_url,
        "sha256": digest.hexdigest(),
        "scanned": scanned,
        "municipality": "4127965",
        "method": "RAIS vínculos ativos em 31/12, layout legado ou layout 2024+",
    }
    store.save(
        "formal_jobs",
        {
            "value": current["value"],
            "period": current["period"],
            "points": series,
            "rows": [{"Ano": point["period"], "Vínculos ativos em 31/12": point["value"]} for point in series],
            "endpoint": args.source_url,
            "origin": "RAIS oficial: importação suplementar validada por operador, fora do MCP Brasil",
            "note": "Arquivo e ano devem ser conferidos pelo operador; hash atesta integridade, não autenticidade.",
        },
        evidence,
    )
    print(f"RAIS {period}: agregado municipal armazenado, {scanned} linhas processadas. Microdados não publicados.")


if __name__ == "__main__":
    main()
