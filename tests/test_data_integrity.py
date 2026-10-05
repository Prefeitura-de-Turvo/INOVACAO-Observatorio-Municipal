"""Fixtures sintéticas só para testes de integridade; nunca carregadas pela aplicação."""

import json

import pytest
from fastapi.testclient import TestClient

from backend import store
from backend.app import app
from backend.catalog import CATALOG
from backend.normalize import normalize, number

POP = next(i for i in CATALOG if i["id"] == "population")


def ibge(value="14000", code="4127965"):
    return {
        "complete": True,
        "url": "https://servicodados.ibge.gov.br/api/v3/agregados/6579",
        "raw": [
            {
                "id": "9324",
                "unidade": "Pessoas",
                "resultados": [{"series": [{"localidade": {"id": code}, "serie": {"2025": value}}]}],
            }
        ],
    }


@pytest.mark.parametrize("value", ["...", "-", "X", "", None, "NaN", "Infinity", True])
def test_missing_is_not_zero(value):
    assert number(value) is None


def test_real_zero_preserved():
    assert normalize(POP, ibge("0"))["value"] == 0


def test_wrong_municipality_rejected():
    with pytest.raises(ValueError, match="Território"):
        normalize(POP, ibge(code="4218806"))


def test_partial_page_rejected():
    response = ibge()
    response["complete"] = False
    with pytest.raises(ValueError, match="incompleta"):
        normalize(POP, response)


def test_ambiguous_classification_rejected():
    response = ibge()
    response["raw"][0]["resultados"] *= 2
    with pytest.raises(ValueError, match="ambíguas"):
        normalize(POP, response)


def test_currency_unit_conversion():
    item = next(i for i in CATALOG if i["id"] == "gdp")
    response = ibge("20")
    response["raw"][0]["id"] = "37"
    response["raw"][0]["unidade"] = "Mil Reais"
    assert normalize(item, response)["value"] == 20000


def test_failure_preserves_last_success(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "cache.db"))
    store.save("population", normalize(POP, ibge()), ibge())
    before = store.read_all()["population"]
    store.fail("population", "Fonte indisponível")
    after = store.read_all()["population"]
    assert before["success_at"] == after["success_at"]
    assert json.loads(after["payload"])["value"] == 14000
    client = TestClient(app)  # Sem lifespan: nenhum acesso a redes nos testes.
    data = client.get("/api/indicators").json()
    population = next(i for i in data["indicators"] if i["id"] == "population")
    assert population["status"] == "stale"
    assert population["updatedAt"] == before["success_at"]
    assert client.get("/api/export/population").status_code == 200


def test_no_fake_values_on_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "empty.db"))
    client = TestClient(app)
    response = client.get("/api/indicators")
    assert response.status_code == 200
    assert all(i["value"] is None for i in response.json()["indicators"])
    assert client.get("/api/export/population").status_code == 503
    assert client.get("/api/export/not-found").status_code == 404


def test_fiscal_cannot_sum_unrelated_accounts():
    item = next(i for i in CATALOG if i["id"] == "rcl")
    response = {
        "complete": True,
        "period": "2025 / 6º bimestre",
        "rows": [
            {"conta": "Receitas tributárias", "coluna": "TOTAL (ÚLTIMOS 12 MESES)", "valor": 200, "cod_ibge": 4127965}
        ],
    }
    with pytest.raises(ValueError, match="RCL"):
        normalize(item, response)


def test_estimated_gdp_requires_same_period_inputs():
    item = next(i for i in CATALOG if i["id"] == "gdp_per_capita")
    with pytest.raises(ValueError, match="período comum"):
        normalize(item, {"complete": True, "points": [], "rows": []})


def test_rais_filters_municipality_and_active_jobs():
    import io

    from backend.import_rais import aggregate

    value, scanned = aggregate(io.StringIO("Município;Vínculo Ativo 31/12\n412796;1\n412796;0\n421880;1\n"))
    assert value == 1 and scanned == 3


def test_rais_unknown_active_code_rejected():
    import io

    from backend.import_rais import aggregate

    with pytest.raises(ValueError, match="não reconhecido"):
        aggregate(io.StringIO("Município;Vínculo Ativo 31/12\n412796;Sim\n"))


def test_idan_m_import_requires_turvo_official_annual_score():
    import io

    from backend.import_idan_m import parse

    points, scanned = parse(
        io.StringIO(
            "codigo_ibge;ano;pontuacao\n"
            "4127965;2023;61,5\n"
            "4218806;2023;99\n"
            "4127965;2024;72\n"
        )
    )
    assert points == [{"period": "2023", "value": 61.5}, {"period": "2024", "value": 72.0}]
    assert scanned == 3


def test_idan_m_import_rejects_duplicate_year_and_out_of_range_score():
    import io

    from backend.import_idan_m import parse

    with pytest.raises(ValueError, match="duplicada"):
        parse(io.StringIO("codigo_ibge;ano;pontuacao\n4127965;2024;50\n4127965;2024;60\n"))
    with pytest.raises(ValueError, match="domínio"):
        parse(io.StringIO("codigo_ibge;ano;pontuacao\n4127965;2024;101\n"))


def test_fiscal_exact_rcl_published_without_summing_components():
    item = next(i for i in CATALOG if i["id"] == "rcl")
    response = {
        "complete": True,
        "period": "2025 / 6º bimestre",
        "rows": [
            {
                "conta": "RECEITA CORRENTE LÍQUIDA (III) = (I - II)",
                "coluna": "TOTAL (ÚLTIMOS 12 MESES)",
                "valor": 100,
                "cod_ibge": 4127965,
            },
            {"conta": "Receitas tributárias", "coluna": "TOTAL (ÚLTIMOS 12 MESES)", "valor": 50, "cod_ibge": 4127965},
        ],
    }
    assert normalize(item, response)["value"] == 100


def test_pncp_contracts_publish_only_aggregated_supplier_dimensions():
    item = next(i for i in CATALOG if i["id"] == "procurement_contracts")
    response = {
        "complete": True,
        "period": "2025",
        "url": "https://pncp.gov.br/api/consulta/v1/contratos",
        "rows": [
            {"numero_controle": "safe-id", "categoria": "Compras", "tipo_fornecedor": "Pessoa jurídica", "valor": 100, "objeto": "Papel"},
            {"numero_controle": "safe-id-2", "categoria": "Serviços", "tipo_fornecedor": "Pessoa jurídica", "valor": 200, "objeto": "Manutenção"},
        ],
    }
    normalized = normalize(item, response)
    assert normalized["value"] == 2
    assert normalized["groups"]["supplier_type"] == [{"name": "Pessoa jurídica", "count": 2}]
    assert all("cnpj" not in str(row).lower() and "fornecedor_nome" not in row for row in normalized["rows"])


def test_ideb_records_are_stratified_not_averaged():
    item = next(i for i in CATALOG if i["id"] == "ideb")
    response = {"complete": True, "period": "2023", "rows": [{"etapa": "anos_iniciais", "rede": "Pública", "ideb": 6.2}]}
    normalized = normalize(item, response)
    assert normalized["value"] is None
    assert normalized["period"] == "2023"
    assert normalized["rows"] == response["rows"]
