---
name: estado-tarefa
description: Aplique em toda tarefa. Manifest da tarefa, máquina de estados fiscalizada pelo hermes-task (quem move, com que evidência), Definition of Done, contrato de API entre front e back, handoff estruturado e estratégia de branch por projeto.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [workflow, state-machine, dod, contract, handoff]
---

# Estado da tarefa — o que vale é o `hermes-task`, não a conversa

Uma tarefa só está no estado que o **manifest** diz. Bot nenhum "acha" que algo está
pronto: ele **move** a tarefa com `hermes-task`, que recusa transição sem permissão ou
sem evidência (e registra a tentativa em `<projeto>/.hermes/audit.jsonl`).

```
<projeto>/.hermes/tasks/<KEY>/
├── manifest.yaml     # contrato principal da tarefa (estado, escopo, allowed_paths, aprovações, artefatos)
├── contrato.yaml     # contrato de API entre front e back (quando os dois trabalham)
└── handoffs/NN-<de>-para-<para>.md
```

## Comandos

```bash
P=~/Documentos/<Projeto>
hermes-task new  "$P" KEY --objetivo "..." --agentes dev-back,dev-front [--ui]   # @orquestrador
hermes-task show "$P" KEY
hermes-task set  "$P" KEY 'allowed_paths.dev-back=["repos/api/src/clientes/**"]' --by techlead
hermes-task move "$P" KEY <ESTADO> --by <você> --ev chave=valor ...
hermes-task check-paths "$P" KEY [--agente dev-back]
hermes-task states        # tabela completa de transições
```

Saída 1 = negado (leia o motivo e corrija, não tente contornar) · 3 = circuit breaker.
Depois de cada `move`, o comando diz o status do TUPLE: mova lá também (`tuple-api`).

## Estados e quem move

| De → Para | Quem | Evidência obrigatória |
|---|---|---|
| RECEIVED → TRIAGED | @orquestrador | `resumo=<arquivo>` |
| TRIAGED → AWAITING_APPROVAL | @orquestrador | `proposta=<arquivo>` (árvore + horas) |
| AWAITING_APPROVAL → SPECIFYING | **humano** (GATE 1) | `issues=KEYS` `via=telegram:<id>` |
| SPECIFYING → AWAITING_SPEC_APPROVAL | @techlead | `story=<arq>` `dor=ok` + `contrato=<arq>` se front+back + `allowed_paths` de cada dev |
| AWAITING_SPEC_APPROVAL → SPEC_APPROVED | **humano** (GATE 2) | `via=...` |
| SPEC_APPROVED → IMPLEMENTING | @techlead | `specs=<dir>` `branch=<nome>` |
| IMPLEMENTING → TESTING | @dev-* | `handoff=<arq>` — só vira TESTING quando **todos** os devs da tarefa entregaram |
| TESTING → CHANGES_REQUESTED | @qa | `relatorio=<arq>` `para=dev-x` (conta 1 volta; **3ª volta → BLOCKED automático**) |
| TESTING → AWAITING_REVIEW | @qa | **DoD** (abaixo) |
| AWAITING_REVIEW → MERGED | **humano** (GATE 3) | `via=...` |
| MERGED → DEPLOYED / HOMOLOGATING → CLOSED | **humano** | — |
| qualquer → BLOCKED | qualquer um | `motivo=...` — **só humano tira** |

Aprovação humana chega pelo Telegram/Desktop; quem registra é o @orquestrador com
`--by humano --ev via=telegram:<id da mensagem>`. Os demais bots são **impedidos pela
política do Kiro** de usar `--by humano`. Nunca registre aprovação que não aconteceu.

Depois da spec aprovada, `agentes`, `allowed_paths`, `escopo`, `criterios_aceite` e
`tem_ui` **travam**: só humano muda. Precisou mudar escopo → `BLOCKED` e peça.

## Definition of Done (TESTING → AWAITING_REVIEW)

O @qa só move com todas as evidências — e o `hermes-task` confere no git que nenhum
arquivo saiu de `allowed_paths`:

`build=ok` · `lint_typecheck=ok` · `testes=ok` · `integracao=ok|na` · `seguranca=ok` ·
`ca=ok` (todos os critérios verificados) · `revisao=<arquivo>` (skill `revisao-codigo`) ·
`evidencia_visual=<arquivo>` (se `tem_ui`) · `pr=<url>` · `tuple=ok` (issue atualizada).

`ok` é afirmação sua, registrada com seu nome no audit: **só escreva `ok` para o que você
rodou e viu passar**. Gerar código não é "feito".

## Contrato de API (front + back em paralelo)

Antes de liberar os dois devs, o @techlead escreve `contrato.yaml` e ambos implementam
**contra ele**, sem reinterpretar:

```yaml
task_id: ABC-123
endpoints:
  - method: POST
    path: /customers
    request:  { name: string, email: string }
    responses:
      201: Customer
      409: { code: DuplicateEmail }
tipos:
  Customer: { id: string, name: string, email: string }
eventos: []        # mensageria, se houver
```

Mudou o contrato no meio → volta ao @techlead; os dois devs atualizam.

## Handoff estruturado

Todo handoff (`handoffs/NN-<de>-para-<para>.md`) começa com um cabeçalho de comando:

```yaml
---
task_id: ABC-123
de: dev-back
para: qa
acao: testar            # implementar | testar | corrigir | especificar | revisar
allowed_paths: ["repos/api/src/customers/**", "repos/api/test/customers/**"]
saidas_exigidas: [testes, relatorio]
voltas_qa: 1/3
---
```

Seguido do corpo curto da skill `fluxo-time` (feito, contrato, arquivos, CAs, como verificar, pendências).

## Branch (definida por projeto no `AGENTS.md`)

- **por-tarefa**: branch `feature/<KEY>-<slug>` a partir da base do projeto; front e
  back na mesma branch da tarefa, cada um só em seus `allowed_paths`; integra por PR.
- **compartilhada**: branch do time; `pull --rebase` antes de todo push, nunca `--force`.

Em ambos: todo commit cita `Refs: <KEY>` — é assim que o `hermes-task` sabe quais
arquivos a tarefa tocou.
