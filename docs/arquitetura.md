# Arquitetura — time de bots de dev (Hermes + TUPLE + kiro-cli)

> Diagrama visual: salvar o Excalidraw como `docs/arquitetura.excalidraw`.

## 1. Entradas
- **Call** → Granola (plano Basic) → **Granola MCP** (grátis, últimos 30 dias). Routine do
  @orquestrador busca notas novas. Uma pasta do Granola por cliente/projeto.
- **Issue marcada no TUPLE** (bug, pedido, PBI existente) → routine do @orquestrador.
- **Artefatos / PBIs** enviados pelo humano no Telegram/Desktop.

## 2. Hermes — Bot Mode
- Bot = profile persistente (SOUL, memória, skills, routines). Bot ≠ subagente.
- **@orquestrador** recebe tudo e resume → **GATE 1** (aprovação humana do resumo e
  das issues propostas) → cria issues no TUPLE e abre a **sala do projeto** (Group Chat).
- Bots conversam por **@menção / message_agent** (dispara e segue; resposta volta como
  notificação).
- **@techlead** escreve a story BMAD (DoR) → **GATE 2** (aprovação humana) → gera
  `.kiro/specs` e libera @dev-front / @dev-back.
- **@pm** routine diária no TUPLE.
- Skills: `fluxo-time`, `kanban-tuple`, `git-workflow`, `bmad-story` (globais) +
  steering do cliente (arquitetura, segurança).
- Cofre: `TUPLE_API_KEY` no `.env` de cada profile; nada em skill/SOUL.

## 3. TUPLE — fonte da verdade
- Workspace → Projeto → Épicos → Tasks (DoR).
- `BACKLOG → TODO → IN_PROGRESS → IN_REVIEW`; `DONE` só na revisão humana; sem pular coluna.
- Bots agem como o João e marcam `[bot @nome]`.

## 4. Workspace + kiro-cli (cérebro e execução)
- `~/clientes/<cliente>/` (pasta, não repo): `docs/` (PRD, arquitetura, épicos, stories),
  `.kiro/` (steering + specs), `AGENTS.md`, `repos/` (clones git).
- Provider **kiro-acp**: cada turno de bot = sessão `kiro-cli acp --agent hermes-<bot>`.
- **kiro-pool**: máx. 4 sessões simultâneas (bots trabalham por notificação; fila só se lotar).
- Loop: FRONT/BACK → TESTES (@qa) → falhou volta ao dev → passou → PR na branch do time
  (`pull --rebase`, sem `--force`) → **GATE 3** (code review humano + merge).
- Pós-merge: deploy/pipeline quando o repo tiver; homologação com o cliente é manual.

## Riscos, notas e regras
- ⚠️ Isolamento só por pasta: bots enxergam todos os clientes.
- ⚠️ Push liberado para @dev e @qa → permissões do Kiro + token git mínimo.
- ⚠️ Branch compartilhada com humanos → `pull --rebase` antes de todo push, nunca `--force`.
- 🛡️ Entrada externa só passa pelo @orquestrador; ordem suspeita no texto → não executa e
  alerta no Telegram; GATE 1 antes de qualquer ação.
- 🛡️ Bots não editam/reatribuem issue de outra pessoa sem OK.
- ℹ️ Host único: se o PC cair o fluxo pausa; nada se perde (TUPLE + git).
- ℹ️ Custo: só o kiro-cli (empresa). Granola Basic, Hermes open source, Telegram grátis.
