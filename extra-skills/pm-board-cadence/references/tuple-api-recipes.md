# Receitas do TUPLE para a rotina do @pm

Todas usam `tuple-api`, nunca `curl` direto: ele lê a chave do projeto e a entrega
ao curl por stdin, então ela não aparece em `argv`, `ps`, log nem mensagem de erro.
**Nunca** faça `. .hermes/tuple.env` para "pegar as variáveis" — isso carrega a
chave no ambiente e ela vaza no primeiro `env` ou stack trace.

A convenção completa está na skill `kanban-tuple`; aqui ficam só os comandos.

## O board somado (é por onde a rotina começa)

```bash
tuple-api "$HERMES_PROJETOS/<Projeto>" board
```

Todos os projetos do workspace, já paginados e agrupados por status, com a lista
`atencao` do que passou do limite (IN_PROGRESS ≥ 3d, IN_REVIEW ≥ 5d, BLOCKED).

**Isto não é conveniência, é a única via dentro do cron.** Lá o sandbox bloqueia
`execute_code`, heredoc, `python -c` e `bash -c` por não haver ninguém para
aprovar, e a máquina não tem `jq` nem `python3`. As receitas abaixo que usam
python só valem em sessão interativa.

## Contexto do projeto (quando precisa de UM projeto)

```bash
P="$HERMES_PROJETOS/<Projeto>"
tuple-api "$P" contexto
# {"workspaceId":"...","projectId":"...","teamId":"...","projeto":"Ouvidoria","prefixo":"OUVI"}
```

Em shell, para reaproveitar:

```bash
eval "$(tuple-api "$P" contexto | python -c 'import json,sys
d = json.load(sys.stdin)
print("WS=%s; PROJ=%s" % (d["workspaceId"], d["projectId"]))')"
```

## Ler o board

```bash
tuple-api "$P" get issues.list "{\"workspaceId\":\"$WS\",\"projectId\":\"$PROJ\",\"limit\":100}" > issues.json
```

`limit` ≤ 100. Se `total` for maior, paginar com `offset`. Guarde em arquivo e
leia o arquivo — despejar 100 issues na resposta é desperdício de contexto
(skill `token-economy`).

Agrupar por coluna:

```bash
python -c "
import json
d = json.load(open('issues.json', encoding='utf-8'))
r = d.get('result', {}).get('data', d)
its = r if isinstance(r, list) else (r.get('items') or [])
from collections import Counter
for st, n in Counter(i.get('status') for i in its).most_common():
    print('%-16s %d' % (st, n))"
```

## Uma issue com comentários

```bash
tuple-api "$P" get issues.getByKeyWithDetails "{\"key\":\"OUVI-12\",\"workspaceId\":\"$WS\"}"
```

`issues.list` **não traz** `description` — tudo parece vazio. Para ler o conteúdo,
use `getByKey` ou `getByKeyWithDetails`.

## Comentar

```bash
tuple-api "$P" post issues.addComment \
  '{"issueId":"<id>","content":"[bot @pm] <fato objetivo>"}'
```

Todo comentário de bot começa com `[bot @pm]` — a chave age como o João, e sem a
marca ninguém distingue o que foi pessoa do que foi bot.

## Mover de coluna

Não existe endpoint de "mover card": coluna é `status` no `issues.update`.

```bash
tuple-api "$P" post issues.update '{"id":"<id>","status":"IN_PROGRESS"}'
```

**O @pm não move issue dos outros, e ninguém move para `DONE`.** `DONE` é o
GATE 3, revisão humana. `IN_REVIEW` parada há dias entra no relatório como
*pronta para fechar*, com a evidência — quem decide é a pessoa.

Também não se pula coluna: `BACKLOG → IN_PROGRESS` direto falha. Passe por `TODO`
em duas chamadas.

## Verificar o resultado

```bash
tuple-api "$P" post issues.update '{"id":"<id>","status":"TODO"}' | head -c 200
```

Sucesso traz `{"result":{"data"`; falha traz `{"error"`. **Não** use `grep` solto
no retorno: `grep '"status"'` casa com os dois e você lê erro como sucesso.

O `tuple-api` já sai com código diferente de zero quando o HTTP não é 2xx — use
isso em vez de inspecionar texto:

```bash
if tuple-api "$P" post issues.update '{"id":"<id>","status":"TODO"}' >/dev/null; then
  echo "ok"
else
  echo "falhou"
fi
```

## Quando dá erro

| mensagem | o que é |
|---|---|
| `401` | chave inválida |
| `403 API keys cannot access this resource` | recurso fora do alcance de qualquer API key (`members`, `workspaces`, `labels`...) — não insista |
| `403` numa chamada que funcionava | o `workspaceId` pode ter mudado; confira a data de validação no `tuple.env` |
| `missing required scope` | a chave é restrita demais; avise o humano, não contorne |
| `429` | limite de 120 req/min — espere, não repita em laço |

Nunca termine um pipeline de curl com `|| cat`: trava esperando stdin.
