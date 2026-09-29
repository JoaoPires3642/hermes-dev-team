# hermes-dev-team

Time de bots de dev no **Hermes Agent (Bot Mode)**, com o **kiro-cli** como cérebro e
motor de execução. Tudo que é decidido vira issue no **TUPLE** (fonte da verdade).

```
Entradas (nota de call da Meetily · issue no TUPLE · artefatos/PBIs)
  → @orquestrador → GATE 1 (humano) → issues no TUPLE + sala do projeto
  → @po / @techlead → story BMAD (DoR) → GATE 2 (humano) → .kiro/specs
  → @dev-front / @dev-back → @qa (loop até passar) → PR → GATE 3 (humano, merge)
```

Arquitetura completa: [docs/arquitetura.md](docs/arquitetura.md).

## Bots

| Bot | Papel | Pet | Kiro pode |
|---|---|---|---|
| @orquestrador | entradas, resumo, GATE 1, distribui | octopus | ler + tuple-api |
| @po | dor → user story, PRD/épicos | peri-the-owl | ler, escrever `docs/`, tuple-api |
| @pm | prazo, cycles, impedimentos (routine diária) | capybara-lulu | ler + tuple-api |
| @techlead | story BMAD + DoR, GATE 2, `.kiro/specs` | pipe-wrench-robot | ler, escrever `docs/` e `.kiro/`, git leitura, tuple-api |
| @dev-front | implementa front, confere a tela no navegador, commit/push, PR | foxlynn | ler, escrever, shell (sem force/reset --hard/--no-verify) |
| @dev-back | implementa back, commit/push, PR | fat-robot | idem |
| @qa | testes + E2E no navegador + revisão, devolve com evidência | prompt-penguin | idem |

@dev-front e @qa têm o toolset `browser` do Hermes (driver **browser-use**, Chromium
empacotado do Hermes, `cloud_provider: local` — sem custo, nunca o Chrome pessoal).

Cada turno de um bot é uma sessão `kiro-cli acp --agent hermes-<bot>`, passando
pelo `kiro-pool` (no máximo 4 sessões ao mesmo tempo).

## Instalar em uma máquina nova

Pré-requisitos: Hermes Agent + Desktop, `git`, `curl`, `jq`, `flock` (util-linux),
`python3` com Pillow (avatares), `kiro-cli` logado na conta da empresa, VPN quando
o remote exigir, e o [codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp)
(só o binário, **sem** configurar agentes):
`curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config`

```bash
gh repo clone JoaoPires3642/hermes-dev-team ~/hermes-dev-team
cd ~/hermes-dev-team
./install.sh
```

Depois, uma vez por máquina:

1. `kiro-cli login`
2. Instalar a [Meetily](https://github.com/Zackriya-Solutions/meetily) (MIT, local) e gravar
   as calls com o título no formato `[Cliente] Assunto` — é daí que sai o cliente/projeto
3. Hermes Desktop → Settings → Advanced → **Warm Bot Backends = 7**
4. Telegram — são **dois** passos, e o segundo é o que costuma faltar:
   - `hermes -p orquestrador gateway setup` — interativo, pede o token do @BotFather
   - `hermes gateway install` — instala o gateway do **host** (no profile `default`,
     sem `-p`). É **um gateway por máquina**, que serve os 7 bots; instalar por profile
     é recusado para não colocar dois pollers no mesmo token.
   - conferir: `hermes gateway status`
5. Routines no Desktop (aba Bots → Routines):
   - @orquestrador: a cada 15 min — "rodar `meetily-notes novas` e ler as notas novas em
     ~/Documentos/_calls/, mais as issues marcadas no TUPLE"
   - @pm: dias úteis 9h — "resumo do board: IN_PROGRESS parado, BLOCKED, IN_REVIEW"
6. Projeto novo: `cp -r templates/projeto ~/Documentos/<Projeto>` (os repos ficam dentro) e preencher:
   - `AGENTS.md` — IDs do TUPLE, repos, branches, restrições (sem segredos)
   - `.kiro/steering/` — arquitetura, segurança, padrões
   - `.hermes/tuple.env` — API key do TUPLE **deste projeto** (`chmod 600`)

Atualizar: `git pull && ./install.sh` (memórias e sessões dos bots ficam).

## Estrutura

```
bots/<bot>/          distribuição Hermes de cada bot (gerada — não editar à mão)
souls/<bot>.md       personalidade/regras de cada bot (editar aqui)
scripts/gen_bots.py  gera bots/ e kiro-agents/ (toolsets, pets, permissões)
shared-skills/       fluxo-time · estado-tarefa · kanban-tuple · tuple-definition-of-ready · git-workflow · bmad-story
                     token-economy · skill-authoring (todos os bots)
extra-skills/        karpathy-guidelines (MIT) + codebase-memory — @techlead, @dev-*, @qa · revisao-codigo — @qa
kiro-agents/         agentes Kiro por bot (~/.kiro/agents/hermes-<bot>.json)
plugins/model-providers/kiro-acp/   provider Hermes → kiro-cli acp
bin/kiro-pool        limita sessões kiro-cli simultâneas (padrão 4)
bin/tuple-api        chama o TUPLE com a chave do projeto (+ audit)
bin/hermes-task      manifest + máquina de estados + DoD + circuit breaker (regras em código)
bin/meetily-notes    exporta as calls da Meetily (SQLite local) como Markdown por cliente
bin/git-bot          git do time com as regras em código (sem force, rebase antes do push)
templates/projeto/   AGENTS.md, docs/, memory/, .kiro/steering/, .hermes/tuple.env.example de um projeto novo
install.sh           instala/atualiza tudo nesta máquina
```

Mudou SOUL, pet, ferramentas ou permissões? Edite `souls/` ou `scripts/gen_bots.py`,
rode `python3 scripts/gen_bots.py`, commite e `./install.sh`.

## Regras que ficam em código (não no prompt)

| Regra | Onde é aplicada |
|---|---|
| estado da tarefa, quem move, evidência, DoD, circuit breaker (3 voltas), escopo travado após a spec | `hermes-task` |
| arquivos só dentro de `allowed_paths` | `hermes-task` (confere no git antes do DoD) |
| bot não finge aprovação humana, não faz deploy nem push em main/master, sem force | permissões dos agentes Kiro (`kiro-agents/`) |
| ferramentas por bot | `platform_toolsets` do Hermes |
| máx. 4 sessões Kiro | `kiro-pool` |
| chave do TUPLE nunca exposta | `tuple-api` |

Auditoria automática: `<projeto>/.hermes/audit.jsonl` (transições, negações, chamadas ao
TUPLE) e `~/.hermes/dev-team-audit.jsonl` (sessões kiro-cli: bot, vaga, duração, saída).

## Segredos

Nenhum segredo neste repo nem nos profiles dos bots. **Cada projeto tem a sua API key
do TUPLE**, em `~/Documentos/<Projeto>/.hermes/tuple.env` (chmod 600). Os bots só
chamam a API pelo `tuple-api <pasta-do-projeto> get|post <procedure> '<json>'`, que lê
a chave do projeto sem expô-la. Credenciais git vêm do credential helper da máquina.

## Estado (v0.1.0)

- ✅ Profiles, skills, toolsets, pets/avatares, kiro-pool (testado com 6 jobs / 4 vagas).
- ⚠️ **Não testado ponta a ponta**: provider `kiro-acp` (reusa o cliente ACP do
  `copilot-acp` do Hermes) e as regras `permissions` dos agentes Kiro — validar numa
  máquina com `kiro-cli` logado (`hermes -p dev-back chat` e mandar um "oi").
- ⚠️ A API key do TUPLE de cada projeto precisa ter escopo naquele projeto (dá 403 fora dele).

## Referências de padrão

DoR, armadilhas da API do TUPLE, formato de revisão e `memory/` por projeto foram
adaptados do `hypesoftlabs/tuple-workspace` (interno Hypesoft). O `tuple-runner-js`
**não** é usado por enquanto.
