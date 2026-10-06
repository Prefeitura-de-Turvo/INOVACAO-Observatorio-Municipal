# Validação da entrega

Validação com APIs reais em 06/10/2026. Estes resultados documentam coletas; não são valores fixados no frontend nem garantia de disponibilidade futura.

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
| IDEB municipal | 2023 (último ano habilitado na versão MCP Brasil fixada) | Adaptador implementado; download INEP indisponível nesta execução de validação |
| Vínculos formais • RAIS | Não disponível | Importador atualizado para layouts antigo e 2024+; série aguarda importação do microdado oficial |
| Contratações publicadas no PNCP | 20250101 a 20251231 | Coleta real validada |
| Contratos PNCP | 2025 | Coleta real validada; 158 contratos, sem identificação fiscal/nominal de fornecedor no cache |
| Planos de transferências especiais | 2025 | Coleta real validada |
| Propostas federais de parceria | 2025 | Coleta real validada; 12 propostas no endpoint público do TransfereGov |
| Empresas ativas e estabelecimentos por porte/CNAE | Não disponível | Importador completo implementado; aguarda processamento de uma edição mensal oficial completa da base CNPJ |
| IDAN-M • Sebrae/PR | Não disponível | Integração de catálogo e importador implementados; série de Turvo pendente de divulgação/extrato oficial municipal |
| Parcerias com instrumento assinado | 2025 | API consultada e vínculos por proposta validados; 0 registros com data de assinatura nesta consulta |
| Valor em ordens bancárias emitidas • parcerias | 2025 | API consultada; nenhum instrumento assinado nem ordem bancária associada foi encontrado nesta consulta |

Comparação validada com 6 municípios (Turvo e 5 pares populacionais do PR) e referência 2026. PNCP retornou 236 identificadores únicos do CNPJ municipal em 2025. FNDE/PNAE retornou registros por esfera e etapa, sem somá-los. RREO Simplificado validou RCL na coluna dos últimos 12 meses.

Verificações concluídas: build TypeScript/Vite; testes de integridade/API/RAIS e privacidade dos agregados; Ruff. A integração IDEB usou os URLs gerados pelo MCP Brasil, mas o host de download fechou a conexão no ambiente de validação; não publicamos resultados sem arquivo processado. As consultas de PNCP contratos e TransfereGov Gestão de Parcerias retornaram dados reais e paginação completa.

Falhas iniciais PNCP HTTP 204/429, filtros FNDE e demonstrativo SICONFI foram corrigidas após inspeção de respostas oficiais. O cache real, as evidências e os logs locais não são incluídos no Git. A instalação nova coleta seus próprios dados.

A aplicação foi executada localmente. Publicação em domínio público não foi realizada; o Pages/Tunnel está configurado em código e documentação, mas ainda requer conta Cloudflare, domínio, token de Tunnel e servidor persistente. RAIS e CNPJ requerem arquivos oficiais locais. O IDAN-M requer extrato oficial Sebrae/PR. A API TransfereGov também consulta parcerias assinadas e ordens bancárias; a coleta de 2025 não encontrou assinatura nem ordem associada às propostas de Turvo.
