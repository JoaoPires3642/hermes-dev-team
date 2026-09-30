---
name: git-workflow
description: Aplique antes de qualquer operação git nos repos dos clientes. Use o git-bot; ele já carrega as regras. Aqui fica só o que exige julgamento.
version: 2.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [git, commits, pr]
---

# Git workflow (time de bots)

**Não monte sequências de git na mão.** Use o `git-bot`: as regras do time estão dentro
dele, em código. Uma chamada faz o que antes eram cinco, e o que é proibido não depende
de você lembrar.

```
git-bot estado   <repo>
git-bot preparar <repo> --estrategia por-tarefa|compartilhada --base BRANCH
                        [--key KEY --slug SLUG | --branch BRANCH] --nome NOME --email EMAIL
git-bot commit   <repo> --key KEY --tipo feat --desc "texto" [--escopo api] [--bot dev-back]
git-bot push     <repo>
```

Saída: `0` ok · `1` erro · `2` falta informação · `3` **BLOCKED** (só humano destrava).

O `git-bot` já garante, sem você pedir: identidade local (nunca `--global`),
Conventional Commits validado com `Refs: <KEY>` no corpo, `fetch` + `pull --rebase`
antes de todo push, recusa de `--force`/`--no-verify`/`reset --hard`, recusa de commit
ou push em `main`/`master`, e recusa de arquivo com cara de segredo.

## O que continua sendo decisão sua

**`--base`, `--branch`, `--nome`, `--email` e a estratégia** vêm do `AGENTS.md` do
projeto. Campo em branco → **pergunte ao humano**. O `git-bot` recusa em vez de adivinhar,
e você faz o mesmo: não invente branch nem e-mail.

**Saiu `3` (BLOCKED)** → houve conflito de rebase e o rebase foi abortado; nada foi
enviado. Bot **não resolve conflito de código alheio**. Mova a tarefa para `BLOCKED`
(`hermes-task move ... BLOCKED`), comente na issue com os arquivos em conflito e avise
o humano. Não tente de novo.

**Saiu `2`** → falta informação. Pergunte, não preencha por conta própria.

**Falha de rede/VPN** → se o `AGENTS.md` disser que o remote exige VPN, ela é
responsabilidade do host. Falhou por rede → `BLOCKED` com comentário. Não contorne.

**Branch de outra pessoa** → não reaproveite, não apague.

## PR e merge

Abrir PR ainda é manual (o `git-bot` não faz isso ainda): título em Conventional Commits,
descrição citando a issue, os CAs cobertos e como testou.

## Nada de marca de bot no histórico

**Commit não leva `[bot @nome]`, nem `@dev-front`, nem qualquer assinatura de bot** —
no cabeçalho ou no corpo. O `git-bot` **recusa** o commit se achar uma, e não remove
calado: se a marca está lá, quem montou a mensagem seguiu regra velha, e apagar sem
avisar deixaria a regra velha de pé.

Por quê: o `git log` é do time e é para sempre. Um commit que se anuncia como de bot
muda como a próxima pessoa lê aquele código, e o histórico do repositório não é o lugar
de registrar quem do Hermes trabalhou.

**No comentário da issue a marca continua obrigatória** (`kanban-tuple`), e ali ela tem
função: a chave da API age como o João, então sem `[bot @nome]` ninguém distingue o que
foi pessoa do que foi bot. São lugares diferentes, com regras opostas de propósito.
Depois de abrir: issue → `IN_REVIEW` com o link (skill `kanban-tuple`).

**Merge é sempre humano (GATE 3).** Nenhum bot faz merge, em nenhuma circunstância.
