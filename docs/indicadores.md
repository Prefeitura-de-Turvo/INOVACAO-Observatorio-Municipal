# Catálogo inicial de indicadores

Valores são obtidos em execução; nenhum valor é fixado neste catálogo. Período disponível vem da fonte, sem supor atualidade pela data de coleta.

| Indicador | Módulo | Fonte | Unidade | Método / limitação |
|---|---|---|---|---|
| População estimada | Demografia | ibge | pessoas | Série anual de estimativas; não interpolar anos de Censo.  |
| Área territorial | Demografia | ibge | km² | Área oficial municipal em km².  |
| PIB municipal | Economia | ibge | R$ | PIB a preços correntes. Conversão de mil reais para reais.  |
| PIB por habitante • calculado | Economia | ibge | R$ | PIB municipal dividido pela população estimada, no último ano comum às duas séries. Não equivale ao PIB per capita oficial quando a base populacional difere.  |
| Alfabetização • 15 anos ou mais | Educação | ibge | % | Censo 2022, total de sexo, cor/raça e idade.  |
| Domicílios ligados à rede de esgoto/pluvial | Saneamento/Infraestrutura | ibge | % | Tabela 6805, categoria 46290: inclui rede geral, pluvial ou fossa ligada à rede. Não equivale a esgoto tratado.  |
| Receita corrente líquida | Finanças Públicas | siconfi | R$ | RREO Anexo 03, RCL (III), coluna TOTAL (ÚLTIMOS 12 MESES). Sem somar receitas componentes.  |
| Estabelecimentos de saúde ativos | Saúde | cnes | unidades | Contagem por CNES único, território validado e todas as páginas. Competência não informada pela API. O horário da coleta não substitui o período da fonte. |
| Alunos atendidos pelo PNAE | Educação | fnde | alunos | Registros FNDE por esfera/etapa, território exato. Não somar linhas sem validação de sobreposição.  |
| IDEB municipal | Educação | inep | índice | Processar microdados municipais por rede e etapa antes da publicação. Conector municipal de microdados ainda não homologado; o MCP disponibiliza catálogo e downloads. |
| Vínculos formais • RAIS | Emprego | rais | vínculos | Estoque em 31/12, município do estabelecimento. Apenas agregados oficiais, sem microdados pessoais. Sem ferramenta RAIS na versão inspecionada. Aceita importação suplementar documentada de agregados oficiais. |
| Contratações publicadas no PNCP | Compras Públicas/PNCP | pncp | processos | Identificadores PNCP únicos por CNPJ municipal, ano de publicação e todas as modalidades/páginas.  |
| Planos de transferências especiais | Transferências/convênios | transferegov | planos | Planos de ação únicos para o CNPJ da Prefeitura. Sem inferir valor pago.  |
| Convênios federais | Transferências/convênios | transferegov | convênios | Não confundir transferências especiais com convênios. O conector MCP atual cobre transferências especiais; convênios dependem de integração complementar homologada. |

## Comparação

Seleciona até cinco municípios do Paraná com população entre 50% e 150% de Turvo no mesmo ano, ordenados pela menor diferença absoluta. Ausência de dado no ano exclui o município. Não afirma semelhança socioeconômica, nem compara anos distintos. O dashboard mostra fonte, referência, coleta, gráfico e tabela.
