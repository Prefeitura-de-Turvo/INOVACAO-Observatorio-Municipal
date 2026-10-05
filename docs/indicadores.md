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
| IDEB municipal | Educação | INEP | índice | Planilhas municipais oficiais processadas por etapa/rede; cada linha mantém seu estrato e ano. |
| Vínculos formais • RAIS | Emprego | rais | vínculos | Estoque em 31/12, município do estabelecimento. Apenas agregados oficiais, sem microdados pessoais. Sem ferramenta RAIS na versão inspecionada. Aceita importação suplementar documentada de agregados oficiais. |
| Contratações publicadas no PNCP | Compras Públicas/PNCP | pncp | processos | Identificadores PNCP únicos por CNPJ municipal, ano de publicação e todas as modalidades/páginas.  |
| Contratos publicados no PNCP | Escritório de Compras Públicas | PNCP | contratos | Todos os contratos do CNPJ municipal e período anual; painel expõe dados agregados de valor/categoria/tipo de pessoa, não CNPJ/CPF nem nome do fornecedor. |
| Empresas ativas por porte e atividade econômica | Escritório de Compras Públicas | Receita Federal / CNPJ | empresas | Indicador pendente: depende de agregação municipal validada da base nacional CNPJ, CNAE, porte e SIMEI. Não será calculado com amostra ou cadastro individual. |
| Planos de transferências especiais | Transferências/convênios | transferegov | planos | Planos de ação únicos para o CNPJ da Prefeitura. Sem inferir valor pago.  |
| Propostas federais de parceria | Transferências/convênios | TransfereGov Gestão de Parcerias | propostas | API aberta filtrada pelo código IBGE. Propostas não equivalem a instrumentos celebrados, valores transferidos ou pagamentos. |

## Escritório de Compras Públicas

O módulo consolida contratos do PNCP e prevê o perfil local de MEI/ME/EPP e atividades econômicas necessário ao diagnóstico de compras públicas do Sebrae. A base CNPJ é nacional e volumosa; até que a carga completa mensal seja processada, os números por porte/CNAE ficam indisponíveis. O diagnóstico Sebrae também pode envolver documentos, CAF, licenças sanitárias, capacitação e atendimentos; não há integração confirmada desses cadastros locais. O termo “IDAM” não foi identificado pelo solicitante e não é associado automaticamente a um órgão ou sistema.

## Comparação

Seleciona até cinco municípios do Paraná com população entre 50% e 150% de Turvo no mesmo ano, ordenados pela menor diferença absoluta. Ausência de dado no ano exclui o município. Não afirma semelhança socioeconômica, nem compara anos distintos. O dashboard mostra fonte, referência, coleta, gráfico e tabela.
