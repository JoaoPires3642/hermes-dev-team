---
name: git-workflow
description: Aplique antes de qualquer operação git nos repos dos clientes. Identidade local, branch compartilhada com o time humano, Conventional Commits, sem force e sem pular hooks.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [git, commits, pr]
---

# Git workflow (time de bots)

## Credenciais

- Nada de credencial em arquivo. O git usa o credential helper da máquina
  (PAT do Azure DevOps / token do GitHub configurado pelo humano no host).
- Se o `AGENTS.md` do projeto disser que o remote exige **VPN**, ela precisa estar
  ativa no host. Falhou por rede → `BLOCKED` com comentário, sem tentar contornar.

## Identidade

- Branch base, branch de trabalho, alvo do PR e identidade (`user.name`/`user.email`)
  de cada repo estão no `AGENTS.md` da pasta do projeto (`~/Documentos/<Projeto>/`).
- Configurar **no repo** (`git config user.name ...`), nunca `--global`.
- Conferir `git config --local user.name` antes de commitar.

## Estratégia de branch (campo do `AGENTS.md` de cada projeto)

- **por-tarefa** → `feature/<KEY>-<slug>` a partir da branch base; front e back na mesma
  branch da tarefa, cada um só nos seus `allowed_paths`; integra só por PR.
- **compartilhada** → a branch do time, com as regras abaixo.

Nos dois casos todo commit leva `Refs: <KEY>` no corpo (o `hermes-task` usa isso).

## Branch compartilhada com humanos

A branch de trabalho pode ser a **mesma** de desenvolvedores humanos. Então:

1. `git fetch` e `git pull --rebase` **antes de cada push**.
2. **Nunca** `--force` / `--force-with-lease`.
3. Conflito no rebase → parar, `git rebase --abort`, `BLOCKED` na issue com os
   arquivos em conflito e avisar na sala. Não resolver conflito de código alheio
   no chute.
4. Não reaproveitar nem apagar branch de outra pessoa.

## Commits (Conventional Commits)

`<type>(<scope>): <descrição>` — minúsculas, imperativo, sem ponto final, ≤ 72c.
Tipos: `feat` `fix` `chore` `docs` `refactor` `perf` `test` `build` `ci` `style` `revert`.
Citar a key da issue no corpo (`Refs: SELL-12`). **Sem** `Co-Authored-By` de agente.

## PR

- Título em Conventional Commits; descrição começa com `[bot @<nome>]`, cita a
  issue, lista os CAs cobertos e como foi testado.
- Depois de abrir: issue → `IN_REVIEW` com o link (skill `kanban-tuple`).
- Merge é **sempre humano** (GATE 3).

## Proibido

`--no-verify`, `--no-gpg-sign`, `--force`, `git reset --hard` em branch
compartilhada, `git config --global`, commitar `.env`/segredos. Hook falhou →
corrigir a causa.
