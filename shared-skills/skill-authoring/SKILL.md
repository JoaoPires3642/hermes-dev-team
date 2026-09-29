---
name: skill-authoring
description: Aplique ao criar ou alterar qualquer skill em shared-skills/ ou extra-skills/. Garante frontmatter correto, corpo prático, e a distinção entre o que é regra de prompt e o que tem que virar código. Audiência - todos os bots e o humano.
version: 1.0.0
author: Joao Pires
metadata:
  hermes:
    tags: [skills, autoria, padroes]
---

# Autoria de skills

Skill é **guia operacional**, não fonte da verdade. A regra normativa mora em
`docs/arquitetura.md` ou no `.kiro/steering/` do cliente; a skill resume e diz
como aplicar.

## Antes de escrever: isso é skill mesmo?

Esta é a pergunta que mais economiza tempo. Skill é texto que entra no contexto
e **depende do modelo obedecer**. Se a regra precisa valer sempre, ela não é
skill — é código.

| Se a regra… | então |
|---|---|
| tem que valer mesmo se o modelo errar | vai para `bin/` (ex.: `git-bot`, `hermes-task`) |
| envolve segredo, push, deploy, estado | vai para código, sem exceção |
| é julgamento sobre conteúdo | pode ser skill |
| é formato de saída ou vocabulário | pode ser skill |

Exemplo real: "nunca `git push --force`" era prosa em `git-workflow` e valia
enquanto o modelo lembrasse. Virou recusa no `git-bot`. A skill agora só aponta
a ferramenta e explica o que fazer com cada código de saída.

## Anatomia

- Arquivo sempre `SKILL.md`, em `shared-skills/<nome-kebab>/` (todos os bots) ou
  `extra-skills/<nome-kebab>/` (só quem listar em `extra-skills.txt`).
- Frontmatter obrigatório:
  ```markdown
  ---
  name: <kebab-case, igual ao nome da pasta>
  description: Aplique ao <gatilho>. <o que garante>. Audiência - <quem>.
  version: 1.0.0
  author: Joao Pires
  ---
  ```
- Corpo **prático**: checklist, tabela, exemplo curto. Sem prosa longa.
- Seção de **antifuncionamento** quando os erros forem previsíveis.

## Escrevendo para uma sessão ACP

O turno do bot roda via `kiro-cli acp` ou provider direto, e isso impõe limites
que não existem num chat comum:

- [ ] **Instrução curta e direta.** Prompt com muitos passos numerados faz o bot
      narrar o plano — e o turno encerra no primeiro texto, antes de agir.
      "Não descreva o que vai fazer: faça" funciona melhor que cinco itens.
- [ ] **Uma fonte por rotina.** Aponte um arquivo ou comando, não "procure".
      Bot que investiga por conta própria reprocessa o que já foi feito.
- [ ] **Diga o que NÃO fazer** nos pontos em que ele tenta ajudar demais: não
      listar a pasta, não investigar, não deduzir. Sem isso ele desconfia do
      caso vazio e vai atrás.
- [ ] **Nunca dependa de memória entre execuções.** Rotina não lembra do turno
      anterior; o estado vive em arquivo.

## Registrar

Skill que ninguém carrega não existe:

- [ ] `shared-skills/` → chega em todos os bots pelo instalador, sem mais nada.
- [ ] `extra-skills/` → adicionar o nome em `extra_skills` do bot no
      `scripts/gen_bots.py` e rodar `python scripts/gen_bots.py`.
- [ ] Citar na lista de skills do `README.md` e em `docs/arquitetura.md`.
- [ ] Reinstalar (`./install.sh` ou `install-windows.sh`) para chegar aos profiles.

## Estilo

- PT-BR. **Negrito** em termo-chave, `code` em arquivo, comando e campo.
- Cada afirmação sobre comportamento externo precisa ter sido **verificada** —
  e vale registrar quando (ver `kanban-tuple`, que anota a data dos IDs).

## Antifuncionamento

- Escrever como skill uma regra que tem que valer sempre.
- Duplicar o conteúdo do doc em vez de resumir e apontar.
- Prompt de rotina com cinco passos numerados.
- Supor que o bot lembra do que fez na execução anterior.
- Afirmar comportamento de API que você não testou.
