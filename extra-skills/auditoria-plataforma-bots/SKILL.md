---
name: auditoria-plataforma-bots
description: Auditar a plataforma de bots — diagrama vs o disco.
version: 1.2.0
author: Hermes Orquestrador
metadata:
  hermes:
    tags: [auditoria, plataforma, bots, diagnostico]
---

# Auditoria da plataforma do time de bots

Aplique quando a pergunta for "falta algo nessa arquitetura?", "isso está implementado?" ou
"dê uma olhada nesse diagrama" — a plataforma sendo Hermes (Bot Mode) + kiro-cli + TUPLE.
A resposta não sai do documento: sai do disco.

**Regra de ouro: diagrama e `docs/` são intenção; o que vale é o arquivo que sustenta a caixa.**
Só afirme que uma parte funciona depois de ver o que a prova. Um desenho honesto já anota
alguns furos conhecidos — e é justamente aí que ele passa confiança demais sobre o resto.

## Ordem da auditoria

Varra tudo isto **antes** de escrever o relatório (as leituras são independentes: peça em paralelo).

| Confira | Onde | O que a ausência significa |
|---|---|---|
| chave `hermes-bots` | `profiles/<bot>/profile.yaml` | sem ela o Hermes não injeta `message_agent` nesse bot: ele **não pode ser chamado por @menção**, e todo handoff do desenho para |
| `model.provider` + `platform_toolsets` | `profiles/<bot>/config.yaml` | provider próprio (ex. `anthropic`) **sem `terminal`** = o bot não roda helper nenhum; quem dava shell era o Kiro |
| `allowedTools` vs `tools` | `~/.kiro/agents/hermes-<bot>.json` | ferramenta listada em `tools` e fora de `allowedTools` pede **aprovação interativa**; em sessão ACP ninguém atende e o turno trava |
| quais helpers do time existem | `~/.local/bin` | o instalador do Windows só cria wrapper para os helpers em **Python**; os de bash ficam de fora mesmo constando no README |
| `platforms` + `served_profiles` | `gateway_state.json` | só o profile com canal conectado recebe alerta; alerta de bot sem canal **não chega a lugar nenhum** |
| diretório de canais vazio | `channel_directory.json` | alvo genérico (`telegram`) não resolve e **falha sem alarde** — entrega sempre como `telegram:<chat_id>` |
| `schedule` · `prompt` · `deliver` | `profiles/<bot>/cron/jobs.json` | routine "por evento" tem cron deliberadamente distante: quem acorda o bot é o exportador, não o horário |
| quantos projetos reais existem | `~/Documents/*/AGENTS.md` | sem projeto não há `.hermes/tuple.env`, `tasks/` nem `audit.jsonl` — o bloco de workspace é molde, não instância |
| nome real das subpastas + log do exportador | pasta de notas de call | doc e disco divergem em nome e em qual exportador roda; confie no disco |
| helper é **obrigatório** ou só disponível? | `bin/*`, agentes Kiro | política que o bot pode escolher não chamar não é política aplicada — diga isso explicitamente |

Depois compare com o que o código realmente implementa (ex.: ler o `hermes-task` e confirmar
máquina de estados, DoD, `allowed_paths`, circuit breaker). **Separe "não implementado" de
"implementado e verificado"**: nomeie o que você leu e confirmou, senão o humano refaz a checagem.

## Como reportar

1. **Contexto** curto: o que o desenho propõe, o que já está certo, quantos furos ele mesmo admite.
2. **Tabela de lacunas** — `# · gap · gravidade · evidência`. Gravidade: 🔴 bloqueia · 🟠 alta ·
   🟡 média · 🔵 baixa. Evidência é **caminho de arquivo**, não impressão.
3. **Caminho crítico em uma frase**: quais lacunas, juntas, impedem o fluxo principal de sair do
   papel. É a única linha que o humano precisa ler para decidir.
4. **Árvore de issues** Feature → Story → Task com estimativa só em task e **soma por story e total**
   (skill `tuple-definition-of-ready`).
5. **Dúvidas que só o humano responde** — em especial as decisões de design que a auditoria expõe.
6. **GATE 1** por último.

## Reiniciar o gateway depois de mudar config em disco

Config nova em `profiles/<bot>/config.yaml` **só passa a valer depois do restart** — o processo
no ar continua com o que leu ao subir. O gateway é um multiplexer único, do profile `default`,
e a sessão do bot roda **dentro** desse PID.

O bot consegue reiniciá-lo. Duas condições, e é a segunda que engana:

1. **Aponte `HERMES_HOME` para a raiz do Hermes**, não para o profile. Restart escopado ao
   profile do bot responde `not confirmed: host operation is still pending` e o PID não muda —
   é pedido errado, não falta de permissão. `HERMES_HOME=<root> hermes gateway status` deve
   mostrar o PID host antes de você mandar o `restart`.
2. **Derrubar o gateway mata o próprio turno**, e a resposta ao humano nunca é entregue. Rode
   o restart por um script desanexado (`setsid nohup`), com atraso de ~20s para a sua mensagem
   sair primeiro, e faça o script gravar `pid` + `start_time` **antes e depois** em um log fora
   do scratch do profile.

A prova de que reiniciou é `start_time` novo no `gateway_state.json` — não o `exit 0` do
comando, e não o log do lançador.

## Aprendeu algo auditando? Espelhe a skill no repo ANTES de terminar o turno

Numa sessão de bot o `skill_manage` escreve em `profiles/<bot>/skills/` — não há como
editar a skill em outro lugar. E o instalador do time faz `rm -rf` + `cp -r` de
`shared-skills/`/`extra-skills/` a cada execução: **a edição que fica só no profile morre
na próxima instalação.** Não é opcional e não é tarefa do humano lembrar; faz parte do
mesmo turno em que você patcheia.

1. Ache o lado do repo: a skill mora em `shared-skills/<nome>/` (todos os bots) ou
   `extra-skills/<nome>/` (só quem lista em `bots/<bot>/extra-skills.txt`).
2. Copie **normalizando para LF**: arquivo escrito no profile sai com CRLF e o
   `.gitattributes` do repo força `eol=lf` — CRLF ali quebra os scripts do próprio repo.
   `tr -d '\r' < "$PROFILE/<nome>/SKILL.md" > "extra-skills/<nome>/SKILL.md"`
3. **Suba a `version:` do frontmatter** nos dois lados, senão ninguém vê que mudou.
4. Commite e faça push. O repo da plataforma **não é repo de cliente**: não tem `AGENTS.md`
   nem KEY, então `git-bot commit --key` (que exige `Refs: <KEY>`) não se aplica — vai `git`
   direto. Continuam valendo: **nenhuma marca de bot na mensagem**, identidade **local**
   (nunca `--global`), e `main` só com autorização explícita do humano naquele pedido.
   - **E-mail ditado pelo humano: confira contra `git log -3 --format="%an <%ae>"`** antes de
     commitar. Um dígito trocado passa sem erro, fica no histórico para sempre e o commit não
     vincula à conta dele. Divergiu → confirme qual vale, citando os dois.
   - **Mensagem longa vai por `git commit -F <arquivo>`**, nunca por heredoc: o
     `approvals.deny` casa substring do comando **inteiro**, então o nome de um helper citado
     no corpo bloqueia o próprio commit. Tire o texto do comando em vez de reescrever a
     mensagem para escapar do filtro.
5. Confirme por `diff` que repo e profile são iguais, comparando sem CR — e liste os arquivos
   dos dois lados (`search_files` com `target='files'`) para achar referência que existe só
   no profile.

Mesma regra para os arquivos de apoio (`references/`, `scripts/`), que é o que mais
escapa: o `SKILL.md` você lembra, a referência nova não.

## Armadilhas

- **Quando a própria lacuna impede criar issue, diga as duas razões** (falta o OK do GATE 1 **e**
  a criação é tecnicamente impossível hoje) e proponha a ordem de desbloqueio. Prometer criação
  que vai falhar é pior que não prometer.
- **Lacuna que expõe contradição de design não se resolve sozinha: vira pergunta.** Quando o
  desenho exige do bot algo que a config dele proíbe, ofereça as saídas e deixe o humano escolher —
  não escolha por ele e não "conserte" a config no meio da auditoria.
- **Antes de reportar segredo exposto em arquivo, confirme com uma busca por padrão.** A leitura de
  arquivo mascara trechos que parecem credencial (um `Bearer %s` legítimo aparece mascarado), e
  você reportaria um bug que não existe.
- **Skill editada numa sessão de bot vive no profile e o instalador a apaga.** A fonte é o repo
  (`shared-skills/`, `extra-skills/`); espelhe no mesmo turno, pela seção acima. Skill de nome
  novo, fora dessas duas árvores, é a única que sobrevive sem espelhamento — e mesmo assim não
  chega aos outros bots.
- **Não registre como pendência o que é escolha do humano.** Nota sem cliente, projeto ainda não
  criado e chave de API ausente são decisões dele, não bug da plataforma: entram como dúvida.
- **Helper que existe pode ainda assim falhar em toda chamada.** Antes de marcar um helper como
  presente, **rode o subcomando mais barato dele** (`states`, `--help`) e confira `exit 0`: no host
  Windows um wrapper que passa path MSYS (`/c/...`) a um interpretador nativo morre em todos os
  projetos de uma vez. Detalhe e conserto na skill `onboarding-projeto-plataforma`, referência
  sobre a fronteira MSYS ↔ nativo. "Existe no PATH" não é evidência de que funciona.
- **Auditoria de UMA pasta de projeto tem skill própria.** Se a pergunta é sobre os arquivos de um
  projeto (`AGENTS.md`, `tuple.env`, `steering`, `tasks`), use `onboarding-projeto-plataforma`;
  esta skill é para a plataforma (profiles, gateway, cron, helpers).
- **Rodar o instalador da plataforma de dentro de uma sessão de bot envenena os caminhos.** O
  Hermes exporta `HERMES_HOME=<root>/profiles/<bot>`, então o script escreve o `.env` do time
  dentro do profile do bot e procura `<profile>/profiles/<bot>`. Suba para a pasta acima de
  `profiles/` **e exporte** `HERMES_HOME`, senão o `hermes` filho herda o do bot.
- **Instalador com `set -e` que termina sem a linha final de sucesso FALHOU.** Ele aborta no
  meio deixando na tela um `==> Bot @<nome>` que parece progresso. Confira o `exit` **e** a
  última linha; depois confira `profiles/<bot>/config.yaml` em disco, que é a única prova de
  que a mudança chegou. Instalador que "rodou" sem trocar arquivo nenhum é o sintoma padrão
  de uma travessia MSYS → nativo errada: detalhe e conserto na skill
  `onboarding-projeto-plataforma`, referência sobre a fronteira MSYS ↔ nativo.
- **Antes de declarar um comando proibido, leia os padrões de `approvals.deny` do profile.**
  Eles casam **substring do comando literal**, não intenção: um deny de `*hermes -p *` não
  proíbe `hermes gateway`, e um deny qualquer dispara se a palavra aparecer dentro de um
  argumento citado (mensagem de commit, texto de `-q`). Quando o texto é que colide, passe-o
  por arquivo (`git commit -F <arquivo>`) em vez de reescrever o texto para escapar do filtro.
  Dizer "não tenho permissão" sem conferir a lista é a pior resposta possível: o humano sabe
  que dá e você perde a rodada.
- **`Background process started` não é prova de que o comando rodou.** Com `setsid nohup ...
  >/dev/null 2>&1` o retorno é só o shell subindo: caminho errado, arquivo ausente e erro de
  sintaxe somem junto com a saída. Dispare com `test -f "$script" && ...`, faça o próprio
  script logar em arquivo, e confirme pelo **efeito** (o estado que devia mudar), nunca pela
  mensagem do lançador.
- **Divergência entre README, diagrama e disco é achado, não ruído.** Reporte qual dos três está
  errado — o que engana o próximo bot é a doc, não a falta em si.
