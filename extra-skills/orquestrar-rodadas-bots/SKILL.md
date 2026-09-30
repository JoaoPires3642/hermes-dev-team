---
name: orquestrar-rodadas-bots
description: Use ao disparar ou parar rodadas de bots numa KEY.
version: 1.0.0
author: Hermes Orquestrador
metadata:
  hermes:
    tags: [workflow, delegar, orquestracao]
---

# Orquestrar rodadas de bots

## When to Use

Ao disparar `hermes-delegar` numa KEY · ao acompanhar rodada em curso · ao precisar parar
um bot · ao receber issues que o humano já criou no board · ao triar artefato que chegou
pelo Telegram.

Complementa `fluxo-time` e `estado-tarefa` (que definem papéis, gates e a máquina de
estados). Aqui estão as armadilhas de **operar** as rodadas: o que quebra na prática ao
disparar, acompanhar e parar bots com `hermes-delegar` / `hermes-task`.

## Antes de disparar

1. **Leia o `assignee` da issue no TUPLE.** Issue atribuída a outra pessoa **não recebe
   bot** — em branch compartilhada os dois escrevem no mesmo arquivo sem se ver, e a
   colisão só aparece no merge. Dono é outro → `BLOCKED` com o motivo e avise o humano.
   Regra do João: *bot trabalha no que está atribuído a ele; issue de outro dev é dele*.
2. **Revise o handoff até a última linha.** O `hermes-delegar` monta o prompt no instante
   do disparo e **congela** o conteúdo do `.md` (confira em `runs/<KEY>/*.prompt.md`).
   Editar o handoff depois não alcança a rodada em curso — a premissa errada custa a
   rodada inteira. Descobriu tarde → conserte o arquivo para o futuro e leve a correção ao
   humano; ela só entra por rodada nova ou pelo `/ajustar` do gate.
3. **Confira se já há rodada em voo:** `hermes-delegar status "<projeto>" [KEY]`.

## Quando a story fica partida entre humano e bots

Issues irmãs que tocam o mesmo arquivo, umas do humano e outras dos bots: não siga calado.
Diga ao humano — ou ele combina a ordem com o outro dev, ou o @techlead aperta o
`allowed_paths` para não invadir.

## Caminho do projeto em host Windows

`hermes-task` e `hermes-delegar` recebem o caminho como argumento de programa nativo, e o
MSYS não traduz. Pasta com espaço no nome quebra com *"não é pasta de projeto"* mesmo
existindo `AGENTS.md`. Sempre:

```bash
cd "$HOME"/OneDrive*/Documentos/<projeto>     # glob: o cd é builtin, aceita
P=$(cygpath -m "$(pwd)")                      # nativo: precisa de C:/...
hermes-task show "$P" <KEY>
```

Comando humano que "não pegou" e não deixou linha no `audit.jsonl` quase sempre é isto —
peça a saída do erro antes de supor outra causa.

## Nunca mova estado com rodada rodando

Mover o estado por baixo de um bot em execução **mata o trabalho dele no meio**: ele
termina, tenta gravar (`set`/`move`) e leva `negado`, porque o estado que autorizava a
escrita já não é o mesmo. No audit o estrago aparece como `negado` seguido de
`delegar-fim ok` — **`ok` ali não significa etapa entregue**, só que o processo saiu sem
crashar. Ao ler o audit depois de um atropelo, reconstrua pela ordem dos timestamps antes
de concluir quem fez o quê.

Precisa parar um bot em voo → espere a rodada fechar e só então mova. Urgência real
(colisão com humano) justifica atropelar, mas registre no motivo do `BLOCKED` que havia
rodada em execução.

## Timeout não é falha de código — redisparar retoma

`status: falhou` com `.out.md` vazio e `exit` negativo, num tempo próximo do
`timeout_min` do `.json` da rodada, é o teto estourando — não erro do bot. A sessão
sobrevive ao processo: o disparo seguinte mostra `↻ Resumed session ... (N total
messages)` no `.err.log` e continua de onde parou. Redisparar é o certo; recomeçar do
zero joga fora o contexto já pago.

Antes de anunciar "morreu", leia `runs/<KEY>/<ts>-<bot>.json`: `inicio`, `fim`,
`timeout_min` e `exit` distinguem timeout de crash em uma olhada.

Da terceira rodada em diante na mesma KEY, pare de redisparar e leve ao humano: a
entrega é grande demais para uma passada, e a decisão (aumentar o teto ou partir a
task) é dele.

## Esperar rodada sem queimar turno

Polling em foreground estoura o limite da ferramenta e devolve o controle no meio. Para
rodada longa, espere em background com notificação e **encerre o turno**:

```bash
for i in $(seq 1 100); do
  s=$(hermes-delegar status "$P" <KEY> | tail -1)
  case "$s" in *rodando*) sleep 30;; *) break;; esac
done
```

com `background=true, notify=true`. Cuidado ao relatar: **a notificação de um monitor que
expirou não é o bot terminando** — confira o `hermes-delegar status` antes de dizer ao
humano que a rodada fechou.

## Limitação de ambiente não é bloqueio da entrega

Build que não sobe nesta máquina — feed privado sem token, dependência que exige
credencial, runtime ausente — é limitação **sua**, não impedimento da tarefa. Quando o
`AGENTS.md` do projeto já avisa que o build local não roda, tratar isso como bloqueio
gera retrabalho de desfazer status e comentário no board.

O caminho certo: `BLOCKED` **no manifest** (que é seu), handoff dizendo o que ficou sem
verificar e por quê, board intocado. Recusar `build=ok` no DoD continua valendo — você
não viu passar — mas recusar é diferente de parar.

O `hermes-task move` imprime `TUPLE: mova para <STATUS>` a cada transição. Isso é
**sugestão, não ordem**: para `BLOCKED` por ambiente, ignore a sugestão.

## Commit local para revisão humana

Antes de commitar em nome de uma KEY, confira `hermes-delegar status` — **nunca commite
com rodada em execução**: o dev pode estar no meio de uma edição e o commit congela
arquivo pela metade. Commit local (sem push) para o humano revisar é pedido comum ao fim
de uma implementação; use `git-bot commit` e mostre o `git show --stat`.

## Status atual não é histórico — confira antes de contradizer

O humano afirma que um bot fez algo; você lê o estado de agora e não vê. Pode estar
vendo **a correção dele**, não a ausência do fato. Antes de dizer "não aconteceu", leia o
rastro: `grep <KEY> .hermes/audit.jsonl` incluindo as linhas `tuple-api` com
`"metodo":"post"` (as escritas), os comentários da issue e o `historico` do manifest.
Contestar a memória do humano com leitura parcial queima confiança e custa mais turnos
que a conferência.

## Sair de BLOCKED é só do humano

`--by humano` é bloqueado para bot por desenho. Não tente contornar: entregue o comando
pronto, em bloco colável, e diga qual saída esperar.

```bash
cd "$HOME"/OneDrive*/Documentos/<projeto>
P=$(cygpath -m "$(pwd)")
hermes-task move "$P" <KEY> <ESTADO_ANTERIOR> --by humano --ev motivo="..."
```

Sai de `BLOCKED` só para o `estado_anterior` do manifest (ou `CLOSED`). **Confirme no
manifest que o estado mudou** antes de seguir: humano dizendo "liberei" não é evidência, e
seguir em cima disso queima a rodada seguinte.

## Quando as issues já existem no board

Entrada comum: o humano já criou as issues no TUPLE e manda "pode orquestrar". O fluxo
normal (issues nascem pós-GATE 1) fica invertido, e o risco é duplicar — `issues.create`
não é idempotente.

- O GATE 1 continua necessário, e não por burocracia: `hermes-task new <ISSUE>
  --herda-gate1 CALL-N` **recusa** se a call não tiver GATE 1. Sem ele as issues não
  entram no fluxo (não chegam a @techlead, spec, dev). Diga isso assim ao humano que quer
  pular etapa — o argumento é o travamento concreto, não o processo.
- No handoff do @po, escreva **"não proponha criar issue"** de forma literal.
- O papel do @pm vira mover coluna e comentar, não criar.

### Como falar disso com o humano

Quem já criou as issues **tem medo concreto de duplicação no board**. Nunca descreva
passos internos com verbos que soem escrita no board ("adotar", "registrar", "dar entrada
nas issues"): ele lê como "vai mexer no TUPLE" e a conversa trava. Diga o que o comando
faz, no concreto: *`hermes-task new` escreve um arquivo local
(`.hermes/tasks/<KEY>/manifest.yaml`); a issue no board não é tocada.*

Voltou a dúvida → **mostre em vez de explicar**: total de issues antes/depois e o
`createdAt` das issues em questão. Evidência encerra; reafirmação não.

## Artefato que chega pelo Telegram (entrada não-call)

Copie para `<projeto>/.hermes/entradas/<AAAA-MM-DD>-<nome>` (o cache do perfil é volátil),
abra `hermes-task new CALL-N` e siga o rito de triagem.

No resumo, **cruze o documento com o board** e diga o que já tem issue e o que não tem — é
o que evita trabalho duplicado adiante.

Retorno de QA é sempre **teste do estado atual**: nenhum item pode ser dimensionado como
"talvez já resolvido por issue anterior em revisão". Havendo issue anterior sobre o mesmo
sintoma, a pergunta ao humano não é *"o bug existe?"* e sim *"o que fazer com a issue
antiga, em revisão sem ter resolvido?"*.
