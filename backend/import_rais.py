"""RAIS suplementar: processa microdados oficiais locais sem publicar dados pessoais.

Uso: uv run python -m backend.import_rais arquivo.txt --year 2024
     --source-url URL_OFICIAL --sha256 HASH_PUBLICADO_OU_VERIFICADO
A obtenção do arquivo e a conferência do hash são responsabilidades do operador.
Não existe API RAIS no catálogo MCP inspecionado; não simulamos uma.
"""

import argparse
import csv
import hashlib
from pathlib import Path
from urllib.parse import urlparse

from backend import store


def aggregate(stream):
    reader = csv.DictReader(stream, delimiter=";")
    if not reader.fieldnames or not {"Município", "Vínculo Ativo 31/12"}.issubset(reader.fieldnames):
        raise ValueError("Layout RAIS não homologado: exige Município e Vínculo Ativo 31/12")
    count, scanned = 0, 0
    for row in reader:
        scanned += 1
        municipality = row["Município"].strip()
        active = row["Vínculo Ativo 31/12"].strip()
        if municipality in {"412796", "4127965"}:
            if active not in {"0", "1"}:
                raise ValueError("Código de vínculo ativo não reconhecido")
            count += int(active)
    if not scanned:
        raise ValueError("Arquivo sem registros")
    return count, scanned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--encoding", default="latin-1")
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
    with args.file.open(encoding=args.encoding, newline="") as stream:
        value, scanned = aggregate(stream)
    period = str(args.year)
    evidence = {
        "sourceUrl": args.source_url,
        "sha256": digest.hexdigest(),
        "scanned": scanned,
        "municipality": "4127965",
        "method": "RAIS vínculos ativos em 31/12, layout municipal original",
    }
    store.save(
        "formal_jobs",
        {
            "value": value,
            "period": period,
            "points": [{"period": period, "value": value}],
            "rows": [{"Ano": period, "Vínculos ativos em 31/12": value}],
            "endpoint": args.source_url,
            "origin": "RAIS oficial: importação suplementar validada por operador, fora do MCP Brasil",
            "note": "Arquivo e ano devem ser conferidos pelo operador; hash atesta integridade, não autenticidade.",
        },
        evidence,
    )
    print(f"RAIS {period}: agregado municipal armazenado, {scanned} linhas processadas. Microdados não publicados.")


if __name__ == "__main__":
    main()
