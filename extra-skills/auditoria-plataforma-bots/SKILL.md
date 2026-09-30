---
name: auditoria-plataforma-bots
description: Auditar a plataforma de bots — diagrama vs o disco.
version: 1.0.0
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
- **Não edite skill dentro de `profiles/<bot>/skills/`.** O instalador do time faz `rm -rf` + `cp -r`
  a partir do repo em cada execução: a alteração desaparece na próxima instalação. A fonte é o repo
  (`shared-skills/`, `extra-skills/`) — e skill de nome novo, fora dessas listas, sobrevive.
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
- **Divergência entre README, diagrama e disco é achado, não ruído.** Reporte qual dos três está
  errado — o que engana o próximo bot é a doc, não a falta em si.
