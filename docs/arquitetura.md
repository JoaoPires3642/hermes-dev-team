# Arquitetura — time de bots de dev (Hermes + TUPLE + kiro-cli)

> Diagrama visual: [`docs/arquitetura.excalidraw`](arquitetura.excalidraw) — abra em
> excalidraw.com (menu → Abrir). Este texto é a fonte da verdade; o desenho segue atrás.

## 1. Entradas
- **Call** → **OpenWhispr** (open source, MIT): transcreve e separa quem falou **localmente**,
  sem bot entrar na reunião. O `openwhispr-notes` lê o SQLite dele e escreve uma nota Markdown
  por call em `~/Documents/_calls/<cliente>/`. A pasta da reunião no app vira só **sugestão**
  de cliente: quem decide é o humano.
  > **Por evento, e o humano diz o cliente.** O exportador roda de 15 em 15 min (custo zero, é só
  > Python lendo SQLite) e, **só quando criou nota**, chama o `call-dispatch varrer` (`--ao-criar`).
  > Cada nota vira `CALL-N` e o humano recebe no Telegram *"de qual cliente?"*. Nenhum modelo
  > roda até ele responder `/cliente CALL-N <projeto>` — call pessoal ou de teste se ignora
  > (`/ignorar`) e não custa nada. Com a resposta, o `call-dispatch` confere que
  > `$HERMES_PROJETOS/<projeto>/AGENTS.md` existe (nunca chuta o parecido) e abre uma sessão
  > do @orquestrador **só daquela call**, na pasta do projeto (§2).
  > **A API e o MCP do OpenWhispr são em nuvem e pedem plano pago**; não são usados. Ler o SQLite
  > é grátis e local, mas **não é contrato público**: mudança de schema dele quebra a ponte
  > (foi o que aconteceu com o `transcript`, que é JSON de segmentos e não texto).
  > Saímos do Granola (MCP pago) e depois da Meetily (diarização e export de Markdown são PRO).
- **Issue marcada no TUPLE** (bug, pedido, PBI existente) → routine do @orquestrador.
- **Artefatos / PBIs** enviados pelo humano no Telegram/Desktop.

## 2. Hermes — Bot Mode
- Bot = profile persistente (SOUL, memória, skills, routines). Bot ≠ subagente.
- **Cérebro por bot**: @orquestrador (`claude-opus-5`), @po (`claude-sonnet-5-5`) e @pm
  (`claude-haiku-4-5`) vão direto no Claude; @techlead, @dev-front, @dev-back e @qa ficam no
  `kiro-cli`, que é a conta da empresa e onde vivem os agentes Kiro e o grafo do código.
  O @orquestrador é o único que lê entrada externa não confiável, então é o que menos se
  economiza; o @pm faz trabalho quase mecânico todo dia útil, então é o mais barato.
- **Sessão por tarefa, nunca a Bot Chat.** Trabalho vai pelo `hermes-delegar`, que abre
  `hermes -p <bot> chat --in <projeto> --continue <KEY>-<bot>`: sessão com nome próprio por
  tarefa e por bot, na pasta do cliente, com o `AGENTS.md` dele e **zero histórico de outro
  cliente**. A mesma tarefa retoma a mesma conversa (ajuste de gate volta com contexto).
  Motivo: a `Bot Chat` é **uma por bot, eterna, na home**, e junta todos os clientes; quando
  enche, o Hermes compacta e o bot responde sobre o projeto errado sem erro nenhum na tela.
  O `hermes-delegar` também confere em código o que a skill não garante: pasta é projeto
  dentro de `$HERMES_PROJETOS`, handoff na pasta da tarefa, e **é a vez daquele bot** no
  estado do manifest (ninguém chega no dev antes do GATE 2). Roda destacado; um supervisor
  grava o resultado em `<projeto>/.hermes/runs/<KEY>/` e avisa no Telegram gate, falha,
  timeout e `BLOCKED`.
- **Gates pelo Telegram, registrados por código.** O humano responde com comando —
  `/cliente`, `/aprovar`, `/ajustar`, `/rejeitar`, `/ignorar`, `/pendentes` — e o plugin
  `hermes-gates` (só no profile do @orquestrador) roda no gateway **depois da autorização e
  antes de qualquer turno do modelo**: repassa ao `call-dispatch` com
  `--via telegram:<uid>:<msg>`, que confere o `uid` em `TELEGRAM_ALLOWED_USERS` e só então
  registra `--by humano` no `hermes-task`. A aprovação nunca é a palavra de um bot.
  Bots não podem rodar `call-dispatch`, `hermes -p`/`hermes chat` cru, nem `--by humano`:
  `approvals.deny` no Hermes (vale até sob `--yolo`) e regra de negação no Kiro. Limite
  honesto: os bots rodam como o mesmo usuário do SO, então isso é cerca, não cofre.
- **Fluxo:** `/cliente` → @orquestrador (sessão `CALL-N`) → resumo + proposta →
  **GATE 1** → `/aprovar` → @pm cria as issues no TUPLE, cada uma com
  `hermes-task new <ISSUE> --herda-gate1 CALL-N` (nasce em `SPECIFYING`) → @po escreve as
  stories → @techlead, uma rodada por issue → **GATE 2** → `/aprovar` → @techlead gera o
  `.kiro/specs` e libera os devs → último dev a entregar chama o @qa → **GATE 3** (PR).
- **`message_agent` / Bot Chat** ficam para recado curto. Duas condições para existir:
  `profile.yaml` com `hermes-bots` e sessão chamada exatamente `Bot Chat` (portão em
  `tools/bot_mode_dm.py`); o instalador cria as duas. As `Bot Chat` são ocultas por design
  (`hermes sessions list` não mostra). Chat do bot aberto no Desktop bloqueia a entrega
  (`target_busy`) e a mensagem se perde — mais um motivo para trabalho não passar por ali.
- **@pm** routine diária no TUPLE.
- **Handoff sintetizado**: cada passagem de bastão é um artefato curto em
  `<projeto>/.hermes/tasks/<KEY>/handoffs/` (contrato, arquivos, CAs, pendências) — nunca o log inteiro.
- Skills: `fluxo-time`, `kanban-tuple`, `git-workflow`, `bmad-story` (globais), `transcricao-crua`
  (só @orquestrador: ASR bruto, marcar incerteza, separar decisão de hipótese) + steering do cliente.
- Chave do TUPLE por projeto (`.hermes/tuple.env`), usada só via `tuple-api`; nada em skill/SOUL/profile.

## 3. TUPLE — fonte da verdade
- Workspace → Projeto → Épicos → Tasks (DoR).
- `BACKLOG → TODO → IN_PROGRESS → IN_REVIEW`; `DONE` só na revisão humana; sem pular coluna.
- Bots agem como o João e marcam `[bot @nome]`.

## 4. Workspace + kiro-cli (cérebro e execução)

> **Onde ficam os projetos:** `$HERMES_PROJETOS` — variável de ambiente do usuário,
> uma pasta por projeto/cliente dentro dela. Não é detectada: numa máquina com
> OneDrive corporativo existem `~/Documents` (vazio de projetos) e
> `~/OneDrive - <Org>/Documentos` (os projetos de verdade), e adivinhar erra calado.
>
> **As notas de call NÃO ficam junto.** `_calls/` mora em `~/Documents`, local e fora
> da sincronização do OneDrive: transcrição de cliente não sai da máquina, que é o
> motivo de transcrever local. Use `HERMES_CALLS` para mudar.
- `$HERMES_PROJETOS/<Projeto>/` (pasta, não repo): `AGENTS.md`, `.hermes/tuple.env` (chave do
  TUPLE do projeto), docs BMAD, `.kiro/` (steering + specs) e os repos clonados.
- Provider **kiro-acp**: cada turno de bot = sessão `kiro-cli acp --agent hermes-<bot>`.
- **kiro-pool**: máx. 4 sessões simultâneas — ⚠️ **não portado para Windows** (depende de `flock`).
  Nesta máquina não há teto de concorrência.
- Loop: FRONT/BACK → TESTES (@qa) → falhou volta ao dev (**circuit breaker: máx. 3 voltas;
  na 3ª falha para, `BLOCKED` + alerta no Telegram + humano decide**) → passou → PR na branch do time
  (`pull --rebase`, sem `--force`) → **GATE 3** (code review humano + merge).
- Pós-merge: deploy/pipeline quando o repo tiver; homologação com o cliente é manual.

## Estado, políticas e auditoria (em código)
- **Task manifest** por tarefa em `<projeto>/.hermes/tasks/<KEY>/` (estado, escopo, `allowed_paths`,
  aprovações, voltas, artefatos, contrato, handoffs estruturados).
- **Máquina de estados** `RECEIVED → TRIAGED → AWAITING_APPROVAL → SPECIFYING → AWAITING_SPEC_APPROVAL →
  SPEC_APPROVED → IMPLEMENTING → TESTING ⇄ CHANGES_REQUESTED → AWAITING_REVIEW → MERGED → DEPLOYED/HOMOLOGATING → CLOSED`
  (+ BLOCKED), fiscalizada pelo `hermes-task`: quem move, evidência exigida, DoD, circuit breaker.
- **Contrato de API** (`contrato.yaml`) antes de front e back em paralelo.
- **Políticas fora do prompt**: toolsets do Hermes, escopo travado após GATE 2 e o `git-bot`
  (recusa `--force`, `--no-verify`, `reset --hard`, push em main e commit de segredo; faz
  `pull --rebase` antes de todo push e devolve BLOCKED em conflito).
- ⚠️ **As permissões dos agentes Kiro NÃO estão sendo aplicadas.** Elas só valem na engine v3,
  e o `acp` do kiro-cli 2.25.0 recusa `--agent` junto com `--agent-engine v3` — as duas são
  mutuamente exclusivas. Em v2 o bloco `permissions` é ignorado **em silêncio**. Verificado com
  agente descartável: regra de negação não bloqueou. Até o Kiro ligar as duas coisas, o que
  segura de fato é o `git-bot`, o `hermes-task`, branch protection no remote e token mínimo.
- **Auditoria**: `audit.jsonl` por projeto + sessões kiro-cli no `kiro-pool`.
- **Branch**: estratégia por projeto no `AGENTS.md` (`por-tarefa` | `compartilhada`).

## Riscos, notas e regras
- ⚠️ Isolamento só por pasta: bots enxergam todos os clientes.
- ⚠️ Push liberado para @dev e @qa → permissões do Kiro + token git mínimo.
- ⚠️ Branch compartilhada com humanos → `pull --rebase` antes de todo push, nunca `--force`.
- 🛡️ Entrada externa só passa pelo @orquestrador; ordem suspeita no texto → não executa e
  vira ⚠️ na proposta do GATE 1; nada é criado antes do `/aprovar`.
- 🛡️ Bots não editam/reatribuem issue de outra pessoa sem OK.
- ℹ️ Host único: se o PC cair o fluxo pausa; nada se perde (TUPLE + git).
- ℹ️ Custo: kiro-cli (empresa) + API da Anthropic para os 3 bots de texto. OpenWhispr, Hermes
  e Telegram são grátis. Credencial no pool do Hermes (`hermes auth add anthropic`), nunca no repo.
- ⚠️ **Todo áudio gravado vira nota em `_calls/`** (local). O @orquestrador só lê depois do
  `/cliente`; call sensível → `/ignorar`. Para nem exportar, desabilite o agendamento
  (`hermes-dev-team - openwhispr-notes` no Windows, `hermes-calls.timer` no Linux) **antes** de gravar.
- ℹ️ Windows: `install-windows.sh` cobre o que o `install.sh` não faz aqui (hermes.cmd,
  HERMES_HOME em `%LOCALAPPDATA%`, wrappers dos scripts Python).
- ℹ️ Gateway: um por máquina (`hermes gateway install`, sem `-p`), serve os 7 profiles. Sobe no
  login e o `gateway-heartbeat` avisa no Telegram se parar — falando direto com a API do
  Telegram, porque o gateway é justamente o que cairia.
- ℹ️ Entrega de routine: use `telegram:<chat_id>`. O alvo genérico `telegram` não resolve
  (o diretório de canais fica vazio) e falha sem alarde.
