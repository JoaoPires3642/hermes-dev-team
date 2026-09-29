---
name: pm-board-cadence
description: Aplique na rotina diária do @pm. Varre o board do TUPLE, cobra BLOCKED, sinaliza risco de prazo e PROPÕE fechamento — nunca fecha: DONE é o GATE 3, revisão humana. Audiência - @pm.
version: 1.0.0
author: Hermes PM
license: CC0
metadata:
  hermes:
    tags: [pm, kanban, cadence, review, tuple]
---

# PM Board Cadence

## When to Use

Load this skill when acting as `@pm` and need to:
- Run daily board review (start of workday)
- Triage issues, identify blockers, flag stalled work
- Propor fechamento do que está em review com evidência — quem fecha é o humano
- Report board status and coordinate with @dev, @qa, @po

**Role**: `@pm` (Project Manager). Cuida de prazo, cycles e bloqueadores. Rotina diária no board do TUPLE: varre status, cobra o que destrava, propõe fechamento com evidência e sinaliza risco. Não move para DONE e não altera escopo, prioridade ou dono.

**Reference**: `references/tuple-api-recipes.md` traz os comandos prontos (ler board, comentar, mover coluna, tratar erro) — todos via `tuple-api`, nunca curl direto.

## Daily Routine (weekdays, start of day)

### Step 1: Pull current board state

Query `issues.list` for the workspace and project:

```bash
P="$HERMES_PROJETOS/<Projeto>"

# IDs resolvidos sem tocar na chave
eval "$(tuple-api "$P" contexto | python -c 'import json,sys;d=json.load(sys.stdin);print("WS=%s; PROJ=%s" % (d["workspaceId"], d["projectId"]))')"

tuple-api "$P" get issues.list "{\"workspaceId\":\"$WS\",\"projectId\":\"$PROJ\",\"limit\":100}" > issues.json
```

**Nunca** faça `. .hermes/tuple.env`: isso carrega a `TUPLE_API_KEY` no seu
ambiente, e daí ela vaza em qualquer `env`, log ou mensagem de erro. O
`tuple-api` lê a chave e a passa ao curl por stdin — ela não aparece nem em `ps`.

**Pitfall**: `limit` ≤ 100; acima disso, paginar com `offset` usando o `total`.
Guarde em arquivo e leia o arquivo; não imprima a resposta inteira.

### Step 2: Summarize by status

Group issues:
- **IN_PROGRESS** > 5 days: flag as stalled, check comments for blockers
- **IN_REVIEW** > 5 dias: candidatas a fechamento se o QA aprovou — entram no relatório, não no `issues.update`
- **BLOCKED**: extract "o que destrava" from comments
- **DONE** vs total: burndown %; BACKLOG: future work not yet started

Report to user:
```
✅ Taxa conclusão: X%
🚀 Em movimento: N (IN_PROGRESS + IN_REVIEW)
🚫 Bloqueadas: N (motivo citado)
📋 Backlog: N (frentes de trabalho futuras)
```

### Step 3: IN_REVIEW parada — PROPOR fechamento, nunca fechar

**Você não move nada para `DONE`.** `DONE` é o GATE 3, a única revisão humana no
fim do fluxo (skill `fluxo-time`). Uma issue fechada sem revisão fica idêntica a
uma revisada — o erro não aparece depois, e é por isso que a regra é absoluta.

Uma versão anterior desta skill se autorizava a fechar após 5 dias com evidência.
Era bem-intencionada e mesmo assim errada: decidir que a evidência basta **é** a
revisão.

O que fazer com `IN_REVIEW` parada há mais de 5 dias:

- [ ] Verificar se há comentário de QA aprovado ou verificação manual.
- [ ] **Com evidência** → listar no relatório como *pronta para fechar*, com a
      `key`, há quantos dias está parada e qual comentário sustenta isso. Quem
      fecha é o humano.
- [ ] **Sem evidência** → é outra coisa: está esperando alguém **testar**, não
      você decretar. Cobre o @qa por @menção e registre no relatório.

Comentar é livre — marque que você olhou:

```bash
tuple-api "$P" post issues.addComment \
  '{"issueId":"<id>","content":"[bot @pm] Em IN_REVIEW há N dias, QA aprovado em <data>. Pronta para o GATE 3."}'
```

**Pitfall**: Bare grep/pattern matching on curl output (e.g., `grep '"status"'`) can match both success and error responses silently. Verify with `head -c 200` or JSON parser: success contains `{"result":{"data"`, errors contain `{"error"`.

### Step 4: Check blockers

For each `BLOCKED` issue, verify the comment says **o que destrava** (what unblocks it). If comment is empty or vague, add one:

```bash
tuple-api "$P" post issues.addComment \
  '{"issueId":"<id>","content":"[bot @pm] Confirmando destravador: <fato específico, decisão pendente ou pessoa>. CC @responsável."}'
```

Cite the person/team who can unblock via @mention (they get notified).

### Step 5: Flag risks

Issues > 3 days in same state with no progress → potential risk. Criteria:
- IN_PROGRESS x 3 dias = dev travado → ask @dev
- IN_REVIEW x 5 dias = revisão travada → ask @qa / owner
- BLOCKED sem comentário claro = política/decisão pendente → escalate

Report high-risk issues to user in Telegram/Desktop with:
- Issue key + title
- Current status + days stuck
- Last comment date (or "no comments")
- Recommended action ("check with @dev", "QA verdict?", etc.)

## Cadence

- **Weekdays, start of day** (e.g., 9 AM): run routine, report summary + risks
- **Same day evening** (e.g., 5 PM, optional): quick check for urgent blockers
- **Weekly** (Friday): review BACKLOG, update impediments log, plan next week

## Handoff to devs / QA

When an issue needs action:
- `@dev` if IN_PROGRESS is stalled → include last commit hash / branch / error from logs
- `@qa` if IN_REVIEW is stalled → ask for verdict + evidence (test result, screenshot, build link)
- `@po` if BLOCKED by product decision → what is the open question?

Always cite the issue key and keep the comment thread **on the Tuple board**, not in side chat. Future PM sessions read the board history, not Slack.

## No scope changes, no repriorization without OK

**Per `fluxo-time`:** PM does NOT alter issue scope, priority, or owner without explicit human OK. If you see an issue that looks wrong (title mismatch, priority low but critical), **comment to confirm, don't move**. Decisions about scope belong to @po + @techlead.
