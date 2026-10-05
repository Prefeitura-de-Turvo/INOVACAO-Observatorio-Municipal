import math


def number(value):
    if value is None or isinstance(value, bool):
        return None
    # IBGE usa ponto decimal sem separador de milhares; símbolos não são zero.
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def normalize(item, response):
    if response.get("complete") is not True:
        raise ValueError("Resposta incompleta: total não publicado")
    id = item["id"]
    points, rows = [], response.get("rows", [])
    if id == "gdp_per_capita":
        points = response["points"]
        if not points:
            raise ValueError("Nenhum período comum entre PIB e população")
        period, value = points[-1]["period"], points[-1]["value"]
        rows = response["rows"]
    elif item["source"] == "ibge":
        raw = response["raw"]
        if len(raw) != 1 or str(raw[0]["id"]) != str(item["args"]["variavel"]):
            raise ValueError("Variável IBGE diferente da solicitada")
        results = raw[0].get("resultados", [])
        if len(results) != 1 or len(results[0].get("series", [])) != 1:
            raise ValueError("Classificações ambíguas ou múltiplos territórios")
        series = results[0]["series"][0]
        if series["localidade"]["id"] != "4127965":
            raise ValueError("Território diferente de Turvo/PR")
        unit = raw[0].get("unidade", "")
        expected = {
            "population": "Pessoas",
            "area": "Quilômetros quadrados",
            "gdp": "Mil Reais",
            "gdp_per_capita": "Reais",
            "literacy": "%",
            "sewage": "%",
        }[id]
        if unit.casefold() not in {expected.casefold(), "percentual" if expected == "%" else expected.casefold()}:
            raise ValueError(f"Unidade inesperada: {unit}")
        for period, value in sorted(series["serie"].items()):
            value = number(value)
            if value is not None:
                if value < 0 or (item["unit"] == "%" and value > 100):
                    raise ValueError("Valor fora do domínio")
                points.append({"period": period, "value": value * (1000 if id == "gdp" else 1)})
        if not points:
            raise ValueError("Fonte sem valores numéricos publicáveis")
        period, value = points[-1]["period"], points[-1]["value"]
        rows = [{"Período": p["period"], "Valor": p["value"]} for p in points]
    elif id == "rcl":
        matches = [
            r
            for r in rows
            if str(r.get("conta", "")).upper().strip().startswith("RECEITA CORRENTE LÍQUIDA (III)")
            and str(r.get("coluna", "")).upper().strip() == "TOTAL (ÚLTIMOS 12 MESES)"
        ]
        if len(matches) != 1 or number(matches[0].get("valor")) is None:
            raise ValueError("RCL sem linha e coluna únicas homologadas; consulte declaração oficial")
        if any(str(r.get("cod_ibge")) != "4127965" for r in matches):
            raise ValueError("Ente fiscal divergente")
        value, period = number(matches[0]["valor"]), response["period"]
        points = [{"period": period, "value": value}]
    elif id == "pnae":
        if not rows:
            raise ValueError("FNDE não retornou registros municipais")
        value, period = None, response["period"]
    else:
        # Somente endpoints de cadastros completos podem publicar zero registros.
        value, period = len(rows), response["period"]
        points = [{"period": period, "value": value}]
    return {
        "value": value,
        "period": period,
        "points": points,
        "rows": rows,
        "endpoint": response.get("url"),
        "query": response.get("params", {}),
        "origin": "MCP Brasil + extensão estruturada local",
        "note": item.get("note", ""),
    }
