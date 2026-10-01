---
name: kanban-tuple
description: Aplique antes de qualquer operação no Kanban Tuple (fonte da verdade das tasks). Cobre autenticação por variável de ambiente, convenção tRPC, ciclo de vida obrigatório da issue, o que a API key não alcança e o que exige OK humano.
version: 1.1.0
author: Joao Pires
metadata:
  hermes:
    tags: [tuple, kanban, issues]
---

# Kanban Tuple

**Tuple** (`https://api.tuple.hypesoft.com.br`) é o Kanban próprio da Hypesoft e a
**fonte da verdade das tasks**. Todo **trabalho** que o time decide entregar vira issue
lá; nada disso fica só na conversa. Andamento, explicação e contexto **não** são task:
vão para `<projeto>/memory/` ou, se falam de uma issue existente, para um comentário nela.
Issue sem nada a entregar polui o board e gera trabalho de limpeza para o dono.

## Autenticação

- **Cada projeto tem a sua API key**, em `<pasta-do-projeto>/.hermes/tuple.env`
  (`TUPLE_API_KEY=...`, chmod 600, fora de qualquer repo).
- **Sempre** chame a API pelo helper `tuple-api` — ele lê a chave do projeto e
  nunca a expõe em comando, log ou saída. Nunca leia, imprima ou copie a chave.
- A chave age **como o membro que a criou** (o João). Por isso todo comentário e
  toda descrição criada por bot começa com `[bot @<seu-nome>]`.
- Erros: `401` chave inválida · `403` fora do escopo/projeto (a chave pode não
  alcançar o projeto — avisar o humano, não insistir) · `429` limite de 120 req/min.

## Identificadores do projeto

Ficam no **`.hermes/tuple.env`** da pasta do projeto, ao lado da chave — não no
`AGENTS.md`, que é tabela preenchida à mão e cujo parse quebra calado.

**Só dois são obrigatórios**, porque só eles não são descobríveis:

| campo | por quê |
|---|---|
| `TUPLE_API_KEY` | óbvio |
| `TUPLE_WORKSPACE_ID` | com a chave sozinha, `workspaces.list` e `users.me` dão **403** (`API keys cannot access this resource`), e todo o resto exige `workspaceId` na entrada |
| `TUPLE_PROJECT` | opcional: nome ou id. Necessário quando o workspace tem mais de um projeto — e normalmente tem |

**`projectId` e `teamId` você NÃO guarda** — e **não leia o `tuple.env`**: a chave
mora nele. Peça o contexto, que resolve os IDs e nunca imprime a chave:

```bash
tuple-api "$P" contexto
# {"workspaceId":"...","projectId":"...","teamId":"...","projeto":"Ouvidoria","prefixo":"OUVI"}
```

Use esses valores nas chamadas seguintes. Erros dele são instrutivos: se o
workspace tiver mais de um projeto e `TUPLE_PROJECT` estiver vazio, ele **lista
os projetos disponíveis** em vez de escolher por você.

Para o panorama, não peça `contexto`: `tuple-api "$P" projetos` lista todos os
projetos do workspace e `tuple-api "$P" board` devolve cada um já paginado e
somado por status. Em rotina de cron esses dois são a **única** via — lá o
sandbox recusa `python -c`, heredoc e `execute_code`, e não há `jq` nem `python3`.

Guardar menos evita o erro caro: colar o `projectId` de um cliente no `tuple.env`
de outro **escreve no board errado**, e ninguém percebe na hora.

Anote no `tuple.env` **a data em que validou o `workspaceId`**. Ele muda se o
workspace for recriado, e o sintoma é `403` em chamada que antes funcionava.

Para descobrir o ID de uma pessoa: ler o objeto `assignee` de uma issue que ela
já tenha (`members.*` é inacessível pela API).

## Convenção de chamada (tRPC, sem REST)

- **Query** — `GET /trpc/<proc>?input=<JSON url-encoded>`
- **Mutation** — `POST /trpc/<proc>` com o JSON no body

```bash
# a pasta do projeto: $HERMES_PROJETOS/<Projeto> no Linux, ~/Documents/<Projeto> no Windows
P=$HERMES_PROJETOS/<Projeto>

# query  (GET  /trpc/<proc>?input=...)
tuple-api "$P" get  issues.getByKey '{"key":"ABC-12","workspaceId":"<ws>"}'

# mutation (POST /trpc/<proc>)
tuple-api "$P" post issues.addComment \
  '{"issueId":"<id>","content":"[bot @dev-back] PR aberto: <link>. CAs cobertos: 1, 2, 4."}'
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

## Armadilhas reais da API (aprendidas em produção)

- **IDs numa chamada só:** `projects.getById` devolve `teamId`, `workspaceId`,
  `issueTypes` e `workflowStatuses`. Não garimpe teamId de issue.
- **`type` omitido NÃO fica em branco: vira `bug`.** É silencioso — a issue nasce
  errada e ninguém percebe até alguém olhar o board. Aconteceu de verdade: oito
  issues seguidas criadas como `bug` por omissão, e outras três tiveram que ser
  convertidas depois. **Sempre mande `type` explícito** no `issues.create`.
- **Dono: você LÊ, mas não atribui.** `issues.list` e `issues.getByKeyWithDetails`
  devolvem `assignee` completo — `{id, name, email}` — quando alguém pegou a issue.
  Verificado em 30/09/2026. (Esta skill afirmava o contrário até então, porque em
  29/09 o board inteiro estava sem dono; era observação daquele dia virada regra.)
  Para atribuir continua faltando o id: `members.list` responde 403 para API key e
  não existe `users.list` — mas agora dá para copiar o `assignee.id` de uma issue que
  a pessoa já tenha. **Cuidado**: `assignee` vem como `null` quando ninguém pegou, não
  ausente — teste `i.get("assignee") and i["assignee"].get("name")`.
- **Dono é POR ISSUE. Nunca conclua o lote pela primeira.** Issues criadas na mesma
  rodada costumam ter donos diferentes: em 30/09, de cinco issues, três eram de uma
  pessoa e duas de outra — e um bot bloqueou as cinco citando o nome errado em duas,
  porque leu uma e generalizou. Se a decisão depende de quem é dono, leia **cada uma**.
  `labelIds` continua fora do alcance: label sugerida vai como texto no comentário.
- **Anexo**: `issues.getAttachmentDownloadUrl '{"id":"<attachmentId>"}'` devolve
  URL assinada que **expira em ~10 min** — baixe na hora, não guarde o link.
- **`type` é validado contra o WORKSPACE, não o projeto** — o `issueTypes` do projeto
  pode omitir `epic`/`story`. Descubra a lista real com uma sonda que falha por
  definição: `tuple-api "$P" post issues.update '{"id":"<qualquer>","type":"__probe__"}'`
  (a mensagem de erro lista os tipos válidos). Nunca sonde com valor que possa ser
  válido. `chore` não existe: use `improvement` ou `task` e deixe o prefixo no título.
- **`estimate` é validado contra a escala do time** (padrão fibonacci 0,1,2,3,5,8,13,21).
  Só em task (skill `tuple-definition-of-ready`).
- **Payload com jq, nunca string interpolada** (descrição tem aspas, crase, quebra de
  linha): `jq -n --rawfile d corpo.md '{title:"...",description:$d,...}' > payload.json`
  e depois `tuple-api "$P" post issues.create @payload.json`.
- **Verificar com `issues.getByKey`** e medir `description|length`. `issues.list` não
  traz description (tudo parece vazio); `issues.getById` traz `type` nulo;
  `issues.getRelations` devolve `{from,to}`, não array.
- **Criar NÃO é idempotente** — e bots e humanos dividem a mesma chave. Para criar
  várias issues, grave `ref → key → id` num log **antes** de descer para o próximo
  item e pule o que já estiver no log (retomável e à prova de execução concorrente).
  Log em `<projeto>/.hermes/tuple-log/`, fora de repo. Travou/perdeu o retorno →
  confira no board antes de tentar de novo.
- **Pai antes de filho**: `parentId` só aceita id que já existe. Valide a árvore
  inteira (tipos, estimates) antes de criar a primeira.
- Nunca `|| cat` no fim de um pipeline de curl (trava esperando stdin).
- `projects.list` pede `workspaceId`; o nome é `getById`, não `byId`.

## Status

`BACKLOG` · `TODO` · `IN_PROGRESS` · `IN_REVIEW` · `BLOCKED` · `DONE` · `CANCELLED` · `DUPLICATE`
Prioridade: `URGENT` · `HIGH` · `MEDIUM` · `LOW` · `NONE`

**O workflow não deixa pular coluna**: `BACKLOG → IN_PROGRESS` direto falha. Passar
por `TODO` (duas chamadas).

## Ciclo de vida (regra de ouro: nenhuma issue é trabalhada fora da coluna certa)

**Quem está trabalhando aparece no comentário, não no campo dono.** A coluna `Dono`
abaixo é o que se espera do lado humano; o bot não preenche.

| Momento | Status | Dono |
|---|---|---|
| Criada, não priorizada | `BACKLOG` | — |
| Selecionada para execução | `TODO` | — |
| **Antes da primeira alteração de código** | **`IN_PROGRESS`** | comentar `[bot @nome] assumindo` |
| **PR aberto, aguardando revisão** | **`IN_REVIEW`** | mantém |
| Parada por dependência/decisão | `BLOCKED` | mantém (comentário diz o que destrava) |

### O board não é o seu diário de bordo

O TUPLE é lido por **pessoas** — o dono da issue, quem vai revisar, quem planeja a
sprint. O status ali responde *"como está o trabalho?"*, não *"como foi o meu turno?"*.
São coisas diferentes e vivem em lugares diferentes:

| o que aconteceu | board do TUPLE | manifest (`hermes-task`) |
|---|---|---|
| trabalho depende de decisão, de outra issue ou de alguém | `BLOCKED` ✅ | `BLOCKED` |
| **o SEU ambiente falhou** — feed sem token, build sem dependência, runtime ausente | **não toque** | `BLOCKED` ✅ |

**Limitação sua não é bloqueio da issue.** Se o `npm run build` não roda porque a
máquina não tem token do feed privado, o trabalho não está parado: *você* está. Marcar
`BLOCKED` no board faz o dono da issue e o planejamento acreditarem que a entrega
travou — e ninguém consegue distinguir isso de um impedimento real. Aconteceu em
30/09 na SELL-78, e o humano teve que desfazer status e comentário.

Nesse caso: `BLOCKED` **no manifest** (que é seu), handoff para o humano, e o board
fica como está. Quem decide se aquilo vira bloqueio de verdade é a pessoa.

**O comentário segue a mesma régua.** É registro do trabalho, não relatório de
diagnóstico: uma ou duas linhas sobre a issue. Log de erro, comando que você tentou,
nome de ferramenta de autenticação e teoria sobre o ambiente vão para o handoff —
o board não é lugar de despejo. E o que **não** foi verificado, isso sim entra, curto:
*"testes verdes; build não verificado (feed privado)"*.
| Merge feito e CAs verificados | `DONE` | **só a revisão humana move** |

Nunca `DONE` por implementação parcial, teste falhando ou CA não verificado.

## Permissão

- **Livre**: ler; mover status do próprio trabalho; comentar progresso — inclusive
  o comentário que marca que você assumiu, já que o campo dono não é preenchível.
- **Criar issue**: só depois do GATE 1 aprovado. Nasce em `BACKLOG`, anunciada na
  sala com `key` e título.
- **Só com OK humano explícito**: alterar título/descrição/prioridade de issue
  existente, reatribuir issue de **outra pessoa**, `CANCELLED`, `DUPLICATE`,
  `issues.delete`. Desfazer o que outra pessoa escreveu é caro.

## Comentários

PT-BR, curtos, factuais, começando com `[bot @<nome>]`. Um por transição relevante.
Ao `IN_REVIEW`: branch/PR + CAs cobertos. Ao `BLOCKED`: o que destrava.
