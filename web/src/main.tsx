import React, { useEffect, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
} from "recharts";
import {
  ArrowUpRight,
  BarChart3,
  Building2,
  Download,
  ExternalLink,
  Landmark,
  Menu,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";
import "./style.css";

type Point = { period: string; value: number };
type Indicator = {
  id: string;
  title: string;
  module: string;
  unit: string;
  method: string;
  note: string;
  source: string;
  sourceInfo: { name: string; url: string; description?: string };
  status: string;
  updatedAt: string | null;
  attemptedAt: string | null;
  value: number | null;
  period: string | null;
  points: Point[];
  rows: Record<string, unknown>[];
  endpoint?: string;
  error?: string;
};
type Dataset = { indicators: Indicator[]; modules: string[] };
type Comparison = {
  rows?: {
    code: string;
    name: string;
    population: number;
    difference: number;
  }[];
  period?: string;
  method?: string;
  url?: string;
  updatedAt?: string;
  status: string;
};
const fmt = (n: number, unit = "") =>
  unit === "R$"
    ? new Intl.NumberFormat("pt-BR", {
        style: "currency",
        currency: "BRL",
        maximumFractionDigits: 0,
      }).format(n)
    : new Intl.NumberFormat("pt-BR", {
        maximumFractionDigits:
          unit === "pessoas" ||
          unit === "unidades" ||
          unit === "processos" ||
          unit === "planos"
            ? 0
            : 2,
      }).format(n) + (unit === "%" ? "%" : "");
const date = (v: string | null | undefined) =>
  v
    ? new Date(v).toLocaleString("pt-BR", {
        timeZone: "America/Sao_Paulo",
        dateStyle: "short",
        timeStyle: "short",
      })
    : "Ainda não coletado";
const statuses: Record<string, string> = {
  available: "Disponível",
  stale: "Cache • atualização pendente",
  unavailable: "Fonte indisponível",
  pending: "Integração pendente",
};
const moduleLabels: Record<string, string> = {
  "Compras Públicas/PNCP": "Compras públicas",
  "Saneamento/Infraestrutura": "Saneamento e infraestrutura",
  "Transferências/convênios": "Transferências e convênios",
};
async function fetchJSON<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok)
    throw new Error("Não foi possível consultar o observatório.");
  return response.json();
}
function Metadata({ item }: { item: Indicator }) {
  return (
    <div className="metadata">
      <a href={item.sourceInfo.url} target="_blank" rel="noreferrer">
        {item.sourceInfo.name} <ExternalLink size={11} />
      </a>
      <span>Referência: {item.period || "Não disponível"}</span>
      <span>Última coleta: {date(item.updatedAt)}</span>
    </div>
  );
}
function Card({ item, onOpen }: { item: Indicator; onOpen: () => void }) {
  const available = item.updatedAt !== null;
  return (
    <button
      className={"card metric " + (!available ? "muted" : "")}
      onClick={onOpen}
      aria-label={"Ver detalhes de " + item.title}
    >
      <div className="metric-title">
        {item.title}
        <ArrowUpRight size={17} />
      </div>
      <div
        className={
          "metric-value " +
          (item.value != null && fmt(item.value, item.unit).length > 11
            ? "long-value"
            : "")
        }
      >
        {item.value != null
          ? fmt(item.value, item.unit)
          : available && item.rows.length
            ? "Ver registros"
            : "—"}
      </div>
      <div className="metric-unit">
        {item.unit !== "%" && item.unit !== "R$"
          ? item.unit
          : item.id === "gdp_per_capita"
            ? "cálculo com dados oficiais"
            : "valor oficial da fonte"}
      </div>
      <span className={"badge " + item.status}>{statuses[item.status]}</span>
      <div className="metric-meta">
        <span>{item.sourceInfo.name}</span>
        <span>Referência: {item.period || "Não disponível"}</span>
        <span>Última coleta: {date(item.updatedAt)}</span>
      </div>
    </button>
  );
}
function Chart({ item }: { item: Indicator }) {
  return (
    <section className="card chart">
      <div className="section-title">
        <div>
          <p className="eyebrow">SÉRIE HISTÓRICA</p>
          <h2>{item.title}</h2>
        </div>
        <span className="unit-chip">{item.unit}</span>
      </div>
      {item.points.length > 1 ? (
        <>
          <div
            className="chart-body"
            role="img"
            aria-label={"Série histórica de " + item.title}
          >
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={item.points}
                margin={{ top: 10, right: 15, left: 15, bottom: 5 }}
              >
                <defs>
                  <linearGradient
                    id={"fill-" + item.id}
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop offset="0%" stopColor="#168570" stopOpacity={0.23} />
                    <stop offset="100%" stopColor="#168570" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  strokeDasharray="3 5"
                  vertical={false}
                  stroke="#e8eee9"
                />
                <XAxis
                  dataKey="period"
                  tickLine={false}
                  axisLine={false}
                  fontSize={12}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={70}
                  fontSize={11}
                  tickFormatter={(v) =>
                    Intl.NumberFormat("pt-BR", { notation: "compact" }).format(
                      v,
                    )
                  }
                  domain={["auto", "auto"]}
                />
                <Tooltip
                  formatter={(v) => fmt(Number(v), item.unit)}
                  labelFormatter={(v) => "Referência: " + v}
                />
                <Area
                  type="linear"
                  dataKey="value"
                  name={item.title}
                  stroke="#168570"
                  strokeWidth={2.5}
                  fill={"url(#fill-" + item.id + ")"}
                  connectNulls={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <p className="chart-note">
            Valores oficiais disponíveis. Anos sem informação não foram
            estimados.
          </p>
        </>
      ) : (
        <div className="empty">
          <BarChart3 size={30} />
          <p>
            {item.points.length === 1
              ? "A fonte possui apenas um período disponível para esta consulta."
              : "A série será exibida após uma coleta validada."}
          </p>
        </div>
      )}
      <Metadata item={item} />
    </section>
  );
}
function DataTable({ item }: { item: Indicator }) {
  const [page, setPage] = useState(0);
  const [query, setQuery] = useState("");
  const rows = item.rows.filter((r) =>
    Object.values(r).some((v) =>
      String(v ?? "")
        .toLowerCase()
        .includes(query.toLowerCase()),
    ),
  );
  const columns = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  return (
    <section className="card table-card">
      <div className="section-title">
        <h2>Registros da fonte</h2>
        <label className="search">
          <Search size={16} />
          <input
            aria-label="Filtrar registros"
            placeholder="Buscar na tabela"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
          />
        </label>
      </div>
      {rows.length ? (
        <>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c}>{c.replaceAll("_", " ")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(page * 15, page * 15 + 15).map((r, i) => (
                  <tr key={i}>
                    {columns.map((c) => (
                      <td key={c}>
                        {typeof r[c] === "number"
                          ? Intl.NumberFormat("pt-BR", {
                              maximumFractionDigits: 2,
                            }).format(r[c] as number)
                          : String(r[c] ?? "Não informado")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>
              {rows.length} registros • página {page + 1}
            </span>
            <button disabled={!page} onClick={() => setPage(page - 1)}>
              Anterior
            </button>
            <button
              disabled={(page + 1) * 15 >= rows.length}
              onClick={() => setPage(page + 1)}
            >
              Próxima
            </button>
          </div>
        </>
      ) : (
        <div className="empty">Nenhum registro validado disponível.</div>
      )}
      <Metadata item={item} />
    </section>
  );
}
function Detail({ item, close }: { item: Indicator; close: () => void }) {
  const dialogRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const cb = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
      if (e.key === "Tab") {
        const nodes = Array.from(
          dialogRef.current?.querySelectorAll<HTMLElement>(
            "button:not(:disabled), a[href], input",
          ) || [],
        );
        if (!nodes.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", cb);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", cb);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [close]);
  return (
    <div className="overlay">
      <section
        ref={dialogRef}
        className="detail"
        role="dialog"
        aria-modal="true"
        aria-label={item.title}
      >
        <div className="detail-top">
          <h2>{item.title}</h2>
          <button onClick={close} aria-label="Fechar detalhes">
            <X />
          </button>
        </div>
        <span className={"badge " + item.status}>{statuses[item.status]}</span>
        <p>{item.method}</p>
        {item.note && <p className="notice">{item.note}</p>}
        {item.status === "stale" && (
          <p className="notice">
            A última resposta validada foi preservada. A atualização está
            pendente ou a fonte falhou.
          </p>
        )}
        <Chart item={item} />
        <DataTable key={item.id} item={item} />
        {item.updatedAt && item.points.length > 0 && (
          <a className="download" href={"/api/export/" + item.id}>
            <Download size={16} /> Exportar série com metadados
          </a>
        )}
      </section>
    </div>
  );
}
function App() {
  const [data, setData] = useState<Dataset | null>(null),
    [comparison, setComparison] = useState<Comparison | null>(null);
  const [module, setModule] = useState("Visão Geral"),
    [selected, setSelected] = useState<Indicator | null>(null),
    [mobile, setMobile] = useState(false),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [reload, setReload] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      fetchJSON<Dataset>("/api/indicators", controller.signal),
      fetchJSON<Comparison>("/api/comparison", controller.signal),
    ])
      .then(([d, c]) => {
        setData(d);
        setComparison(c);
        setError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [reload]);
  const indicators = data?.indicators || [];
  const featured = ["population", "gdp_per_capita", "rcl", "health_units"];
  const visible =
    module === "Visão Geral"
      ? indicators.filter((i) => featured.includes(i.id))
      : indicators.filter((i) => i.module === module);
  const available = indicators.filter((i) => i.updatedAt).length;
  return (
    <div className="app">
      <aside className={"sidebar " + (mobile ? "open" : "")}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setModule("Visão Geral");
          }}
        >
          <div className="brand-mark">
            <Landmark size={24} />
          </div>
          <div>
            OBSERVATÓRIO
            <strong>
              TURVO <span>/ PR</span>
            </strong>
          </div>
        </a>
        <p className="nav-label">EXPLORE O MUNICÍPIO</p>
        <nav>
          {(
            data?.modules || [
              "Visão Geral",
              "Demografia",
              "Economia",
              "Finanças Públicas",
              "Saúde",
              "Educação",
              "Emprego",
              "Saneamento/Infraestrutura",
              "Compras Públicas/PNCP",
              "Transferências/convênios",
              "Comparação",
              "Fontes",
            ]
          ).map((m, i) => (
            <button
              key={m}
              className={module === m ? "active" : ""}
              onClick={() => {
                setModule(m);
                setMobile(false);
              }}
            >
              <span className="nav-number">
                {String(i + 1).padStart(2, "0")}
              </span>
              {moduleLabels[m] || m}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <ShieldCheck size={20} />
          <span>
            Dados públicos.
            <br />
            <strong>Decisões informadas.</strong>
          </span>
        </div>
      </aside>
      {mobile && (
        <button
          className="mobile-backdrop"
          onClick={() => setMobile(false)}
          aria-label="Fechar menu"
        />
      )}
      <main>
        <header className="topbar">
          <button
            className="menu-button"
            aria-label="Abrir menu"
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <span>
            Prefeitura Municipal de Turvo <span className="top-divider">/</span>{" "}
            Paraná
          </span>
          <span className="public-label">
            <span className="green-dot" /> Acesso público
          </span>
        </header>
        <div className="content">
          <div className="breadcrumb">
            Observatório municipal <span>/</span>{" "}
            {moduleLabels[module] || module}
          </div>
          <section className="hero">
            <div>
              <p className="eyebrow">TURVO, PARANÁ • IBGE 4127965</p>
              <h1>
                {module === "Visão Geral" ? (
                  <>
                    O município em <em>perspectiva.</em>
                  </>
                ) : (
                  moduleLabels[module] || module
                )}
              </h1>
              <p className="subtitle">
                {module === "Visão Geral"
                  ? "Conheça Turvo através de indicadores públicos. Informação acessível para acompanhar o presente e planejar o futuro."
                  : "Explore os dados oficiais, os períodos de referência e a metodologia de cada indicador."}
              </p>
            </div>
            <div className="hero-icon">
              <Building2 strokeWidth={1} size={70} />
            </div>
          </section>
          <div className="status-strip">
            <ShieldCheck size={16} />
            <span>Fontes oficiais via MCP Brasil</span>
            <span className="status-count">
              {available}/{indicators.length || "—"} indicadores com coleta
              validada
            </span>
            <button
              onClick={() => setReload(reload + 1)}
              disabled={loading}
              aria-label="Recarregar dados do cache"
            >
              <RefreshCw size={14} className={loading ? "spin" : ""} />{" "}
              Recarregar
            </button>
          </div>
          {error && (
            <div role="alert" className="notice">
              {error}{" "}
              <button onClick={() => setReload(reload + 1)}>
                Tentar novamente
              </button>
            </div>
          )}
          {loading && !data ? (
            <div className="empty" aria-live="polite">
              Consultando o cache de dados públicos…
            </div>
          ) : (
            <>
              {module === "Fontes" ? (
                <>
                  <div className="section-title">
                    <h2>Transparência desde a origem</h2>
                    <span className="unit-chip">
                      Catálogo de fontes e indicadores
                    </span>
                  </div>
                  <p className="plain-note">
                    Última coleta é a data em que o observatório recebeu os
                    dados. Referência é o período medido pela fonte. Indicadores
                    pendentes e indisponíveis nunca são convertidos em zero.
                  </p>
                  <div className="sources-grid">
                    {Object.entries(
                      Object.fromEntries(
                        indicators.map((i) => [i.source, i.sourceInfo]),
                      ),
                    ).map(([key, s]) => (
                      <section className="card source-card" key={key}>
                        <p className="eyebrow">FONTE OFICIAL</p>
                        <h2>{s.name}</h2>
                        <p className="plain-note">{s.description}</p>
                        <a href={s.url} target="_blank" rel="noreferrer">
                          Consultar fonte <ExternalLink size={13} />
                        </a>
                        {indicators
                          .filter((i) => i.source === key)
                          .map((i) => (
                            <button
                              key={i.id}
                              className="source-indicator"
                              onClick={() => setSelected(i)}
                            >
                              <span>{i.title}</span>
                              <span className={"badge " + i.status}>
                                {statuses[i.status]}
                              </span>
                              <small>
                                {i.method}
                                <br />
                                Referência: {i.period || "Não disponível"} •
                                Coleta: {date(i.updatedAt)}
                              </small>
                            </button>
                          ))}
                      </section>
                    ))}
                  </div>
                  <a
                    href="/api/sources"
                    target="_blank"
                    rel="noreferrer"
                    className="download"
                  >
                    Catálogo completo em JSON <ExternalLink size={14} />
                  </a>
                </>
              ) : module === "Comparação" ? (
                <section className="card comparison">
                  <div className="section-title">
                    <h2>Municípios com porte populacional semelhante</h2>
                    <span className={"badge " + comparison?.status}>
                      {statuses[comparison?.status || "unavailable"]}
                    </span>
                  </div>
                  <p>
                    {comparison?.method ||
                      "A seleção será calculada com populações oficiais do mesmo ano, entre municípios do Paraná."}
                  </p>
                  {comparison?.rows?.length ? (
                    <>
                      <div className="chart-body">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={comparison.rows}>
                            <CartesianGrid
                              strokeDasharray="3 5"
                              vertical={false}
                            />
                            <XAxis dataKey="name" fontSize={11} />
                            <YAxis fontSize={11} />
                            <Tooltip
                              formatter={(v) => fmt(Number(v), "pessoas")}
                            />
                            <Bar
                              dataKey="population"
                              name="População"
                              fill="#168570"
                              radius={[5, 5, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>Município</th>
                              <th>Código IBGE</th>
                              <th>População</th>
                              <th>Diferença de Turvo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {comparison.rows.map((r) => (
                              <tr key={r.code}>
                                <td>{r.name}</td>
                                <td>{r.code}</td>
                                <td>{fmt(r.population)}</td>
                                <td>{fmt(r.difference, "%")}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <div className="empty">
                      Comparação aguardando uma coleta validada.
                    </div>
                  )}
                  <div className="metadata">
                    <a
                      href={
                        comparison?.url ||
                        "https://sidra.ibge.gov.br/tabela/6579"
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      IBGE / SIDRA
                    </a>
                    <span>
                      Referência: {comparison?.period || "Não disponível"}
                    </span>
                    <span>Última coleta: {date(comparison?.updatedAt)}</span>
                  </div>
                </section>
              ) : (
                <>
                  <div className="section-title">
                    <h2>
                      {module === "Visão Geral"
                        ? "Um retrato de Turvo"
                        : "Indicadores do módulo"}
                    </h2>
                    <span className="subtle">
                      Clique para explorar os dados
                    </span>
                  </div>
                  <div className="metrics">
                    {visible.map((item) => (
                      <Card
                        key={item.id}
                        item={item}
                        onOpen={() => setSelected(item)}
                      />
                    ))}
                  </div>
                  {module === "Visão Geral" ? (
                    <>
                      <div className="charts-grid">
                        {["population", "gdp"]
                          .map((id) => indicators.find((i) => i.id === id))
                          .filter((i): i is Indicator => !!i)
                          .map((item) => (
                            <Chart item={item} key={item.id} />
                          ))}
                      </div>
                      <section className="card explore">
                        <div>
                          <p className="eyebrow">DO DADO À COMPREENSÃO</p>
                          <h2>Uma visão mais completa do município</h2>
                          <p>
                            Saúde, educação, emprego, finanças e infraestrutura.
                            <br />
                            Explore cada tema e acompanhe a origem dos números.
                          </p>
                        </div>
                        <button onClick={() => setModule("Fontes")}>
                          Conhecer as fontes <ArrowUpRight size={17} />
                        </button>
                      </section>
                    </>
                  ) : (
                    visible.map((item) => (
                      <React.Fragment key={item.id}>
                        <Chart item={item} />
                        <DataTable item={item} />
                      </React.Fragment>
                    ))
                  )}
                </>
              )}
            </>
          )}
          <footer>
            <span>Observatório Municipal de Turvo/PR</span>
            <span>
              Informação pública • Fontes identificadas • Sem dados simulados
            </span>
            <a
              href="https://github.com/Prefeitura-de-Turvo/observatorio-municipal"
              target="_blank"
              rel="noreferrer"
            >
              Código aberto <ExternalLink size={12} />
            </a>
          </footer>
        </div>
      </main>
      {selected && <Detail item={selected} close={() => setSelected(null)} />}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
