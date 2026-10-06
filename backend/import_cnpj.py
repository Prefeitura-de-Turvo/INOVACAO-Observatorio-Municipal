"""Agrega o cadastro aberto nacional CNPJ da Receita Federal para Turvo.

Use somente com a edição mensal completa, com arquivos Empresas, Estabelecimentos e Simples
descompactados. O processamento mantém índices transitórios fora do cache público e grava
somente totais locais agregados por porte e CNAE principal.
"""

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

from backend import store

SOURCE_DEFAULT = "https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/cadastros"


def input_files(directory: Path) -> list[Path]:
    files = sorted(path for path in directory.rglob("*") if path.is_file())
    if not files:
        raise ValueError(f"Nenhum arquivo descompactado encontrado em {directory}")
    if any(path.suffix.lower() == ".zip" for path in files):
        raise ValueError("Descompacte a edição mensal CNPJ antes do processamento")
    return files


def stream_rows(path: Path, encoding: str):
    with path.open(encoding=encoding, newline="") as stream:
        yield from csv.reader(stream, delimiter=";", quotechar='"')


def _chunks(rows, size=10000):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) == size:
            yield batch
            batch = []
    if batch:
        yield batch


def aggregate(companies_files, establishment_files, simples_files, encoding="latin-1", database=":memory:"):
    db = sqlite3.connect(database)
    db.execute("PRAGMA journal_mode=OFF")
    db.execute("PRAGMA synchronous=OFF")
    db.execute("PRAGMA temp_store=FILE")
    db.execute("PRAGMA cache_size=-32000")
    db.execute("CREATE TABLE companies (basic TEXT PRIMARY KEY, porte TEXT NOT NULL, mei INTEGER NOT NULL DEFAULT 0)")
    db.execute("CREATE TABLE counts (porte TEXT NOT NULL, cnae TEXT NOT NULL, establishments INTEGER NOT NULL, PRIMARY KEY (porte,cnae))")
    db.execute("CREATE TABLE local_businesses (porte TEXT NOT NULL, cnae TEXT NOT NULL, basic TEXT NOT NULL, PRIMARY KEY (porte,cnae,basic))")
    company_rows = 0
    for path in companies_files:
        for batch in _chunks(stream_rows(path, encoding)):
            values = []
            for row in batch:
                if len(row) < 6 or not row[0].strip():
                    raise ValueError("Layout Receita CNPJ / Empresas não reconhecido")
                basic, porte = row[0].strip(), row[5].strip().zfill(2)
                if porte not in {"00", "01", "03", "05"}:
                    raise ValueError("Código de porte não reconhecido no arquivo Empresas")
                values.append((basic, porte))
            db.executemany(
                "INSERT INTO companies(basic,porte) VALUES(?,?) ON CONFLICT(basic) DO UPDATE SET porte=excluded.porte",
                values,
            )
            company_rows += len(values)
    if not company_rows:
        raise ValueError("Base Empresas vazia")

    simples_rows = 0
    for path in simples_files:
        for batch in _chunks(stream_rows(path, encoding)):
            values = []
            for row in batch:
                if len(row) < 5 or not row[0].strip():
                    raise ValueError("Layout Receita CNPJ / Simples não reconhecido")
                values.append((row[0].strip(), 1 if row[4].strip().upper() == "S" else 0))
            db.executemany(
                "UPDATE companies SET mei=MAX(mei,?) WHERE basic=?",
                ((mei, basic) for basic, mei in values),
            )
            simples_rows += len(values)
    if not simples_rows:
        raise ValueError("Base Simples/MEI vazia; o perfil por porte ficaria incompleto")

    scanned, active_local = 0, 0
    for path in establishment_files:
        for batch in _chunks(stream_rows(path, encoding)):
            for row in batch:
                scanned += 1
                if len(row) < 21:
                    raise ValueError("Layout Receita CNPJ / Estabelecimentos não reconhecido")
                if row[19].strip().upper() != "PR" or row[20].strip().zfill(6) != "412796" or row[5].strip() != "02":
                    continue
                basic = row[0].strip()
                record = db.execute("SELECT porte,mei FROM companies WHERE basic=?", (basic,)).fetchone()
                if record is None:
                    raise ValueError("Estabelecimento local sem correspondência na base Empresas completa")
                porte_code, is_mei = record
                porte = (
                    "MEI"
                    if is_mei
                    else {
                        "00": "Porte não informado",
                        "01": "Microempresa",
                        "03": "Empresa de pequeno porte",
                        "05": "Demais portes",
                    }[porte_code]
                )
                cnae = row[11].strip()
                cnae = cnae.zfill(7) if cnae.isdigit() and cnae else "Não informado"
                db.execute(
                    "INSERT INTO counts VALUES(?,?,1) ON CONFLICT(porte,cnae) DO UPDATE SET establishments=establishments+1",
                    (porte, cnae),
                )
                db.execute("INSERT OR IGNORE INTO local_businesses VALUES(?,?,?)", (porte, cnae, basic))
                active_local += 1
    if scanned == 0:
        raise ValueError("Base Estabelecimentos vazia")
    if not active_local:
        raise ValueError("Nenhum estabelecimento ativo encontrado para Turvo/PR (RFB município 412796)")
    rows = [
        {
            "porte": porte,
            "cnae_principal": cnae,
            "empresas_ativas": db.execute(
                "SELECT COUNT(*) FROM local_businesses WHERE porte=? AND cnae=?", (porte, cnae)
            ).fetchone()[0],
            "estabelecimentos_ativos": count,
        }
        for porte, cnae, count in db.execute(
            "SELECT porte,cnae,establishments FROM counts ORDER BY porte,cnae"
        )
    ]
    active_businesses = db.execute("SELECT COUNT(DISTINCT basic) FROM local_businesses").fetchone()[0]
    db.close()
    return rows, active_businesses, scanned, company_rows, simples_rows


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies-dir", type=Path, required=True)
    parser.add_argument("--establishments-dir", type=Path, required=True)
    parser.add_argument("--simples-dir", type=Path, required=True)
    parser.add_argument("--month", required=True, help="Competência da edição, no formato AAAA-MM")
    parser.add_argument("--source-url", default=SOURCE_DEFAULT)
    parser.add_argument("--encoding", default="latin-1")
    parser.add_argument("--temp-dir", type=Path, help="Disco com espaço livre para o índice transitório nacional")
    parser.add_argument(
        "--complete-release",
        action="store_true",
        help="Ateste que todos os arquivos/partições da mesma edição mensal foram baixados e extraídos.",
    )
    args = parser.parse_args()
    if not args.complete_release:
        parser.error("confirme o conjunto nacional completo com --complete-release; partes isoladas não podem ser publicadas")
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        raise ValueError("Mês inválido; use AAAA-MM")
    date.fromisoformat(args.month + "-01")
    source = urlparse(args.source_url)
    host = source.hostname or ""
    if source.scheme != "https" or not (host == "gov.br" or host.endswith(".gov.br")):
        raise ValueError("A proveniência deve apontar a uma página governamental oficial da Receita Federal")

    companies = input_files(args.companies_dir)
    establishments = input_files(args.establishments_dir)
    simples = input_files(args.simples_dir)
    if any(path.resolve() in {p.resolve() for p in establishments + simples} for path in companies):
        raise ValueError("Separe os arquivos das três tabelas CNPJ em diretórios próprios")
    with tempfile.TemporaryDirectory(prefix="cnpj-turvo-", dir=args.temp_dir) as temp:
        rows, total, scanned, company_rows, simples_rows = aggregate(
            companies,
            establishments,
            simples,
            args.encoding,
            database=str(Path(temp) / "indice-cnpj.sqlite3"),
        )
    inputs = companies + establishments + simples
    hashes = [{"file": str(path), "sha256": sha256(path)} for path in inputs]
    period = args.month
    previous = store.read_all().get("business_profile", {})
    points_by_period = {}
    if previous.get("payload"):
        points_by_period.update(
            {
                point["period"]: point["value"]
                for point in json.loads(previous["payload"]).get("points", [])
            }
        )
    points_by_period[period] = total
    points = [
        {"period": month, "value": points_by_period[month]}
        for month in sorted(points_by_period)
    ]
    store.save(
        "business_profile",
        {
            "value": total,
            "period": period,
            "points": points,
            "rows": rows,
            "endpoint": args.source_url,
            "origin": "Receita Federal / Dados Abertos do CNPJ, agregado localmente",
            "note": "Total de empresas distintas pelo CNPJ básico com ao menos um estabelecimento ativo em Turvo/PR. A tabela detalha empresas e estabelecimentos por porte/CNAE principal; empresas com filiais de CNAEs diferentes podem aparecer em mais de uma linha. MEI classificado pela opção S na tabela Simples. Não identifica empresas.",
        },
        {
            "sourceUrl": args.source_url,
            "month": period,
            "municipalityIbge": "4127965",
            "rfbMunicipalityCode": "412796",
            "establishmentRowsScanned": scanned,
            "companyRowsScanned": company_rows,
            "simplesRowsScanned": simples_rows,
            "files": hashes,
            "method": "Agregação completa da edição nacional CNPJ: estabelecimentos ativos do município 412796/PR agrupados por porte (MEI consultado na tabela Simples) e CNAE principal.",
            "completenessAttested": True,
        },
    )
    establishment_total = sum(row["estabelecimentos_ativos"] for row in rows)
    print(f"Perfil CNPJ {period}: {total} empresas ativas agregadas; {establishment_total} estabelecimentos em {len(rows)} combinações de porte/CNAE.")


if __name__ == "__main__":
    main()
