"""Extensões estruturadas locais. Não são ferramentas oficiais do MCP Brasil.

As tools originais formatam texto e algumas eliminam períodos/paginam parcialmente.
Estas extensões usam seus clientes HTTP, constantes, schemas e lifecycle, mantendo
os atributos necessários à publicação de indicadores auditáveis.
"""

import asyncio
import os
from datetime import date, datetime
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

os.environ["MCP_BRASIL_TOOL_SEARCH"] = "none"
from mcp_brasil._shared.http_client import create_client, http_get
from mcp_brasil.data.compras.pncp import client as pncp
from mcp_brasil.data.compras.pncp.constants import CONTRATACOES_URL
from mcp_brasil.data.fnde.constants import PNAE_URL
from mcp_brasil.data.fnde.schemas import PnaeAluno
from mcp_brasil.data.ibge.constants import AGREGADOS_URL
from mcp_brasil.data.saude import client as saude
from mcp_brasil.data.saude.constants import ESTABELECIMENTOS_URL
from mcp_brasil.data.siconfi import client as fiscal
from mcp_brasil.data.siconfi.constants import SICONFI_API_BASE
from mcp_brasil.data.transferegov import client as transfere
from mcp_brasil.data.transferegov.constants import DEFAULT_PAGE_SIZE, PLANO_ACAO_URL
from mcp_brasil.server import mcp


@mcp.tool(name="observatorio_ibge")
async def ibge(agregado: int, variavel: int, municipios: str = "4127965", classificacao: str = "") -> dict:
    """JSON completo IBGE: períodos reais, unidade, território e classificações."""
    if not all(len(c) == 7 and c.isdigit() for c in municipios.split("|")):
        raise ValueError("Códigos IBGE inválidos")
    params = {"localidades": "N6[" + municipios.replace("|", ",") + "]"}
    if classificacao:
        params["classificacao"] = classificacao
    url = f"{AGREGADOS_URL}/{agregado}/periodos/-10/variaveis/{variavel}"
    meta = await http_get(f"{AGREGADOS_URL}/{agregado}/metadados")
    raw = await http_get(url, params=params)
    return {"raw": raw, "metadata": meta, "url": url, "params": params, "complete": True}


@mcp.tool(name="observatorio_entes")
async def entes() -> dict:
    """Cadastro SICONFI para validar o CNPJ do ente municipal pelo código IBGE."""
    rows = await fiscal.listar_entes()
    return {
        "rows": [r.model_dump() for r in rows if str(r.cod_ibge) == "4127965"],
        "url": f"{SICONFI_API_BASE}/entes",
        "complete": True,
    }


@mcp.tool(name="observatorio_fiscal")
async def financas(ano: int) -> dict:
    """RREO anexo 03, normal ou simplificado, último bimestre entregue."""
    for periodo in range(6, 0, -1):
        for tipo in ("RREO", "RREO Simplificado"):
            params = {
                "an_exercicio": ano,
                "nr_periodo": periodo,
                "co_tipo_demonstrativo": tipo,
                "id_ente": 4127965,
                "no_anexo": "RREO-Anexo 03",
                "co_esfera": "M",
            }
            rows, pages = [], []
            for offset in range(0, 20000, 1000):
                await asyncio.sleep(1.1)
                query = {**params, "offset": offset, "limit": 1000}
                raw = await http_get(f"{SICONFI_API_BASE}/rreo?" + urlencode(query, quote_via=quote))
                if not isinstance(raw.get("items"), list) or not isinstance(raw.get("hasMore"), bool):
                    raise ValueError("Schema SICONFI não reconhecido")
                pages.append(raw)
                rows.extend(raw["items"])
                if not raw["hasMore"]:
                    break
                if not raw["items"]:
                    raise ValueError("Paginação SICONFI interrompida")
            else:
                raise ValueError("Paginação SICONFI excedeu limite")
            if rows:
                if any(str(r.get("cod_ibge")) != "4127965" for r in rows):
                    raise ValueError("Ente fiscal divergente")
                return {
                    "rows": rows,
                    "rawPages": pages,
                    "period": f"{ano} / {periodo}º bimestre",
                    "url": f"{SICONFI_API_BASE}/rreo",
                    "complete": True,
                    "params": params,
                }
    raise ValueError("RREO não encontrado no exercício consultado")


@mcp.tool(name="observatorio_cnes")
async def cnes() -> dict:
    """Todos os estabelecimentos ativos; paginação e conferência de território."""
    rows = []
    for offset in range(0, 2000, 20):
        batch = await saude.buscar_estabelecimentos(codigo_municipio="412796", status=1, limit=20, offset=offset)
        if any(str(r.codigo_municipio) not in {"412796", "4127965"} for r in batch):
            raise ValueError("CNES retornou território diferente")
        for record in batch:
            row = record.model_dump()
            # O parser upstream usa descrição do turno no campo descricao_tipo.
            row["turno_atendimento"] = row.pop("descricao_tipo", None)
            rows.append(row)
        if len(batch) < 20:
            unique = {r["codigo_cnes"]: r for r in rows}
            return {
                "rows": list(unique.values()),
                "url": ESTABELECIMENTOS_URL,
                "complete": True,
                "period": "Cadastro corrente; competência não informada pela API",
                "params": {"codigo_municipio": "412796", "status": 1},
            }
    raise ValueError("Paginação CNES excedeu o limite; total não publicado")


@mcp.tool(name="observatorio_pnae")
async def pnae(ano: int = 2022) -> dict:
    """Alunos PNAE, última cobertura documentada do endpoint FNDE (2022)."""
    rows = []
    for skip in range(0, 10000, 1000):
        params = {
            "$format": "json",
            "$top": 1000,
            "$skip": skip,
            "$filter": f"Ano eq '{ano}' and Estado eq 'PR' and Municipio eq 'TURVO'",
        }
        # Olinda interpreta '+' como operador; espaços devem ser %20.
        raw = await http_get(PNAE_URL + "?" + urlencode(params, quote_via=quote))
        if not isinstance(raw.get("value"), list):
            raise ValueError("Schema FNDE não reconhecido")
        batch = [PnaeAluno.model_validate(row) for row in raw["value"]]
        rows.extend(r.model_dump() for r in batch if r.municipio.upper().strip() == "TURVO" and r.estado == "PR")
        if len(batch) < 1000:
            return {"rows": rows, "url": PNAE_URL, "complete": True, "period": str(ano)}
    raise ValueError("Paginação PNAE incompleta")


async def pncp_page(params: dict) -> dict:
    """Corrige 204 do PNCP, que o http_get original tenta decodificar como JSON."""
    async with create_client(timeout=30) as client:
        for attempt in range(5):
            await asyncio.sleep(2.5)
            response = await client.get(CONTRATACOES_URL, params=params)
            if response.status_code == 204:
                return {"data": [], "totalPaginas": 0, "totalRegistros": 0}
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 4:
                await asyncio.sleep(min(60, max(10, float(response.headers.get("Retry-After", "10")))))
                continue
            response.raise_for_status()
            raw = response.json()
            if not isinstance(raw.get("data"), list) or not isinstance(raw.get("totalPaginas"), int):
                raise ValueError("Schema PNCP não reconhecido")
            return raw
    raise ValueError("PNCP indisponível")


@mcp.tool(name="observatorio_pncp")
async def compras(cnpj: str, ano: int) -> dict:
    """Contratações por CNPJ, todas as modalidades e páginas do ano até hoje."""
    if len(cnpj) != 14 or not cnpj.isdigit():
        raise ValueError("CNPJ não configurado/validado")
    rows, pages = {}, []
    end = min(date(ano, 12, 31), datetime.now(ZoneInfo("America/Sao_Paulo")).date()).strftime("%Y%m%d")
    for modalidade in range(1, 15):
        expected = None
        collected = 0
        for pagina in range(1, 101):
            params = {
                "dataInicial": f"{ano}0101",
                "dataFinal": end,
                "codigoModalidadeContratacao": modalidade,
                "cnpj": cnpj,
                "uf": "PR",
                "pagina": pagina,
                "tamanhoPagina": 50,
            }
            raw = await pncp_page(params)
            pages.append(raw)
            if expected is None:
                expected = raw["totalRegistros"]
            elif expected != raw["totalRegistros"]:
                raise ValueError("PNCP alterou total durante paginação; repetir coleta")
            for source in raw["data"]:
                unit = source.get("unidadeOrgao") or {}
                org = source.get("orgaoEntidade") or {}
                if org.get("cnpj") != cnpj or str(unit.get("codigoIbge")) != "4127965":
                    raise ValueError("PNCP retornou órgão ou território diferente")
                r = pncp._parse_contratacao(source).model_dump()
                r.update(
                    {
                        "municipio": unit.get("municipioNome"),
                        "uf": unit.get("ufSigla"),
                        "atualizacao_na_fonte": source.get("dataAtualizacaoGlobal"),
                    }
                )
                if not r["numero_controle_pncp"]:
                    raise ValueError("PNCP sem identificador")
                rows[r["numero_controle_pncp"]] = r
            collected += len(raw["data"])
            if pagina >= raw["totalPaginas"]:
                if collected != expected:
                    raise ValueError("Paginação PNCP incompleta")
                break
        else:
            raise ValueError("Paginação PNCP excedeu limite")
    return {
        "rows": list(rows.values()),
        "rawPages": pages,
        "url": CONTRATACOES_URL,
        "complete": True,
        "period": f"{ano}0101 a {end}",
        "params": {"cnpj": cnpj, "ano": ano, "modalidades": list(range(1, 15))},
    }


@mcp.tool(name="observatorio_transferencias")
async def transferencias(cnpj: str, ano: int) -> dict:
    """Transferências especiais por CNPJ validado. Não representam convênios nem valor pago."""
    rows = {}
    for pagina in range(1, 101):
        batch = await transfere.emendas_por_municipio("TURVO", ano=ano, pagina=pagina)
        for r in batch:
            if r.cnpj_beneficiario == cnpj and r.uf_beneficiario == "PR":
                if not r.id_plano_acao:
                    raise ValueError("Transferência sem identificador")
                rows[r.id_plano_acao] = r.model_dump()
        if len(batch) < DEFAULT_PAGE_SIZE:
            return {
                "rows": list(rows.values()),
                "url": PLANO_ACAO_URL,
                "complete": True,
                "period": str(ano),
                "params": {"ano": ano, "cnpj_beneficiario": cnpj},
            }
    raise ValueError("Paginação TransfereGov excedeu limite")


@mcp.tool(name="observatorio_comparacao")
async def comparacao() -> dict:
    """Seleciona 5 municípios do PR mais próximos em população no mesmo ano."""
    from mcp_brasil.data.ibge.client import listar_municipios

    municipios = await listar_municipios("PR")
    series = []
    for offset in range(0, len(municipios), 30):
        codes = "|".join(str(m.id) for m in municipios[offset : offset + 30])
        result = await ibge(6579, 9324, codes)
        series.extend(result["raw"][0]["resultados"][0]["series"])
    by_code = {s["localidade"]["id"]: s for s in series}
    turvo = by_code["4127965"]
    periods = sorted(turvo["serie"], reverse=True)
    year = next(y for y in periods if turvo["serie"][y].replace(".", "", 1).isdigit())
    population = float(turvo["serie"][year])
    rows = []
    for code, s in by_code.items():
        value = s["serie"].get(year, "")
        if not value.replace(".", "", 1).isdigit():
            continue
        value = float(value)
        if code != "4127965" and 0.5 * population <= value <= 1.5 * population:
            rows.append(
                {
                    "code": code,
                    "name": s["localidade"]["nome"],
                    "population": value,
                    "difference": (value / population - 1) * 100,
                }
            )
    rows.sort(key=lambda r: (abs(r["difference"]), r["code"]))
    rows = [{"code": "4127965", "name": "Turvo (PR)", "population": population, "difference": 0}] + rows[:5]
    return {
        "rows": rows,
        "period": year,
        "unit": "pessoas",
        "source": "IBGE / SIDRA 6579",
        "url": "https://sidra.ibge.gov.br/tabela/6579",
        "complete": True,
        "method": "Municípios do Paraná com população entre 50% e 150% de Turvo, ordenados pela menor diferença absoluta no mesmo ano. Sem alegar equivalência socioeconômica.",
    }


@mcp.tool(name="observatorio_pib_por_habitante")
async def pib_por_habitante() -> dict:
    """Razão calculada com dados oficiais e mesmo ano, sem atalho nacional."""
    gdp = await ibge(5938, 37)
    pop = await ibge(6579, 9324)

    def values(response):
        result = response["raw"][0]["resultados"]
        if len(result) != 1 or len(result[0]["series"]) != 1:
            raise ValueError("Séries ambíguas")
        s = result[0]["series"][0]
        if s["localidade"]["id"] != "4127965":
            raise ValueError("Município divergente")
        return s["serie"]

    gs, ps = values(gdp), values(pop)
    rows, points = [], []
    for year in sorted(set(gs) & set(ps)):
        try:
            total, people = float(gs[year]) * 1000, float(ps[year])
        except ValueError:
            continue
        if total >= 0 and people > 0:
            points.append({"period": year, "value": total / people})
            rows.append(
                {
                    "Período": year,
                    "PIB (R$)": total,
                    "População estimada": people,
                    "PIB por habitante calculado (R$)": total / people,
                }
            )
    return {
        "complete": True,
        "points": points,
        "rows": rows,
        "url": "https://sidra.ibge.gov.br/tabela/5938",
        "inputs": {"gdp": gdp, "population": pop},
    }


if __name__ == "__main__":
    if os.getenv("MCP_BRIDGE_HTTP") == "1":
        mcp.run(transport="http", host="0.0.0.0", port=8001, show_banner=False)
    else:
        mcp.run(show_banner=False)
