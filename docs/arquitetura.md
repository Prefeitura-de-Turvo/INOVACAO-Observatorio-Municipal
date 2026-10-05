# Arquitetura

```mermaid
flowchart LR
  visitante[Visitante] --> react[React / Vite / Recharts]
  react --> api[FastAPI: leitura pública]
  api --> cache[(SQLite WAL: cache e evidências)]
  scheduler[Agendador / CLI] --> lock[Lock transacional]
  lock --> client[FastMCP Client]
  client --> bridge[MCP Brasil + extensões locais]
  bridge --> oficiais[IBGE / SICONFI / CNES / FNDE / PNCP / TransfereGov]
  client --> validacao[Validação de território / período / unidade / completude]
  validacao --> cache
  arquivo[RAIS oficial verificada] --> importador[Importador suplementar de agregados]
  importador --> cache
```

## Componentes e decisões

Frontend React 19/TypeScript com navegação por tema, cards, séries e gráficos Recharts, tabelas pesquisáveis/paginadas, modal de metodologia e exportação de séries. Não consulta APIs governamentais no navegador. Fontes, estilos e assets são locais; sem dependência de fontes externas. Layout responsivo com menu móvel, foco visível e preferência de movimento reduzido.

FastAPI serve a API somente leitura e o build do frontend. O ciclo da aplicação cria uma tarefa assíncrona de coleta; consultas públicas seguem disponíveis durante ingestão. Respostas possuem headers de segurança e cache HTTP de 60 segundos. Não há endpoint público de atualização, URL proxy livre ou execução de ferramenta arbitrária.

SQLite em WAL armazena: `cache` por indicador; `evidence` por coleta bem-sucedida; `runs` por execução; `locks` para evitar jobs concorrentes. Um lock de duas horas expira em caso de encerramento abrupto. Gravação de cache e evidência é atômica. Falhas atualizam tentativa/erro, preservando payload e data da última coleta bem-sucedida. Falhas de uma fonte não impedem as demais.

MCP Brasil é executado como sidecar stdio no mesmo ambiente Python fixado por `uv.lock`. Esse isolamento mantém ferramentas e credenciais fora do frontend. HTTP privado é uma alternativa para separar serviços. As extensões usam clientes do MCP Brasil e preservam dados que os formatadores textuais descartam. O checksum/revisão do código-fonte do fornecedor aparece no catálogo da API.

## Ingestão

IBGE mantém JSON de origem, variável, classificação, município, unidade, períodos e URL. Variações monetárias são nominais; sem deflacionamento implícito. Séries não interpolam períodos faltantes. PIB por habitante usa apenas a interseção de anos do PIB municipal e estimativas populacionais.

CNES faz paginação de 20 estabelecimentos por página e confere todos os códigos municipais antes de contar identificadores únicos. Sem extrapolar a primeira página. Competência desconhecida permanece desconhecida. Profissionais descontinuados e leitos potencialmente nacionais não são publicados.

PNCP trata HTTP 204 como ausência legítima de registros, valida o schema da resposta 200, pagina com `totalPaginas`/`totalRegistros`, confere CNPJ e `unidadeOrgao.codigoIbge`, deduplica `numeroControlePNCP` e consulta todas as modalidades 1–14. Limites ou mudança do total durante coleta impedem a publicação. Requisições são espaçadas e HTTP 429 respeita espera/backoff. APIs indisponíveis produzem estado de erro, não coleção vazia falsa.

TransfereGov pagina e filtra CNPJ e UF; não atribui emendas de Turvo/SC a Turvo/PR. A contagem é de planos de transferências especiais. FNDE expõe registros por etapa/esfera sem soma potencialmente duplicada. SICONFI exige linha e coluna únicas para RCL e não soma todos os valores monetários da declaração.

## Limites operacionais

A versão inicial opera em uma instância com disco persistente. Para escala, trocar SQLite/locks por PostgreSQL, agendador por worker dedicado e acrescentar Redis para respostas derivadas; o modelo de proveniência permanece. Evidências não têm remoção automática: estabelecer política de retenção e backup em produção. Índices públicos nunca devem conter microdados pessoais. RAIS mantém apenas resultado agregado e hash de entrada.
