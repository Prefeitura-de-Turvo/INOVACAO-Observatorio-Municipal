# Publicação no Cloudflare Pages e Cloudflare Tunnel

O frontend é uma aplicação estática Vite e pode ser implantado no Cloudflare Pages. A API permanece no backend FastAPI, porque a ingestão MCP Brasil, o agendador e o cache SQLite precisam de processo e armazenamento persistentes. O Tunnel conecta o Pages à API sem abrir porta de entrada no servidor. O Pages e o Tunnel são produtos distintos da Cloudflare.

## 1. Criar o projeto Pages

No painel Cloudflare, abra **Workers & Pages → Create application → Pages → Connect to Git** e selecione `Prefeitura-de-Turvo/observatorio-municipal`. Configure:

- Root directory: `/`
- Build command: `npm run build`
- Build output directory: `dist`
- Build environment: `NODE_VERSION=22`
- Build variable: `VITE_API_BASE_URL=https://api.seu-dominio.gov.br`

O domínio da API é o hostname público que você vai configurar no Tunnel. Use um hostname controlado pela Prefeitura. Configure a variável para Production e Preview. O valor é incorporado ao frontend durante o build, portanto, alterá-lo exige novo deploy. O projeto é estático; não configure backend Pages Functions.

O arquivo `wrangler.jsonc` declara `pages_build_output_dir: ./dist` para que o Wrangler identifique o destino como **Cloudflare Pages** e não tente publicar o diretório usando uma configuração de Workers Static Assets. O nome configurado é `observatorio-municipal`; mantenha esse nome igual ao nome do projeto Pages no painel. No projeto Pages, não use `wrangler deploy` como comando de publicação de Worker. A configuração atual do projeto é `npm run build` com saída `dist`.

## 2. Publicar o backend pelo Tunnel

No servidor que manterá o SQLite e executará o coletor, instale Docker Compose e clone o repositório. Copie `.env.example` para `.env` e configure:

```dotenv
CORS_ORIGINS=https://seu-projeto.pages.dev,https://seu-dominio.gov.br
CORS_ORIGIN_REGEX=^https://([a-z0-9-]+\.)?seu-projeto\.pages\.dev$
CLOUDFLARED_TUNNEL_TOKEN=TOKEN_DO_TUNNEL
```

Inclua o domínio Production e o domínio institucional em `CORS_ORIGINS`. Para URLs Preview variáveis, use uma expressão regular ancorada apenas ao nome do seu projeto Pages como no exemplo, substituindo `seu-projeto`; não permita todos os subdomínios `pages.dev`. O backend já publica a porta apenas em loopback no host; o serviço Tunnel conversa com o backend pela rede privada do Compose.

Crie no painel um Tunnel **remotamente gerenciado** e configure um Public Hostname para `api.seu-dominio.gov.br`, serviço `http://observatorio:8000`. Copie o token para o arquivo `.env` no servidor (nunca para o GitHub ou para uma variável `VITE_*`) e inicie os serviços:

```bash
docker compose up -d --build observatorio
docker compose --profile tunnel up -d cloudflared
docker compose ps
```

Se já iniciou o backend, o segundo comando acrescenta o serviço do Tunnel ao mesmo projeto Compose. Não habilite políticas de login no Access para o hostname da API pública do dashboard; a API é somente leitura, e políticas de autenticação impediriam visitantes anônimos. Não exponha o MCP sidecar nem a porta 8000 publicamente.

## 3. Conferir conectividade

Abra `https://api.seu-dominio.gov.br/api/health`. O retorno deve conter `"status":"ok"`. Depois abra o domínio Pages e confirme que os módulos carregam dados. Se o navegador acusar CORS, inclua a origem exata do site em `CORS_ORIGINS`, reinicie o backend e publique de novo. Não use `*` como origem CORS.

O hostname da API serve apenas a API, então não precisa publicar o frontend pelo Tunnel. Também é possível servir o dashboard e a API juntos no mesmo backend, conforme as instruções em [deploy](deploy.md), sem Pages.

## Limites

Pages hospeda o build estático, não o serviço FastAPI nem seu arquivo SQLite. O backend precisa continuar ativo em máquina/servidor com armazenamento persistente e saída de rede para as fontes públicas e para a Cloudflare. Para alta disponibilidade, troque o armazenamento/lock SQLite por PostgreSQL e execute o coletor em worker persistente.
