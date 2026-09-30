---
name: onboarding-projeto-plataforma
description: Habilitar uma pasta de projeto na plataforma de bots.
version: 1.1.0
author: Hermes Orquestrador
metadata:
  hermes:
    tags: [onboarding, projeto, plataforma, config, agents-md]
---

# Trazer um projeto para a plataforma do time de bots

## When to Use

Aplique quando o pedido for "configurar o projeto X", "começar a config do zero", "falta algo
nessa pasta?", "olha o repo Y" — o alvo sendo uma **pasta de projeto** específica e os arquivos
que a plataforma exige dela (`AGENTS.md`, `.hermes/tuple.env`, `.kiro/steering/`, `memory/`,
`docs/`, `.hermes/tasks/`).

Não aplique para a plataforma inteira (profiles, gateway, cron, helpers) — essa é
`auditoria-plataforma-bots`.

**Regra de ouro: maturidade de código não implica maturidade de processo.** Um projeto pode ter
repos com commit de ontem, board com dezenas de issues e skills locais boas, e ainda assim ser
invisível para a plataforma — porque o que habilita a ferramentaria é um arquivo, não o histórico.
Inventarie o disco antes de afirmar o que falta.

## Ordem

### 1. Localize a pasta e o padrão de referência

`$HERMES_PROJETOS` pode **não** ser `~/Documents` — leia a variável em vez de supor, e liste
`"$HERMES_PROJETOS"/*/AGENTS.md` para ver quais pastas a plataforma já reconhece. A pasta que
**tem** `AGENTS.md` é o seu molde: leia-a inteira e compare campo a campo com a que você vai
configurar. Não invente seções — copie a forma que já funciona.

### 2. Inventarie antes de escrever (leituras em paralelo)

| Confira | O que a ausência quebra |
|---|---|
| `AGENTS.md` na raiz | **keystone**: os helpers do time recusam a pasta ("não parece uma pasta de projeto") — sem ele nenhum bot opera o board dali |
| `.hermes/tuple.env` | chave da API; confira só os **nomes** das variáveis (`grep -o '^[A-Z_]*'`), nunca o valor |
| `.kiro/steering/` | sessões kiro-cli sobem sem as regras do cliente |
| `memory/` | nada que o projeto aprendeu sobrevive ao turno |
| `.hermes/tasks/` + `audit.jsonl` | `hermes-task` nunca rodou: **nenhuma tarefa tem estado e nenhum GATE tem registro**, mesmo com o board cheio |
| `docs/` (BMAD) | stories existem só no board, sem fonte versionável |
| scripts soltos em `.hermes/` (`create_*.js`) | sinal de que o board foi construído **fora** do fluxo; trate como achado, não como ferramenta a reusar |
| repos: branch, remote, último commit | o `AGENTS.md` precisa refletir o que o disco diz, não o que o kickoff combinou |

Colete os fatos dos repos por comando (`git -C <repo> rev-parse --abbrev-ref HEAD`,
`config --get remote.origin.url`, `log -1`, scripts do `package.json`, `<TargetFramework>`).
**Campo de `AGENTS.md` preenchido por suposição quebra calado** — quem lê depois confia nele.

### 3. Clarifique o escopo ANTES de escrever qualquer arquivo

"Começar do zero" tem leitura aditiva e leitura destrutiva. Quando o pedido admite as duas,
**pergunte antes de agir, com a opção conservadora primeira** — e enumere explicitamente o que
fica intacto (board, repos). Board e repositório são trabalho de humanos: recriá-los por
interpretação generosa de "do zero" é dano irreversível.

Pergunte junto o que não é descobrível: onde mora a doc (local × máquina de outro time),
estratégia de branch quando kickoff e disco divergem, prefixo do cliente nas notas de call.

### 4. Reporte e peça o GATE 1

Contexto curto · achados 🔴 antes da proposta · árvore Feature → Story → Task com estimativa só
em task e **soma por story e total** (`tuple-definition-of-ready`) · dúvidas · nota de segurança.
Nada é criado no board antes do OK.

## Armadilhas

- **Distinga ferramentaria sua de ação no projeto.** Consertar um wrapper em `~/.local/bin` que
  impede o seu próprio fluxo é manutenção da sua caixa de ferramentas: conserte, **valide rodando**
  e relate no GATE como já feito. Criar issue, alterar board ou tocar repo é ação externa e espera
  o OK. Confundir os dois trava a sessão ou atropela o humano.
- **"Não é versionado" não significa "não é sincronizado".** Antes de aceitar segredo em arquivo
  porque a pasta está fora do git, confira se algum ancestral do caminho é raiz de sync
  (OneDrive, Dropbox, Drive): se for, o segredo está em claro na nuvem corporativa. Reporte como
  🔴 e proponha variável de ambiente — a justificativa escrita no próprio arquivo é a que engana.
- **Segredo redundante é o mais fácil de remover.** Se os repos já autenticam por
  `credential.helper`, o PAT anotado em skill não está nem sendo usado — diga isso, porque muda a
  decisão do humano de "onde guardo" para "posso apagar".
- **Valor com espaço em arquivo sourceado precisa de aspas.** `FOO=Seller Center` sem quotes vira
  `Center: command not found` no `. arquivo` e derruba a carga das variáveis seguintes.
- **Um helper lê o arquivo que ele documenta, não o que parece óbvio.** IDs num `tuple-ids.env`
  paralelo são invisíveis para quem lê `tuple.env`: consolide no arquivo que o helper abre, e só
  guarde o que não é descobrível por API.
- **Não registre como pendência o que é escolha do humano** (branch, onde mora a doc, prefixo de
  call): vira dúvida no GATE, não item da tabela de lacunas.
- Detalhe do ambiente Windows (fronteira MSYS ↔ nativo, e como ler o board antes de o helper
  funcionar): `references/windows-msys-nativo.md` · script pronto: `scripts/board-resumo.sh`.
