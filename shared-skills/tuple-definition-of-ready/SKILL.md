---
name: tuple-definition-of-ready
description: Aplique ao redigir, quebrar ou revisar uma issue do TUPLE antes de criá-la. Define o corpo em quatro seções (Contexto, Escopo, Critérios de aceite, Observações), o título em formato de commit e a árvore Feature → Story → Task.
version: 1.1.0
author: Joao Pires
metadata:
  hermes:
    tags: [tuple, dor, issue, backlog]
---

# Definition of Ready — issue do TUPLE

Uma issue está pronta quando **alguém que não participou da conversa consegue pegá-la e
começar sem perguntar nada**. Esse é o teste, e o único.

A issue é lida por **pessoas** no board — o dono, quem revisa, quem planeja a sprint.
Ela diz *o que o usuário passa a poder fazer*, curta e em linguagem de negócio. A parte
técnica (causa com `arquivo:linha`, arquivos a mexer, alternativas descartadas) mora na
**story BMAD** em `docs/` (skill `bmad-story`), que é o documento completo; a issue é a
peça de trabalho. Despejar a story inteira na issue faz ninguém ler nenhuma das duas.

Corpo em markdown, pt-BR acentuado.

## Título: formato de commit

`<tipo>(<escopo>): <o que muda, em minúsculas>` — o escopo é o repo/módulo alvo.
Diz **o que muda**, não o que dói. O prefixo é convenção de commit; o campo `type`
da issue é outra coisa (skill `kanban-tuple`).

## O corpo: quatro seções, nesta ordem

```markdown
## Contexto

<1 a 3 frases: quem sente o problema, o que acontece hoje, por que importa.>

## Escopo

- <o que será entregue, em verbo no infinitivo: Buscar…, Avisar…, Levar…>

## Critérios de aceite

- <uma frase por critério, observável por quem não escreveu o código>

## Observações

<origem, dependências, repo/branch, o que ficou em aberto — o que não cabe nas outras três>
```

**Contexto** — o sintoma como o usuário vive, sem código nem nome de arquivo. Mostre a
dor com o fato concreto: *"O analista confere na mão se a pessoa já esteve em ouvidoria
procedente. O sistema conta qualquer caso anterior com o mesmo CPF, sem dizer qual."* Em
issue de produto: que decisão fica melhor depois disso?

**Escopo** — a lista do que muda, no nível do comportamento, não dos arquivos. Cada item
é algo que o usuário ou o relatório passa a ter. Se a causa é desconhecida, o primeiro
item é **achar a causa** — a issue é de investigação e diz isso.

**Critérios de aceite** — frases curtas que se verificam de fora: o comportamento novo
acontece, o vizinho não regrediu, o limite está dito (*"a busca nunca usa o nome"*). Nada
de "funcionar corretamente". Sem cerimônia de Dado/Quando/Então na issue — ela vale na
proposta e na story BMAD, onde o CA vira teste; aqui a frase diz o mesmo, em uma linha,
sem acrescentar nem tirar condição.

**Observações** — de onde veio (*"Reunião de 29/09/2026 com <quem>"*, `CALL-N`), dependências
(*"depende de X"*, e crie a relação `BLOCKS` na API), `**Repo:** <repo> · **Branch:** <nome>
(a partir de <base>)`, dúvida em aberto e quem responde. Causa com `arquivo:linha` **só**
quando você abriu o código e confirmou, em uma linha; senão fica na story.

### Modelo (ouvidoria, 29/09)

```markdown
## Contexto

O analista confere na mão se a pessoa já esteve em ouvidoria procedente. O sistema conta
qualquer caso anterior com o mesmo CPF, sem dizer qual.

## Escopo

- Buscar pelo CPF ou ID os casos anteriores do mesmo cliente concluídos como procedentes.
- Avisar ao informar o documento, com o número da ouvidoria e o tipo de denúncia.
- Levar a reincidência ao relatório final.

## Critérios de aceite

- Ao informar o documento, o analista vê se a pessoa é reincidente e em quais ouvidorias.
- Só contam casos concluídos com desfecho que conta como procedente.
- A busca nunca usa o nome.
- O relatório final lista as ouvidorias anteriores de cada envolvido reincidente.

## Observações

Reunião de 29/09/2026 com Edimilson e Anderson (testes do sistema). Ver roadmap.
```

## Árvore: Feature → Story → Task

| nível | type | o que é | quem pega |
|---|---|---|---|
| Feature | feature | resultado de negócio, guarda-chuva | ninguém direto |
| Story | story | fatia mergeável sozinha, comportamento observável | um dev, se quebrada |
| Task | task | 2h a 8h de trabalho, uma sentada | um dev, direto |

Funcionalidade nova **nunca** nasce como uma issue só. Correção pontual continua
sendo uma issue só. Ligação por `parentId`, criando **pai antes de filho**.

Cada nível usa as mesmas quatro seções, com o que é dele: a **feature** tem Contexto e
Escopo (as fatias) e Observações, sem critérios próprios — os dela são os das stories; a
**story** tem os quatro, com os CAs observáveis; a **task** tem os quatro, curtos, e em
Observações o teste que falha sem a mudança, se já se sabe onde ele mora. Task de 3h com
um parágrafo de contexto é teatro; task sem critério é recado.

**Régua da task: 2h a 8h.** Menos → junte. Mais → quebre. Não dá para quebrar com
honestidade → falta investigação: pare na story e escreva em Observações:

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
- Contexto com nome de arquivo, função ou stack trace? Isso é da story: tire.
- Escopo listando arquivos em vez de comportamento? Reescreva como o que o usuário ganha.
- CA que você não sabe verificar? Não é CA.
- Afirmação sobre código que você não abriu? Abra ou remova.
- Segredo, token, CPF ou dado pessoal real no corpo? Fora — a issue é lida pelo workspace inteiro.
- O título sozinho, na lista do board, diz o que muda?
- Funcionalidade nova virando uma issue só? Falta a árvore.
- Task fora de 2–8h, ou estimate em feature/story?
