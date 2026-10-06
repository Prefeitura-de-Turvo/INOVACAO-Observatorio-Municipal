# Inspeção do MCP Brasil

Inspeção em 05/10/2026 antes da implementação:

- Servidor conectado: `listar_features` retornou 42 features ativas e 10 ignoradas; SICONFI não estava habilitado.
- `search_tools` revelou schemas das ferramentas IBGE, educação, saúde, PNCP e TransfereGov.
- `call_tool(ibge_consultar_agregado, indicador=populacao, nivel=municipio, localidade=4127965, periodos=2025)` retornou tabela de Turvo/PR. Essa consulta foi usada para confirmar a interface, não como constante de produção.
- Código oficial, README, clientes, constantes e schemas foram lidos na revisão `2efb258370b125bbf190884283ae10f209b9d335`.

## Interfaces originais relevantes

| Interface | Parâmetros / cuidado |
|---|---|
| `ibge_consultar_agregado` | `agregado_id`, `variavel_id`, `nivel`, `localidade`, `periodos`; a tabela textual elimina a coluna de período |
| `siconfi_consultar_rreo` | `exercicio`, `periodo`, `ente_id`, `anexo`, `simplificado`, `esfera`; formatador trunca em 100 linhas |
| `saude_buscar_estabelecimentos` | `codigo_municipio` de 6 dígitos, `status`, `limit`, `offset`; API limita estabelecimentos a 20 |
| `fnde_consultar_pnae_alunos` | `ano` texto, `estado`, `municipio`, `limite`; filtro municipal parcial exige conferência exata |
| `compras_pncp_buscar_contratacoes` | datas YYYYMMDD, modalidade obrigatória, CNPJ e página; texto é filtro local |
| `transferegov_emendas_por_municipio` | nome municipal, ano e página; busca pelo nome requer validação adicional por CNPJ/UF |
| `inep_consultar_ideb` | `ano`, `etapa`, `nivel`; o MCP Brasil gera links oficiais XLSX, pois o INEP não oferece API REST para este conjunto |

O atalho IBGE `pib_per_capita` da versão inspecionada muda a consulta para nível nacional. Não é utilizado. A variável 543 da tabela 5938 representa impostos, não PIB per capita; a validação de unidade bloqueou essa hipótese na implantação. A implementação final calcula uma razão própria a partir de PIB e população em ano comum, deixando o método explícito.

O resumo CNES `resumo_rede_municipal` consulta leitos sem filtro municipal e profissionais com endpoint descontinuado. Não é utilizado. O PNCP retorna localização em `unidadeOrgao`, enquanto o parser original procura certos atributos em `orgaoEntidade`; o adaptador local preserva esses campos do JSON oficial. HTTP 204 do PNCP exige tratamento antes de decodificar JSON. O FNDE/Olinda interpreta `+` como operador em filtros OData; a extensão usa `%20` para espaços e modelos PNAE do pacote. Turvo entrega RREO Simplificado: o adaptador testa demonstrativos normal e simplificado, com paginação completa.

## Extensões locais

`integration/bridge.py` registra as extensões `observatorio_ibge`, `observatorio_entes`, `observatorio_fiscal`, `observatorio_cnes`, `observatorio_pnae`, `observatorio_ideb`, `observatorio_pncp`, `observatorio_pncp_contratos`, `observatorio_transferencias`, `observatorio_parcerias`, `observatorio_comparacao` e `observatorio_pib_por_habitante` no servidor MCP Brasil importado. São ferramentas deste observatório, não nomes anunciados pelo projeto upstream.

Mantêm clientes, constantes e modelos oficiais do pacote; consultas que requerem estrutura perdida nos formatadores usam `mcp_brasil._shared.http_client`. Não há LLM interpretando ou inventando números. Comparação usa lista real de municípios do PR e consultas IBGE em lotes; localizações múltiplas são separadas por vírgula dentro de `N6[...]`.

O MCP Brasil oferece retry/backoff para falhas transitórias. As correções locais PNCP usam sua fábrica HTTP e acrescentam tratamento de 204, validação de schema e espera em 429. Atualizar a dependência implica repetir testes de contrato e conferir clientes privados utilizados pelo bridge; não se atualiza automaticamente para main.

O adaptador IDEB usa links XLSX oficiais gerados pelo cliente INEP do MCP Brasil e exige `openpyxl`; o host de download pode ficar indisponível, mantendo o último cache validado. Gestão de Parcerias usa a API oficial `api-publica.transferegov.gestao.gov.br`: filtra propostas de Turvo pelo IBGE, junta cada proposta às parcerias pelo ID e publica separadamente assinaturas e ordens bancárias emitidas. A ordem bancária não é tratada como pagamento final. Contratos PNCP usam a API de consulta oficial e guardam apenas agregados públicos; CNPJ/CPF e nomes de fornecedores não entram na resposta estruturada armazenada pelo observatório.
