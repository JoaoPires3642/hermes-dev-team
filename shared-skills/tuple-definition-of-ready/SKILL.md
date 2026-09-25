---
name: tuple-definition-of-ready
description: Aplique ao redigir, quebrar ou revisar uma issue do TUPLE antes de criá-la. Define o Definition of Ready (contexto de negócio, causa com arquivo:linha, o que NÃO está quebrado, mudança, alternativas descartadas, critérios verificáveis, o teste que precisa falhar, dependências, repo/branch) e a árvore Feature → Story → Task.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [tuple, dor, issue, backlog]
---

# Definition of Ready — issue do TUPLE

> Adaptado do padrão interno `hypesoftlabs/tuple-workspace` (skill `tuple-definition-of-ready`).

Uma issue está pronta quando **alguém que não participou da investigação consegue
pegá-la e começar sem perguntar nada**. Esse é o teste, e o único.

Corpo em markdown, pt-BR acentuado. Lido por humano e por bot.

## Título: formato de commit

`<tipo>(<escopo>): <o que muda, em minúsculas>` — o escopo é o repo/módulo alvo.
Diz **o que muda**, não o que dói. O prefixo é convenção de commit; o campo `type`
da issue é outra coisa (skill `kanban-tuple`).

## As seções

1. **Contexto de negócio** (1º parágrafo, sem título) — o sintoma como o usuário vive:
   quem sente, o que vê, quando. Cole a evidência literal (tela, log, trecho da call).
   Em issue de produto: que decisão fica melhor depois disso?
2. **Causa** — cadeia causal com `arquivo:linha` e o trecho que erra (use o grafo:
   skill `codebase-memory`). Intermitente → explique a corrida. Causa desconhecida →
   a issue é de **investigação** e a entrega é a spec; diga isso.
3. **O que NÃO está quebrado** — delimita o dano; o que já foi verificado intacto.
4. **Mudança** — arquivos e a alteração, com o porquê de cada uma (a decisão, não o diff).
5. **Alternativas descartadas** — qual era e por que perdeu.
6. **Critérios de aceite** — checklist verificável por alguém de fora: o comportamento
   novo acontece · o vizinho não regrediu · o fallback continua. Nada de "funcionar
   corretamente".
7. **Teste** — o teste que **precisa falhar sem o fix**: entrada, saída, onde mora.
8. **Dependências** — o que bloqueia e por quê; crie a relação `BLOCKS` na API.
9. **Repo e branch** — `**Repo:** <repo> · **Branch:** <nome> (a partir de <base>)`.

## Árvore: Feature → Story → Task

| nível | type | o que é | quem pega |
|---|---|---|---|
| Feature | feature | resultado de negócio, guarda-chuva | ninguém direto |
| Story | story | fatia mergeável sozinha, comportamento observável | um dev, se quebrada |
| Task | task | 2h a 8h de trabalho, uma sentada | um dev, direto |

Funcionalidade nova **nunca** nasce como uma issue só. Correção pontual continua
sendo uma issue só. Ligação por `parentId`, criando **pai antes de filho**.

Cada nível carrega só o que é dele: contexto inteiro na feature; a fatia e os CAs
observáveis na story; arquivos, CA e teste da própria task na task. Task de 3h com
"alternativas descartadas" é teatro; task sem CA e sem teste é recado.

**Régua da task: 2h a 8h.** Menos → junte. Mais → quebre. Não dá para quebrar com
honestidade → falta investigação: pare na story e escreva nela:

```markdown
## Quebra em tasks — pendente
Esta story **não** foi quebrada. Quebre antes de começar.
**O que falta saber:** <comportamento não mapeado, integração não verificada, decisão em aberto>
**Como descobrir:** <ler tal módulo, medir tal volume, perguntar a tal pessoa>
```

## Prioridade e estimativa

| priority | quando |
|---|---|
| URGENT | quebrado em produção, sem contorno |
| HIGH | usuário sente todo dia; contorno feio |
| MEDIUM | incomoda, contorno óbvio |
| LOW | dívida, polimento |

`estimate` só na **task**, só na escala do time (padrão fibonacci: dentro da régua
2h–8h os valores são **2, 3, 5, 8** = horas). Feature e story ficam sem estimate.
Chute registrado vira compromisso alheio: só preencha quando souber.

## Antes de criar, releia procurando

- Frase que só faz sentido para quem estava na conversa? Reescreva.
- CA que você não sabe verificar? Não é CA.
- Afirmação sobre código que você não abriu? Abra ou remova.
- Segredo, token, dado de cliente no corpo? Fora — a issue é lida pelo workspace inteiro.
- O título sozinho, na lista do board, diz o que muda?
- Funcionalidade nova virando uma issue só? Falta a árvore.
- Task fora de 2–8h, ou estimate em feature/story?
