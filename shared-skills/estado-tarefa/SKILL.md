---
name: estado-tarefa
description: Aplique em toda tarefa. Manifest da tarefa, máquina de estados fiscalizada pelo hermes-task (quem move, com que evidência), Definition of Done, contrato de API entre front e back, handoff estruturado e estratégia de branch por projeto.
version: 1.3.0
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
P=$HERMES_PROJETOS/<Projeto>
hermes-task new  "$P" KEY --objetivo "..." --agentes dev-back,dev-front [--ui] --herda-gate1 CALL-N   # @pm, por issue criada
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
| TRIAGED → AWAITING_APPROVAL | @po | `proposta=` `evidencias=` `corpos=` (skill `call-para-proposta`; o hermes-task confere evidência × proposta) |
| AWAITING_APPROVAL → SPECIFYING | **humano** (GATE 1) | `issues=...` `via=telegram:<uid>:<msg>` |
| AWAITING_APPROVAL → TRIAGED | **humano** (GATE 1: ajustar) | `motivo=...` (volta ao @orquestrador; máx. 3) |
| AWAITING_APPROVAL → TRIAGED | `auditor` (hermes-delegar, antes do gate sair) | `motivo=...` `auditoria=<arquivo>` (volta ao @po; máx. 2) |
| SPECIFYING → CLOSED | @po | só `CALL-N`: `issues=KEY1,KEY2` — a call virou issues e cada uma segue sozinha |
| TRIAGED → CLOSED | @orquestrador ou @po | só `CALL-N` **sem trabalho**: `sem_trabalho=<por quê>` + `memoria=<arquivo>` — o humano é avisado com o motivo |
| SPECIFYING → AWAITING_SPEC_APPROVAL | @techlead | `story=<arq>` `dor=ok` `decisoes=<o que você pergunta>` + `contrato=<arq>` se front+back + `allowed_paths` de cada dev |
| SPECIFYING → SPEC_APPROVED | @techlead, **sem gate** | `story=<arq>` `dor=ok` `sem_decisoes=<por que não há o que decidir>` + o mesmo `contrato`/`allowed_paths` acima |
| AWAITING_SPEC_APPROVAL → SPEC_APPROVED | **humano** (GATE 2) | `via=...` |
| IMPLEMENTING → SPECIFYING | **humano** | `motivo=` — recurso contra GATE 2 dispensado |
| IMPLEMENTING / AWAITING_SPEC_APPROVAL → CLOSED | **humano** | `atendido=` — o trabalho já existe |
| SPEC_APPROVED → IMPLEMENTING | @techlead | `specs=<dir>` `branch=<nome>` |
| IMPLEMENTING → TESTING | @dev-* | `handoff=<arq>` — só vira TESTING quando **todos** os devs da tarefa entregaram |
| TESTING → CHANGES_REQUESTED | @qa | `relatorio=<arq>` `para=dev-x` (conta 1 volta; **3ª volta → BLOCKED automático**) |
| TESTING → AWAITING_REVIEW | @qa | **DoD** (abaixo) |
| AWAITING_REVIEW → MERGED | **humano** (GATE 3) | `via=...` |
| MERGED → DEPLOYED / HOMOLOGATING → CLOSED | **humano** | — |
| qualquer → BLOCKED | qualquer um | `motivo=...` — **só humano tira** |

Aprovação humana chega **por comando no Telegram** (`/aprovar`, `/ajustar`, `/rejeitar`)
e quem registra `--by humano` é o **`call-dispatch`** — código, chamado pelo plugin
`hermes-gates` sem modelo no caminho, com `via=telegram:<uid>:<msg>` conferido contra
`TELEGRAM_ALLOWED_USERS`. **Bot nenhum** usa `--by humano`: bloqueado por
`approvals.deny` (Hermes) e pela política do Kiro. Humano disse "ok" em texto livre?
Peça o comando; não registre.

**A call é uma tarefa** (`CALL-N`): o GATE 1 é dado nela. Cada issue que o @pm cria nasce
com `--herda-gate1 CALL-N` — direto em `SPECIFYING`, com a aprovação herdada; o
`hermes-task` recusa se a call não tiver GATE 1.

Depois da spec aprovada, `agentes`, `allowed_paths`, `escopo`, `criterios_aceite` e
`tem_ui` **travam**: só humano muda. Precisou mudar escopo → `BLOCKED` e peça.

## Definition of Done (TESTING → AWAITING_REVIEW)

### Commit é a ÚLTIMA coisa, não a primeira

A ordem é: dev implementa **sem commitar** → `TESTING` → @qa tenta build e roda os testes
→ aprovou → `AWAITING_COMMIT` → **aí** o dev commita, dá push e move `AWAITING_REVIEW`.

No board isso significa: a issue fica em `IN_PROGRESS` o tempo todo e **só vira
`IN_REVIEW` quando o código verificado subiu**. Antes era o contrário — o dev commitava
e abria PR antes do QA olhar, então código não verificado já estava na branch
compartilhada e a issue aparecia em revisão sem ninguém ter conferido nada.

Quem assina o quê não muda: o **@qa** assina o DoD (`TESTING → AWAITING_COMMIT`), o
**dev** assina o commit (`AWAITING_COMMIT → AWAITING_REVIEW`, com `commit=<sha>`). O dev
não declara o que o QA verificou, e o QA não sobe código.

PR deixou de ser exigido no DoD: vai para `IN_REVIEW` com o commit na branch, e o PR o
humano abre quando quiser.

O @qa só move com todas as evidências — e o `hermes-task` confere no git que nenhum
arquivo saiu de `allowed_paths`:

`build=ok|na` · `lint_typecheck=ok|na` · `testes=ok` · `integracao=ok|na` · `seguranca=ok` ·
`ca=ok` (todos os critérios verificados) · `revisao=<arquivo>` (skill `revisao-codigo`) ·
`evidencia_visual=<arquivo>` (se `tem_ui`) · `pr=<url>` · `tuple=ok` (issue atualizada).

`ok` é afirmação sua, registrada com seu nome no audit: **só escreva `ok` para o que você
rodou e viu passar**. Gerar código não é "feito".

### `na` é para o que não roda aqui — e só

`build` e `lint_typecheck` aceitam `na` porque existe projeto onde o comando **não roda
nesta máquina e nunca vai rodar**: o feed npm privado do agregador exige PAT, e bot não
manuseia PAT. Nesses casos o projeto declara o que não roda no próprio `AGENTS.md`.

Leia o `AGENTS.md` **antes** de recusar. Se o comando está listado lá como não
verificável:

- escreva `na`, não `ok` — você não viu passar, e mentir aqui é pior que a limitação;
- **não** marque `BLOCKED` e **não** peça waiver ao humano: a decisão já foi tomada
  quando alguém escreveu aquilo no `AGENTS.md`, e pedir de novo a cada tarefa gasta a
  pessoa à toa;
- escreva uma linha no comentário da issue dizendo o que ficou sem verificar.

Se o comando **não** está listado e mesmo assim falhou, aí sim é achado: relate. A
diferença entre "decidimos que não roda" e "quebrou hoje" é o que separa waiver de bug.

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
