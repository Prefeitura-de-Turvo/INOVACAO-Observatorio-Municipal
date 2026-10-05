# Deploy e operação

## Publicação em servidor

1. Clone o repositório, copie `.env.example` para `.env` e confira parâmetros.
2. Construa o frontend e ambiente Python, ou use `docker compose up --build -d`.
3. Configure reverse proxy HTTPS para `127.0.0.1:8000`, domínio e certificado sob controle da Prefeitura.
4. Preserve o volume de dados. Não publique o sidecar MCP nem arquivos `.env`, logs, banco ou evidências brutas.
5. Consulte `/api/health`, `/api/indicators` e a tabela `runs` após a primeira coleta. Processo saudável não implica fontes saudáveis.

O CNPJ pode ser obtido automaticamente do cadastro de entes SICONFI por IBGE 4127965. Na inspeção inicial, esse cadastro confirmou `78279973000107`; não usar CNPJ de Turvo/SC. Um valor manual deve ser conferido em fonte oficial. A validação PNCP confirma o código territorial na resposta.

## Agendamento

Agendador interno padrão: a cada 24 horas, com verificação de necessidade a cada minuto. Configurar `REFRESH_HOURS` sem criar tarefas por visitante. Backend deve usar um worker e permanecer ativo. A CLI permite coleta seletiva e é protegida por lock no mesmo banco.

O template do workflow GitHub prevê coleta às 09:30 UTC (06:30 São Paulo), ou manualmente. Está em `docs/github-actions/`, aguardando ativação em `.github/workflows/` por credencial com escopo `workflow`; essa permissão não estava disponível na entrega. Produz um artefato de evidência e sinaliza `partial` como falha. Não distribui esse banco ao deploy. Não executar duas instâncias escrevendo no mesmo SQLite via sistema de arquivos remoto; adotar PostgreSQL e worker dedicado para réplicas.

## Observabilidade e recuperação

`runs.detail` identifica erros por fonte; `cache.error` sinaliza erro público genérico. Retentar após corrigir configuração/API. Não substituir a última resposta validada por arrays vazios após falhas. O dashboard mostra `stale` quando TTL expira ou tentativa falha.

SQLite WAL: para backup consistente em operação, usar `sqlite3.Connection.backup()` ou comando `.backup`; não copiar apenas o arquivo principal durante escritas. Restaurar para um volume vazio, iniciar e verificar metadados. Evidências podem crescer; definir retenção institucional. Não remover evidências sem política de auditoria.

## Limites e disponibilidade

PNCP: todas as modalidades 1–14, 50 registros/página, máximo de 100 páginas/modalidade; exceder o limite bloqueia totais. Pode sofrer HTTP 429 e demorar. Timeout da ferramenta PNCP mínimo de 300 segundos; demais ferramentas, 90 segundos, configurável.

CNES: 20 registros/página, limite de 2.000 antes de bloquear a publicação. FNDE: limite de 10.000; fontes não retornando schema reconhecido são indisponíveis. SICONFI: cadência mínima de uma consulta/segundo. Comparação: filtro do PR e ±50% de população, não uma classificação geral de equivalência entre cidades.

Dockerfile incluído com usuário sem privilégios e healthcheck. A publicação em infraestrutura externa e o provisionamento de domínio/certificado dependem do ambiente de hospedagem escolhido; não foram realizados nesta entrega.
