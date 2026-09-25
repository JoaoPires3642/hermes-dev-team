---
name: bmad-story
description: Aplique ao escrever ou revisar uma story/PBI. Define o template BMAD do time (1 story = 1 PBI), o checklist de DoR que libera o GATE 2 e como derivar o .kiro/specs a partir da story aprovada.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [bmad, story, spec, dor, kiro]
---

# Story BMAD (padrão do time)

Hierarquia na pasta de docs do projeto (a indicada no `AGENTS.md`; padrão `docs/` em `~/Documentos/<Projeto>/`):

```
docs/
├── prd-<projeto>.md
├── architecture-<projeto>.md
└── epic-<n>-<slug>/
    ├── EPIC-<slug>.md                 # visão, stories, CAs do épico, dependências, riscos
    └── story-<n>.<m>-<slug>.md        # 1 story = 1 PBI = 1 issue no TUPLE
```

## Template da story

```markdown
---
epic: ./EPIC-<slug>.md
story_id: <n>.<m>
status: pending            # pending | approved | in-progress | in-review | done
tuple_key: <PREFIX-123>
---

# Story <n>.<m>: <Título>

## Metadados
| Campo | Valor |
|---|---|
| **Epic** | [EPIC ...](./EPIC-<slug>.md) |
| **Story ID** | <n>.<m> |
| **Titulo** | ... |
| **Status** | Pending |
| **Prioridade** | Alta / Média / Baixa |
| **Repositório** | repos/<repo> (branch <base>) |

## 1. Objetivo
## 2. Historia de Usuario
    Como <papel> / Quero <capacidade> / Para <benefício>
## 3. Contexto                      (estado atual, o que existe, por que mudar)
## 4. Criterios de Aceite           (cenários Dado / Quando / Então / E — numerados)
## 5. Especificacao Tecnica
## 6. Arquivos a Criar/Modificar    (tabela: arquivo · ação · motivo)
## 7. Implementacao de Referencia   (trechos-guia, não o código final)
## 8. Integracoes
## 9. Cenarios de Teste             (tabela: # · título · entrada · resultado esperado)
## 10. Diagrama de Sequencia        (mermaid)
## 11. Dependencias
## 12. Beneficios
## 13. Riscos e Mitigacoes          (tabela: risco · prob. · impacto · mitigação)
## 14. Referencias
## 15. Historico de Alteracoes      (tabela: data · autor · alteração — autor "[bot @nome]" quando for bot)
```

## DoR (Definition of Ready) — checklist antes de pedir o GATE 2

As issues no TUPLE seguem a skill `tuple-definition-of-ready` (árvore, 2–8h,
causa com `arquivo:linha`, o que NÃO está quebrado, teste que falha sem o fix).
A story BMAD em `docs/` é o documento completo; a issue é a peça de trabalho.


- [ ] Objetivo e história de usuário claros, sem termo ambíguo.
- [ ] Todo CA em Dado/Quando/Então, testável, numerado.
- [ ] Arquivos a criar/modificar listados; nenhum "a definir" crítico.
- [ ] Cenários de teste cobrem todos os CAs (inclusive regressão do que não pode mudar).
- [ ] Dependências e bloqueios explícitos (outras stories, acessos, dados, VPN).
- [ ] Riscos com mitigação.
- [ ] Tamanho cabe em 1 PBI; se não couber, quebrar em subtasks no TUPLE (`parentId`).
- [ ] Decisões em aberto listadas como pergunta ao humano, não assumidas.

Story que não passa no DoR **não** vai para o GATE 2: volta para a sala com o
que falta.

## Derivar o .kiro/specs (depois do GATE 2 aprovado)

A story aprovada é a fonte; o `.kiro/specs/<story-id>-<slug>/` é gerado dela:

- `requirements.md` ← seções 1, 2 e 4 (CAs viram requisitos EARS / Dado-Quando-Então)
- `design.md` ← seções 5, 7, 8 e 10
- `tasks.md` ← seção 6 + 9, uma task por arquivo/grupo coerente, cada uma citando
  os CAs que cobre e a key da issue

Mudou a story depois de aprovada → atualizar o histórico (seção 15), regenerar o
spec e avisar na sala. Nunca editar só o `.kiro/specs`.
