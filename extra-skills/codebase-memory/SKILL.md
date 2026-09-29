---
name: codebase-memory
description: Aplique antes de explorar código. Use o grafo do codebase-memory-mcp (busca estrutural, call chains, arquitetura, impacto de diff) em vez de ler arquivo por arquivo.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [code, graph, mcp, impact]
---

# codebase-memory-mcp (grafo do código)

MCP local ([DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp),
MIT, sem rede/telemetria). Disponível nas sessões kiro-cli de @techlead, @dev-front,
@dev-back e @qa como `@codebase-memory-mcp`.

## Primeiro uso em um repo

1. `list_projects` — o repo já está indexado?
2. Se não: `index_repository(repo_path="<caminho ABSOLUTO do repo>")`
   (ex.: `$HERMES_PROJETOS/<Projeto>/<repo>` expandido). Depois disso o índice se mantém
   sozinho (watcher).
3. `get_graph_schema` e `get_architecture(aspects=['all'])` para se situar.

O nome do projeto no grafo vem do caminho (ex.: `home-joaop-Documentos-Proj-repo`);
pegue em `list_projects` e passe como `project` nas outras chamadas.

## Quando usar o quê

| Preciso de… | Ferramenta |
|---|---|
| achar função/classe/rota pelo nome | `search_graph` (use regex: `name_pattern=".*Parte.*"`) |
| quem chama X / o que X chama | `trace_path` (profundidade 1–5) |
| código de uma função | `get_code_snippet` |
| estrutura de um arquivo | `get_file_outline` |
| texto solto (string, config) | `search_code` |
| o que meu diff afeta (blast radius) | `detect_changes` |
| visão geral do repo | `get_architecture` |

## Por papel

- **@techlead**: `get_architecture` + `trace_path` para preencher "Arquivos a
  Criar/Modificar" e "Dependências" da story com base real, não chute.
- **@dev-***: antes de editar, `trace_path` na função alvo para ver quem quebra.
- **@qa**: `detect_changes` no diff da branch para escolher o que testar e onde
  cabe regressão.

Grafo é ponto de partida: confirme lendo o trecho antes de afirmar que algo
"não existe" ou "não é usado".
