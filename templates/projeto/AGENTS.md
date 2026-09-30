# <Projeto> — contexto para o time de bots

> Copie esta pasta para `$HERMES_PROJETOS/<Projeto>/` e preencha. Este arquivo é lido
> pelos bots e pelas sessões kiro-cli. **Nada de segredo aqui**: a chave do TUPLE
> deste projeto fica em `.hermes/tuple.env` (chmod 600); credenciais git no
> credential helper da máquina.

## Projeto
- Nome / descrição curta:
- Pasta do cliente no OpenWhispr (vira a pasta em `~/Documents/_calls/`; prefixo `[Cliente]` no título é reserva):
- Pasta de docs BMAD: `docs/`
- Humanos no time (nome · papel · quem revisa):
- Onde tirar dúvida técnica:

## TUPLE

Chave e IDs ficam em `.hermes/tuple.env` — **não repita aqui**. Duplicar dá
divergência: alguém atualiza um lado e o bot lê o outro. Só dois campos são
obrigatórios lá (`TUPLE_API_KEY` e `TUPLE_WORKSPACE_ID`); `projectId` e `teamId`
o bot descobre com `projects.list`.

| Campo | Valor |
|---|---|
| workspace slug (só para humano achar a URL) | |
| assigneeId do João, se você souber | (opcional: a API aceita gravar, mas o bot não consegue descobrir id de ninguém — `members.list` dá 403) |
| Como marcar issue para os bots | (ex.: comentário `@bots` ou prioridade/coluna combinada) |

## Repositórios (em `repos/`)
| Repo | Remote (host) | Branch base | Branch de trabalho | Alvo do PR | Build | Testes |
|---|---|---|---|---|---|---|
| repos/<front> | | | | | | |
| repos/<back> | | | | | | |

**Estratégia de branch:** `por-tarefa` | `compartilhada`  ← escolha uma

Identidade git local: `user.name` = `Joao Pires`, `user.email` = `<email do cliente>`.
Branch compartilhada com humanos? (sim/não — se sim, quem):

## Contrato de comandos
- Ordem entre repos (se houver contrato compartilhado):
- CI/CD — o que dispara em PR / branch de integração / main:
- Regra: **Build → Test → Push**, nessa ordem, sempre — exceto o listado abaixo.

### O que NÃO roda nesta máquina (não peça waiver: decidido aqui)

Preencha só o que de fato não roda. Vazio = tudo roda, e o bot deve rodar.

| comando | por quê | o que vale no lugar |
|---|---|---|
| | | |

Um comando listado aqui vira `na` no DoD (`build=na`, `lint_typecheck=na`), **nunca
`ok`** — quem revisa precisa saber o que não foi verificado. O bot **não** marca
`BLOCKED` nem pede waiver por isso: a decisão está tomada nesta tabela. Ele entrega e
escreve uma linha no comentário da issue dizendo o que ficou sem checar.

Comando que **não** está listado e falha é achado, não waiver: o bot relata.

## Acessos e restrições
- VPN necessária? Bancos: só leitura? Ambientes que bots NÃO tocam:

## Documentação
- `memory/` — aprendizados duráveis do projeto (ver `memory/README.md`).
- `docs/` segue o padrão BMAD (skill `bmad-story`).
- `.kiro/steering/` tem arquitetura, segurança e padrões deste cliente.
