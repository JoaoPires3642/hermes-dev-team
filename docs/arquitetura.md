# Arquitetura — time de bots de dev (Hermes + TUPLE + kiro-cli)

> Diagrama visual: salvar o Excalidraw como `docs/arquitetura.excalidraw`.

## 1. Entradas
- **Call** → **Meetily** (open source, MIT, transcrição 100% local com Whisper) → `meetily-notes`
  lê o SQLite dela e exporta uma nota Markdown por call em `~/Documentos/_calls/<cliente>/`.
  Routine do @orquestrador roda o exportador e lê as notas novas. O cliente/projeto vem do
  título da call, por convenção `[Cliente] Assunto`; sem prefixo a nota cai em `_sem-cliente/`
  e o bot pergunta.
  > Saímos do Granola MCP: o MCP dele é pago. A Meetily não tem API nem MCP oficial e o export
  > de Markdown é feature PRO, então `meetily-notes` lê o SQLite local direto — o que é rápido
  > e gratuito, mas **não é contrato público**: uma mudança de schema dela quebra a ponte.
  > O schema esperado está documentado no cabeçalho do `bin/meetily-notes`.
- **Issue marcada no TUPLE** (bug, pedido, PBI existente) → routine do @orquestrador.
- **Artefatos / PBIs** enviados pelo humano no Telegram/Desktop.

## 2. Hermes — Bot Mode
- Bot = profile persistente (SOUL, memória, skills, routines). Bot ≠ subagente.
- **@orquestrador** recebe tudo e resume → **GATE 1** (aprovação humana do resumo e
  das issues propostas) → cria issues no TUPLE e chama os bots por @menção.
- Bots conversam por **@menção / message_agent** (dispara e segue; resposta volta como
  notificação). **Sem sala obrigatória**: o registro fica nos comentários da issue no
  TUPLE; Group Chat no Desktop é opcional, só para o humano acompanhar.
- **@techlead** escreve a story BMAD (DoR) → **GATE 2** (aprovação humana) → gera
  `.kiro/specs` e libera @dev-front / @dev-back.
- **@pm** routine diária no TUPLE.
- **Handoff sintetizado**: cada passagem de bastão é um artefato curto em
  `<projeto>/.hermes/handoffs/<KEY>/` (contrato, arquivos, CAs, pendências) — nunca o log inteiro.
- Skills: `fluxo-time`, `kanban-tuple`, `git-workflow`, `bmad-story` (globais) +
  steering do cliente (arquitetura, segurança).
- Chave do TUPLE por projeto (`.hermes/tuple.env`), usada só via `tuple-api`; nada em skill/SOUL/profile.

## 3. TUPLE — fonte da verdade
- Workspace → Projeto → Épicos → Tasks (DoR).
- `BACKLOG → TODO → IN_PROGRESS → IN_REVIEW`; `DONE` só na revisão humana; sem pular coluna.
- Bots agem como o João e marcam `[bot @nome]`.

## 4. Workspace + kiro-cli (cérebro e execução)
- `~/Documentos/<Projeto>/` (pasta, não repo): `AGENTS.md`, `.hermes/tuple.env` (chave do
  TUPLE do projeto), docs BMAD, `.kiro/` (steering + specs) e os repos clonados.
- Provider **kiro-acp**: cada turno de bot = sessão `kiro-cli acp --agent hermes-<bot>`.
- **kiro-pool**: máx. 4 sessões simultâneas (bots trabalham por notificação; fila só se lotar).
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
- **Políticas fora do prompt**: permissões dos agentes Kiro (sem deploy, sem push em main, sem fingir humano),
  toolsets do Hermes, escopo travado após GATE 2.
- **Auditoria**: `audit.jsonl` por projeto + sessões kiro-cli no `kiro-pool`.
- **Branch**: estratégia por projeto no `AGENTS.md` (`por-tarefa` | `compartilhada`).

## Riscos, notas e regras
- ⚠️ Isolamento só por pasta: bots enxergam todos os clientes.
- ⚠️ Push liberado para @dev e @qa → permissões do Kiro + token git mínimo.
- ⚠️ Branch compartilhada com humanos → `pull --rebase` antes de todo push, nunca `--force`.
- 🛡️ Entrada externa só passa pelo @orquestrador; ordem suspeita no texto → não executa e
  alerta no Telegram; GATE 1 antes de qualquer ação.
- 🛡️ Bots não editam/reatribuem issue de outra pessoa sem OK.
- ℹ️ Host único: se o PC cair o fluxo pausa; nada se perde (TUPLE + git).
- ℹ️ Custo: só o kiro-cli (empresa). Meetily Community, Hermes e Telegram são grátis.
- ⚠️ Meetily: o pacote Windows exige CPU x64 com AVX2. Diarização de quem falou é PRO.
