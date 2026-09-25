# Steering do projeto

O Kiro carrega automaticamente os `.md` desta pasta. Um arquivo por assunto:

- `projeto.md` — mapa: repos, camadas, stack, ordem entre repos (ex.: contrato → api → web),
  mapa de CI/CD (o que dispara em PR / develop / main).
- `<repo>.md` — **um por repo**: só o que NÃO se tira de um grep — mapa de onde fica o
  quê, decisões, regras invioláveis e **gotchas** (o que já custou caro).
- `seguranca.md` — baseline de segurança.
- `revisao.md` — regras de revisão específicas desta stack (usadas pelo @qa junto
  com a skill `revisao-codigo`).

Regra viva: quando uma regra/gotcha nova deixa um arquivo impreciso, **corrija-o**.
**Sem segredos** — nada de chave, PAT, connection string.
