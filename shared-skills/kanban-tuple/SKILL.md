---
name: kanban-tuple
description: Aplique antes de qualquer operação no Kanban Tuple (fonte da verdade das tasks). Cobre autenticação por variável de ambiente, convenção tRPC, ciclo de vida obrigatório da issue, o que a API key não alcança e o que exige OK humano.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [tuple, kanban, issues]
---

# Kanban Tuple

**Tuple** (`https://api.tuple.hypesoft.com.br`) é o Kanban próprio da Hypesoft e a
**fonte da verdade das tasks**. Tudo que o time de bots decide vira issue lá; nada
fica só na conversa.

## Autenticação

- A chave vem **só** da variável `TUPLE_API_KEY` (cofre / `.env` do profile).
  **Nunca** escrever a chave em skill, SOUL, AGENTS.md, commit, comentário ou log.
- Toda request: `Authorization: Bearer $TUPLE_API_KEY`.
- A chave age **como o membro que a criou** (o João). Por isso todo comentário e
  toda descrição criada por bot começa com `[bot @<seu-nome>]`.
- Erros: `401` chave inválida · `403` fora do escopo/projeto (a chave pode não
  alcançar o projeto — avisar o humano, não insistir) · `429` limite de 120 req/min.

## Identificadores do projeto

`workspaceId`, `projectId`, `teamId`, prefixo das issues e `assigneeId` ficam no
`AGENTS.md` da pasta do cliente (`~/clientes/<cliente>/AGENTS.md`). Ler de lá;
se faltar algum, perguntar ao humano — não chutar.

Para descobrir o ID de uma pessoa: ler o objeto `assignee` de uma issue que ela
já tenha (`members.*` é inacessível pela API).

## Convenção de chamada (tRPC, sem REST)

- **Query** — `GET /trpc/<proc>?input=<JSON url-encoded>`
- **Mutation** — `POST /trpc/<proc>` com o JSON no body

```bash
curl -s "https://api.tuple.hypesoft.com.br/trpc/issues.getByKey?input=$(jq -rn --arg k SELL-12 --arg w "$WS" '{key:$k,workspaceId:$w}|@uri')" \
  -H "Authorization: Bearer $TUPLE_API_KEY"

curl -s -X POST https://api.tuple.hypesoft.com.br/trpc/issues.addComment \
  -H "Authorization: Bearer $TUPLE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"issueId":"<id>","content":"[bot @dev-back] PR aberto: <link>. CAs cobertos: 1, 2, 4."}'
```

- `issues.list`: `limit` ≤ 100; paginar com `offset` usando o `total`.
- `status` é um valor só. Não existe "mover card": é `issues.update` com `status`.
- Procedures úteis: `issues.list`, `issues.getById`, `issues.getByKey`,
  `issues.getByKeyWithDetails`, `issues.create` (`title` + `teamId` obrigatórios;
  `parentId` para subtask), `issues.update`, `issues.addComment`,
  `issues.addRelation` (`BLOCKS` · `RELATES_TO` · `DUPLICATES`), `issues.statusHistory`,
  `projects.list`, `projects.getById`.

### Fora do alcance de qualquer API key

`labels`, `members`, `teams`, `roles`, `workspaces`, `workflowStates`, `agents`,
`connectors`, `notetaker`, `automations` — bloqueados por design. Labels sugeridas
saem como texto no comentário. `cycles.*` só com escopo `cycles:read`.

## Status

`BACKLOG` · `TODO` · `IN_PROGRESS` · `IN_REVIEW` · `BLOCKED` · `DONE` · `CANCELLED` · `DUPLICATE`
Prioridade: `URGENT` · `HIGH` · `MEDIUM` · `LOW` · `NONE`

**O workflow não deixa pular coluna**: `BACKLOG → IN_PROGRESS` direto falha. Passar
por `TODO` (duas chamadas).

## Ciclo de vida (regra de ouro: nenhuma issue é trabalhada sem dono e na coluna certa)

| Momento | Status | Dono |
|---|---|---|
| Criada, não priorizada | `BACKLOG` | — |
| Selecionada para execução | `TODO` | — |
| **Antes da primeira alteração de código** | **`IN_PROGRESS`** | **assinar** |
| **PR aberto, aguardando revisão** | **`IN_REVIEW`** | mantém |
| Parada por dependência/decisão | `BLOCKED` | mantém (comentário diz o que destrava) |
| Merge feito e CAs verificados | `DONE` | **só a revisão humana move** |

Nunca `DONE` por implementação parcial, teste falhando ou CA não verificado.

## Permissão

- **Livre**: ler; assinar a issue que está executando; mover status do próprio
  trabalho; comentar progresso.
- **Criar issue**: só depois do GATE 1 aprovado. Nasce em `BACKLOG`, anunciada na
  sala com `key` e título.
- **Só com OK humano explícito**: alterar título/descrição/prioridade de issue
  existente, reatribuir issue de **outra pessoa**, `CANCELLED`, `DUPLICATE`,
  `issues.delete`. Desfazer o que outra pessoa escreveu é caro.

## Comentários

PT-BR, curtos, factuais, começando com `[bot @<nome>]`. Um por transição relevante.
Ao `IN_REVIEW`: branch/PR + CAs cobertos. Ao `BLOCKED`: o que destrava.
