---
name: call-para-proposta
description: Aplique ao montar a proposta do GATE 1 (call em TRIAGED). Converte o que a call disse em evidências citadas, prova o que já existe antes de propor issue, e escreve uma proposta curta de decisão, com os corpos das issues à parte. Audiência - @po.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [gate-1, proposta, call, evidencias, gap-check]
---

# Da call à proposta

Você **não** está resumindo a reunião. Está convertendo o que a call disse em uma proposta
de trabalho **verificável**: cada linha da proposta aponta para algo que foi dito, e cada
coisa dita tem destino na proposta.

São três arquivos em `.hermes/tasks/CALL-N/`, nesta ordem, e o `hermes-task` recusa o
`move` para `AWAITING_APPROVAL` se eles não baterem entre si:

```
hermes-task move "$P" CALL-N AWAITING_APPROVAL --by po \
  --ev proposta=.hermes/tasks/CALL-N/proposta.md \
  --ev evidencias=.hermes/tasks/CALL-N/evidencias.md \
  --ev corpos=.hermes/tasks/CALL-N/corpos.md
```

A recusa diz exatamente o que faltou: corrija aquilo e mova de novo.

## Fase 1 — Extração: `evidencias.md`

Leia a **nota da call** (caminho no handoff 00), não só o resumo. Extraia **só fatos, sem
interpretar**: um bloco por pedido, decisão, problema, restrição, dúvida ou mudança pedida.

```markdown
Fonte: /caminho/da/nota-da-call.md

## E1 · pedido
> a gente precisa que o perfil tenha aquelas quatro opções
Classe: existente OUVI-147

## E2 · dúvida
> e o nome do responsável também tem que aparecer
Classe: dúvida

## E3 · pedido
Fonte: docs/cliente/especificacao.md
> Com Perfil Válido, Sem Perfil Válido, Sem Pesquisa, Não se Aplica
Classe: existente OUVI-147
```

- `>` é o trecho **literal** da fonte, mínimo 3 palavras. O código confere se ele está lá
  (ignora acento, pontuação e maiúscula). Não corrija o ASR nem resuma; para pular um
  pedaço, corte com `…`.
- `Fonte:` no topo vale para todos; um item de outra fonte (documento do cliente) tem a
  própria `Fonte:`.
- Tudo que a call pediu entra, inclusive o que você acha que já existe: é a Fase 2 que
  decide o destino, não a extração.

## Fase 2 — Contexto: a `Classe:` de cada evidência

Antes de classificar como `nova`, **tente provar que não é**: procure no TUPLE
(`issues.list` com `search`), no `docs/` e no código/AGENTS.md do projeto.

| Classe | Quando | Destino na proposta |
|---|---|---|
| `existente <KEY>` | uma issue aberta já cobre (ou cobre com ajuste) | Alterações (se muda algo) ou Nada a fazer |
| `já feito` + como sabe | já está entregue (issue DONE, tela no ar, código) | Nada a fazer |
| `configuração` | resolve com cadastro/catálogo/parâmetro, sem código | Nada a fazer (ou Alterações, se alguém precisa configurar) |
| `duplicada <KEY>` | é o mesmo que outra evidência ou outra issue | Nada a fazer |
| `dúvida` | falta informação, há contradição, ou é decisão do humano | **Preciso do seu OK** |
| `fora do escopo` | hipótese ("acho que", "numa v2"), pedido de terceiro, papo | Nada a fazer |
| `nova` | você procurou e não existe | Alterações |

**Nunca crie issue só porque o cliente mencionou algo.** `nova` é a última classe, não a
primeira.

## Fase 3 — Gap check

Para cada evidência, pergunte e anote o que achar:

1. Apareceu **explicitamente** na fonte, ou eu deduzi?
2. Está representada na proposta? Na issue **certa**?
3. Implementar exige uma regra que ninguém disse? → é `dúvida`, com a sua premissa.
4. Contradiz outra evidência, uma issue ou o que está no ar?
5. Falta informação para estimar ou para escrever o critério de aceite?
6. Eu acrescentei algo que não está em nenhuma evidência? → tire, ou vire dúvida.

Decisão de negócio com mais de uma leitura não é sua: vai para "Preciso do seu OK" com a
**sua premissa** e o **impacto de cada resposta**. Nunca escolha calado.

## Fase 4 — `proposta.md` (o que o humano lê no Telegram)

Máximo de 80 linhas não vazias. Cinco seções `##`, nesta ordem, todas presentes (escreva
`nenhum` dentro quando for o caso):

```markdown
# Proposta — CALL-5 · <cliente> · <assunto em 5 palavras>

<2 linhas: quem pediu e para quê>

## Resultado
1 desbloqueio · 1 decisão sua · 3 absorvidos por issues existentes · 2 já existem · 0 issues novas · ~6h

## Preciso do seu OK
### 🔴 D1 — Situação do perfil: lista fixa ou editável por cliente? (E2)
Minha premissa: fixa.
- Fixa → só a OUVI-147
- Editável → nova issue de catálogo por cliente (~8h)

## Alterações propostas
### OUVI-147 · desbloquear (E1, E3)
Motivo: o documento do cliente traz as 4 opções. ~3h

### Nova · feat(relatorio): exportar ouvidorias em CSV (E5) · 6h

## Nada a fazer
- E4 → OUVI-149 já cobre
- E6 → já feito: OUVI-98 (DONE)
- E7 → configuração: catálogo de amplitude

## Gap check
Evidências: 7 · com destino: 7 · decisões: 1 · issues novas: 1 · contradições: 0
```

O código cobra:

- **toda** evidência `E<n>` aparece em alguma seção (senão: “esquecida?”);
- todo item `###` de "Preciso do seu OK" e "Alterações propostas" cita ao menos uma
  evidência (senão: “de onde veio?”);
- toda evidência de classe `dúvida` aparece em "Preciso do seu OK";
- nenhuma evidência citada que não exista.

Prioridade e estimativa de cada item cabem em uma linha. Critério de aceite e corpo **não**
entram aqui.

## `corpos.md` (o que o @pm cola no board)

Um bloco por issue nova e por alteração de issue existente, com o corpo completo nas
quatro seções da skill `tuple-definition-of-ready` (Contexto · Escopo · Critérios de
aceite · Observações), título em formato de commit, tipo, prioridade, estimativa e a
árvore Feature → Story → Task quando houver. Cite as evidências na seção Contexto.
Sem issue nem alteração: escreva só `Nenhuma issue nova nem alteração.`

## Depois do move: a auditoria

Quando a call chega em `AWAITING_APPROVAL`, **antes** do gate sair, uma sessão nova sua,
que não viu você escrever, lê a call e procura o que a proposta **perdeu**, **inventou**
ou **decidiu sem autorização**. Se achar, a proposta volta para você nesta mesma sessão,
com os achados num handoff `NN-auditor-para-po.md`:

- procede → corrija os três arquivos e mova de novo;
- não procede → uma linha no Gap check dizendo por quê, e mova de novo.

Depois de 2 voltas o gate sai mesmo assim, com o que sobrou, e quem decide é o humano.

## Antifuncionamento

- Escrever a proposta primeiro e montar as evidências depois para "fechar a conta": as
  evidências viram reflexo da proposta, e o esquecido continua esquecido.
- Uma evidência por assunto em vez de uma por pedido: "relatórios" engole três pedidos
  diferentes, e dois somem.
- Trecho reescrito "para ficar claro": o código recusa, e com razão — paráfrase é onde o
  sentido muda.
- Classe `nova` sem ter procurado no TUPLE: é a origem de issue duplicada.
- Dúvida escondida em "Observações" do corpo: o humano não lê os corpos no gate.
