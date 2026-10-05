# Validação da entrega

Validação com APIs reais em 05/10/2026. Estes resultados documentam uma coleta; não são valores fixados no frontend nem garantia de disponibilidade futura.

| Indicador | Referência observada | Situação |
|---|---|---|
| População estimada | 2026 | Coleta real validada |
| Área territorial | 2010 | Coleta real validada |
| PIB municipal | 2023 | Coleta real validada |
| PIB por habitante • calculado | 2021 | Coleta real validada |
| Alfabetização • 15 anos ou mais | 2022 | Coleta real validada |
| Domicílios ligados à rede de esgoto/pluvial | 2022 | Coleta real validada |
| Receita corrente líquida | 2025 / 6º bimestre | Coleta real validada |
| Estabelecimentos de saúde ativos | Cadastro corrente; competência não informada pela API | Coleta real validada |
| Alunos atendidos pelo PNAE | 2022 | Coleta real validada |
| IDEB municipal | Não disponível | Integração complementar pendente |
| Vínculos formais • RAIS | Não disponível | Integração complementar pendente |
| Contratações publicadas no PNCP | 20250101 a 20251231 | Coleta real validada |
| Planos de transferências especiais | 2025 | Coleta real validada |
| Convênios federais | Não disponível | Integração complementar pendente |

Comparação validada com 6 municípios (Turvo e 5 pares populacionais do PR) e referência 2026. PNCP retornou 236 identificadores únicos do CNPJ municipal em 2025. FNDE/PNAE retornou registros por esfera e etapa, sem somá-los. RREO Simplificado validou RCL na coluna dos últimos 12 meses.

Verificações concluídas: build TypeScript/Vite; 20 testes de integridade/API/RAIS; Ruff; imagem Docker construída e API /health confirmada no container; verificação visual desktop e móvel, menu, comparação, tabelas e metadados, sem erros no console.

Falhas iniciais PNCP HTTP 204/429, filtros FNDE e demonstrativo SICONFI foram corrigidas após inspeção de respostas oficiais. O cache real, as evidências e os logs locais não são incluídos no Git. A instalação nova coleta seus próprios dados.

A aplicação foi executada localmente. Publicação em domínio público não foi realizada; os arquivos de deploy e instruções estão incluídos. RAIS requer arquivo real, IDEB municipal e convênios tradicionais requerem homologação complementar.
