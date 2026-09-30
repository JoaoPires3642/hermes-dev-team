---
name: token-economy
description: Aplique sempre. Reduz custo e latência de cada turno — leitura dirigida, edição incremental, chamadas em paralelo, resposta enxuta — e reconhece quando o trabalho nem deveria ter começado. Audiência - todos os bots.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [custo, contexto, eficiencia]
---

# Economia de token

Cada turno de bot é uma sessão de modelo paga. O que custa caro não é pensar: é
**ler o que não precisava** e **acordar sem ter o que fazer**.

## Não comece o que não é seu

Antes de qualquer leitura, confira se a tarefa é sua e se há algo novo:

- [ ] Fila vazia, board sem pendência, nada mudou → responda `[SILENT]` e **pare**.
      Um turno que não produz nada custa igual a um que produz.
- [ ] A tarefa é de outro papel? Passe adiante (`hermes-delegar`, skill `fluxo-time`) em vez de "ajudar".
- [ ] Já processou isso? O que diz o que é novo é o handoff da rodada ou o manifest
      (`hermes-task show`) — não a sua memória do turno anterior.

## Leitura

- **Localize antes de ler.** `grep`/`find` para achar o trecho; `read` com faixa
  de linhas quando souber a região. Nunca leia arquivo grande "para explorar".
- **Não releia** um arquivo logo depois de editá-lo só para conferir. A escrita
  falha se não aplicou — se não falhou, aplicou.
- Transcrição de call é longa: leia **só as notas listadas na fila**, nunca a
  pasta inteira.

## Edição

- Prefira edição pontual a reescrever o arquivo inteiro.
- Substituição global (`replace_all`) para renome amplo, em vez de N edições.

## Chamadas

- Chamadas independentes vão **na mesma mensagem**, em paralelo. Em série, você
  paga o contexto inteiro a cada ida e volta.
- Busca ampla e exploratória: delegue a um sub-agente, para não encher o seu
  contexto com o que foi descartado.

## Resposta

- Uma frase por atualização relevante. Sem narrar o plano antes de agir — além
  de custar, na sessão ACP o turno costuma **encerrar no primeiro texto**, e o
  trabalho não acontece.
- Não repita o que o diff, a tabela ou o comando já mostram.
- GATE: resumo curto + o que precisa de decisão. O humano não quer o log.

## Antifuncionamento

- Ler a pasta `_calls/` inteira quando a fila apontava uma nota.
- Reler arquivo recém-editado "para garantir".
- Reescrever arquivo inteiro onde uma linha mudaria.
- Chamadas independentes uma por mensagem.
- Narrar "vou fazer X, depois Y" antes de fazer.
- Reprocessar o que já foi triado porque não consultou o controle.
