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


def test_cloudflare_api_cors_allows_only_configured_frontend():
    client = TestClient(app)
    allowed = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    rejected = client.get("/api/health", headers={"Origin": "https://other.example"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in rejected.headers


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
        aggregate(io.StringIO("Município;Vínculo Ativo 31/12\n412796;Talvez\n"))


def test_rais_new_public_layout_comma_delimited_and_accented_headers():
    import io

    from backend.import_rais import aggregate

    value, scanned = aggregate(
        io.StringIO(
            "Município - Código,Ind Vínculo Ativo 31/12 - Código\n"
            "412796,1\n"
            "412796,0\n"
            "4106902,1\n"
        )
    )
    assert (value, scanned) == (1, 3)


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


def test_cnpj_profile_import_aggregates_only_active_turvo_establishments(tmp_path):
    from backend.import_cnpj import aggregate

    companies = tmp_path / "companies"
    establishments = tmp_path / "establishments"
    simples = tmp_path / "simples"
    for directory in (companies, establishments, simples):
        directory.mkdir()

    company_rows = []
    for basic, porte in [("00000001", "01"), ("00000002", "03")]:
        row = [basic, "PUBLICO", "", "", "", porte, ""]
        company_rows.append(";".join(row))
    (companies / "Empresas0").write_text("\n".join(company_rows), encoding="latin-1")

    simples_row = ["00000001", "S", "", "", "S", "", ""]
    (simples / "Simples0").write_text(";".join(simples_row), encoding="latin-1")

    def establishment(basic, status="02", uf="PR", city="412796", cnae="6201500"):
        fields = [""] * 21
        fields[0], fields[5], fields[11], fields[19], fields[20] = basic, status, cnae, uf, city
        return ";".join(fields)

    (establishments / "Estabelecimentos0").write_text(
        "\n".join(
            [
                establishment("00000001"),
                establishment("00000001"),
                establishment("00000002", cnae="5611201"),
                establishment("00000001", status="08"),
                establishment("00000002", uf="SC"),
            ]
        ),
        encoding="latin-1",
    )
    rows, companies_active, scanned, companies_scanned, simples_scanned = aggregate(
        [companies / "Empresas0"],
        [establishments / "Estabelecimentos0"],
        [simples / "Simples0"],
    )
    assert rows == [
        {"porte": "Empresa de pequeno porte", "cnae_principal": "5611201", "empresas_ativas": 1, "estabelecimentos_ativos": 1},
        {"porte": "MEI", "cnae_principal": "6201500", "empresas_ativas": 1, "estabelecimentos_ativos": 2},
    ]
    assert (companies_active, scanned, companies_scanned, simples_scanned) == (2, 5, 2, 1)


def test_cnpj_profile_rejects_active_local_establishment_without_company_record(tmp_path):
    from backend.import_cnpj import aggregate

    companies = tmp_path / "Empresas0"
    companies.write_text("00000001;;;;;01;\n", encoding="latin-1")
    simples = tmp_path / "Simples0"
    simples.write_text("00000001;S;;;N;;;\n", encoding="latin-1")
    establishment = [""] * 21
    establishment[0], establishment[5], establishment[11], establishment[19], establishment[20] = (
        "99999999",
        "02",
        "6201500",
        "PR",
        "412796",
    )
    local = tmp_path / "Estabelecimentos0"
    local.write_text(";".join(establishment), encoding="latin-1")
    with pytest.raises(ValueError, match="sem correspondência"):
        aggregate([companies], [local], [simples])


def test_transferegov_orders_are_summed_and_proposed_values_are_not_used():
    item = next(i for i in CATALOG if i["id"] == "agreement_orders")
    response = {
        "complete": True,
        "period": "2025",
        "rows": [{"valor": 25.5}, {"valor": 74.5}],
    }
    result = normalize(item, response)
    assert result["value"] == 100
    assert result["points"] == [{"period": "2025", "value": 100}]


def test_complete_transferegov_query_preserves_real_empty_as_zero():
    item = next(i for i in CATALOG if i["id"] == "signed_agreements")
    result = normalize(item, {"complete": True, "period": "2025", "rows": []})
    assert result["value"] == 0
    assert result["points"] == [{"period": "2025", "value": 0}]


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
