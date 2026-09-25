# <Cliente> — contexto para o time de bots

> Copie esta pasta para `~/clientes/<cliente>/` e preencha. Este arquivo é lido
> pelos bots e pelas sessões kiro-cli. **Nada de segredo aqui** (chaves e PATs
> ficam no `.env` dos profiles / credential helper do git).

## Projeto
- Nome / descrição curta:
- Humanos no time (nome · papel · quem revisa):
- Onde tirar dúvida técnica:

## TUPLE
| Campo | Valor |
|---|---|
| workspace slug | |
| workspaceId | |
| projectId | |
| teamId | |
| Prefixo das issues | |
| assigneeId do João | |
| Como marcar issue para os bots | (ex.: comentário `@bots` ou prioridade/coluna combinada) |

## Repositórios (em `repos/`)
| Repo | Remote (host) | Branch base | Branch de trabalho | Alvo do PR | Build | Testes |
|---|---|---|---|---|---|---|
| repos/<front> | | | | | | |
| repos/<back> | | | | | | |

Identidade git local: `user.name` = `Joao Pires`, `user.email` = `<email do cliente>`.
Branch compartilhada com humanos? (sim/não — se sim, quem):

## Acessos e restrições
- VPN necessária? Bancos: só leitura? Ambientes que bots NÃO tocam:

## Documentação
- `docs/` segue o padrão BMAD (skill `bmad-story`).
- `.kiro/steering/` tem arquitetura, segurança e padrões deste cliente.
