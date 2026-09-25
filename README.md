# hermes-dev-team

Time de bots de dev no **Hermes Agent (Bot Mode)**, com o **kiro-cli** como cérebro e
motor de execução. Tudo que é decidido vira issue no **TUPLE** (fonte da verdade).

```
Entradas (Granola MCP · issue no TUPLE · artefatos/PBIs)
  → @orquestrador → GATE 1 (humano) → issues no TUPLE + sala do projeto
  → @po / @techlead → story BMAD (DoR) → GATE 2 (humano) → .kiro/specs
  → @dev-front / @dev-back → @qa (loop até passar) → PR → GATE 3 (humano, merge)
```

Arquitetura completa: [docs/arquitetura.md](docs/arquitetura.md).

## Bots

| Bot | Papel | Pet | Kiro pode |
|---|---|---|---|
| @orquestrador | entradas, resumo, GATE 1, distribui | octopus | ler + curl no TUPLE |
| @po | dor → user story, PRD/épicos | peri-the-owl | ler, escrever `docs/`, curl TUPLE |
| @pm | prazo, cycles, impedimentos (routine diária) | capybara-lulu | ler + curl TUPLE |
| @techlead | story BMAD + DoR, GATE 2, `.kiro/specs` | pipe-wrench-robot | ler, escrever `docs/` e `.kiro/`, git leitura, curl TUPLE |
| @dev-front | implementa front, commit/push, PR | foxlynn | ler, escrever, shell (sem force/reset --hard/--no-verify) |
| @dev-back | implementa back, commit/push, PR | fat-robot | idem |
| @qa | testes + revisão, devolve com evidência | prompt-penguin | idem |

Cada turno de um bot é uma sessão `kiro-cli acp --agent hermes-<bot>`, passando
pelo `kiro-pool` (no máximo 4 sessões ao mesmo tempo).

## Instalar em uma máquina nova

Pré-requisitos: Hermes Agent + Desktop, `git`, `curl`, `jq`, `flock` (util-linux),
`python3` com Pillow (avatares), `kiro-cli` logado na conta da empresa, VPN quando
o remote exigir.

```bash
gh repo clone JoaoPires3642/hermes-dev-team ~/hermes-dev-team
cd ~/hermes-dev-team
./install.sh            # pergunta a TUPLE_API_KEY na 1ª vez (fica em ~/.config/hermes-dev-team/secrets.env)
```

Depois, uma vez por máquina:

1. `kiro-cli login`
2. `hermes -p orquestrador mcp login granola` (OAuth do Granola MCP)
3. Hermes Desktop → Settings → Advanced → **Warm Bot Backends = 7**
4. Telegram do @orquestrador: `hermes -p orquestrador gateway setup`
5. Routines no Desktop (aba Bots → Routines):
   - @orquestrador: a cada 15 min — "buscar notas novas no Granola MCP e issues marcadas no TUPLE"
   - @pm: dias úteis 9h — "resumo do board: IN_PROGRESS parado, BLOCKED, IN_REVIEW"
6. Pasta do cliente: `cp -r templates/cliente ~/clientes/<cliente>` e preencher o `AGENTS.md`
   e o `.kiro/steering/` (arquitetura, segurança — sem segredos).

Atualizar: `git pull && ./install.sh` (memórias e sessões dos bots ficam).

## Estrutura

```
bots/<bot>/          distribuição Hermes de cada bot (gerada — não editar à mão)
souls/<bot>.md       personalidade/regras de cada bot (editar aqui)
scripts/gen_bots.py  gera bots/ e kiro-agents/ (toolsets, pets, permissões)
shared-skills/       fluxo-time · kanban-tuple · git-workflow · bmad-story
kiro-agents/         agentes Kiro por bot (~/.kiro/agents/hermes-<bot>.json)
plugins/model-providers/kiro-acp/   provider Hermes → kiro-cli acp
bin/kiro-pool        limita sessões kiro-cli simultâneas (padrão 4)
templates/cliente/   AGENTS.md, docs/, .kiro/steering/ de um cliente novo
install.sh           instala/atualiza tudo nesta máquina
```

Mudou SOUL, pet, ferramentas ou permissões? Edite `souls/` ou `scripts/gen_bots.py`,
rode `python3 scripts/gen_bots.py`, commite e `./install.sh`.

## Segredos

Nenhum segredo neste repo. `TUPLE_API_KEY` fica em
`~/.config/hermes-dev-team/secrets.env` (chmod 600) e é copiada para o `.env` de
cada profile. Credenciais git vêm do credential helper da máquina.

## Estado (v0.1.0)

- ✅ Profiles, skills, toolsets, pets/avatares, kiro-pool (testado com 6 jobs / 4 vagas).
- ⚠️ **Não testado ponta a ponta**: provider `kiro-acp` (reusa o cliente ACP do
  `copilot-acp` do Hermes) e as regras `permissions` dos agentes Kiro — validar numa
  máquina com `kiro-cli` logado (`hermes -p dev-back chat` e mandar um "oi").
- ⚠️ A API key do TUPLE precisa ter escopo no projeto do cliente (dá 403 fora dele).
