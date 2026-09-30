---
name: instalar-plataforma-bots
description: Aplicar mudanças do repo hermes-dev-team nos bots.
version: 1.1.0
author: Hermes Orquestrador
license: MIT
metadata:
  hermes:
    tags: [plataforma, instalacao, gateway, windows, bots]
---

# Aplicar mudanças da plataforma nos bots

## When to Use

"dá um pull no hermes-dev-team e aplica nos agents", "reinstala os bots", "reinicia o
gateway", ou qualquer mudança em `bots/`, `souls/`, `shared-skills/`, `extra-skills/`,
`bin/`, `plugins/` que precisa **chegar em disco** nos profiles. Ciclo:
pull → `install-windows.sh` → verificar artefato → gateway → relatar.

O repo da plataforma **não é cliente**: não tem `AGENTS.md`, não entra no fluxo de
call/GATE. É manutenção da própria caixa de ferramentas — faça e relate (mesma distinção
de `onboarding-projeto-plataforma`). O que **não** é livre é commit/push: veja a última seção.

**Regra de ouro: o log do instalador não é prova de que a mudança chegou.** Só o arquivo no
profile é. Verifique o artefato, sempre.

## Ordem

### 1. Ache o repo — ele não está em `$HERMES_PROJETOS`

```bash
grep HERMES_DEV_TEAM "$LOCALAPPDATA/hermes/.env"      # fonte canônica
```

O repo da plataforma mora fora da árvore de projetos (`~/Documents/hermes-dev-team` nesta
máquina), então `ls "$HERMES_PROJETOS"/*/AGENTS.md` **não** o encontra. Ler a variável evita
queimar turno procurando na pasta errada.

### 2. Pull limpo, e leia o que veio

`git status --porcelain` + `git stash list` antes — trabalho local não commitado morre num
pull mal feito. Depois `git pull --ff-only`, e **`git show <HEAD> --stat`**: o que esse commit
mudou é exatamente a lista que você vai conferir no passo 4.

### 3. Rodar o instalador com log e exit code

```bash
cd <repo> && bash install-windows.sh > "$TMPDIR/inst.log" 2>&1; echo "EXIT=$?"
```

**O instalador tem `set -e` e imprime `==> Bot @<nome>` ANTES de cada bot — uma morte no
primeiro bot é indistinguível de "terminou bem" na cauda do log.** Nunca leia só o fim:
confira `EXIT` e, no passo seguinte, o artefato. É assim que várias execuções aparentemente
limpas não entregam mudança nenhuma aos profiles.

**Rodando de DENTRO de uma sessão de bot**, o Hermes exporta
`HERMES_HOME=<root>/profiles/<bot>`, e todo caminho que o script deriva dele cai dentro do
profile de um bot — sintoma: `profile X não apareceu em .../profiles/X/profiles/X`, e o `.env`
do time escrito no lugar errado. Um script de plataforma tem de subir para a raiz acima de
`profiles/` e **exportar** o `HERMES_HOME` corrigido, senão os `hermes` filhos herdam o do bot.

### 4. Verificar o artefato, não o log

A chave que o commit adicionou precisa aparecer em **cada** profile:

```bash
for b in orquestrador po pm arquiteto techlead dev-front dev-back qa; do
  printf '%-13s ' "$b"
  grep -A2 "^telegram:" "$LOCALAPPDATA/hermes/profiles/$b/config.yaml" | tr -d '\r' | tr '\n' ' '
  echo
done
```

`profile install --force` sobrescreve só arquivos *distribution-owned*: config que não mudou
no repo continua igual no profile, e o profile carrega `_config_version` próprio — comparar com
`diff` contra o repo sempre mostra ruído, então busque **a chave**, não igualdade de arquivo.

Confira junto: `.env` da raiz (caminhos **sem contrabarra**) e
`schtasks /Query /TN "<nome da tarefa>"` para cada tarefa agendada.

### 5. Gateway por último

Estado real (pid, `gateway_state`, `served_profiles`, `platforms`) está em
`$LOCALAPPDATA/hermes/gateway_state.json` — leia com `python -c`, não pelo que o CLI diz.

**Reiniciar o gateway de dentro de uma sessão servida por ele derruba o próprio canal no meio
do turno**, e a resposta ao humano se perde. Agende o restart com atraso, em processo
destacado que sobreviva ao fim do turno, responda ao humano, e **confirme depois que o `pid`
em `gateway_state.json` mudou** — restart não confirmado não é restart feito.

Canal que aparece como `connected` é só o do bot que tem token; bot sem canal não recebe
alerta nenhum (detalhe em `auditoria-plataforma-bots`).

### 6. Relatar

Para cada mudança que você teve de fazer: **bug → mecanismo → conserto**, e a lista do que
você **rodou e viu** (exit code, chave presente nos 8 profiles, `schtasks /Query`, pid novo).
O humano deste time pede evidência verificável, não reafirmação — "deve estar ok" não serve,
e surpresa em commit alheio é pior que pergunta.

## Mudança que nasce aqui: o que é gerado não se edita à mão

Quando a mudança não veio de `git pull` e sim de você (skill nova, bot novo, toolset,
deny), **o arquivo que parece ser o certo geralmente é um artefato gerado**. Tudo em
`bots/<bot>/` (`config.yaml`, `extra-skills.txt`, `SOUL.md`) e `kiro-agents/hermes-<bot>.json`
sai de `scripts/gen_bots.py`. Editar o gerado funciona até a próxima regeneração e depois
desaparece sem erro — o mesmo sumiço silencioso da skill que fica só no profile.

**Antes de editar qualquer arquivo do repo da plataforma, procure o nome dele em
`scripts/`.** Achou quem o escreve → mexa na fonte e regere.

Para **uma skill chegar aos bots**, o caminho inteiro é:

1. Arquivo da skill em `shared-skills/<nome>/` (vai para **todos** os bots, sem registro) ou
   `extra-skills/<nome>/` (vai só para quem a **lista**).
2. Se foi `extra-skills/`, acrescente o nome à lista `extra_skills` do bot em
   `scripts/gen_bots.py`. **Sem esse registro a skill pode estar commitada e no push e ainda
   assim não carregar para bot nenhum**: o instalador copia `extra-skills/` lendo
   `bots/<bot>/extra-skills.txt`, que é gerado dessa lista.
3. Regere e confira o `exit`:
   ```bash
   PYTHONPATH="$(cygpath -m "$LOCALAPPDATA/hermes/pylibs")" python scripts/gen_bots.py
   ```
   As dependências Python do time moram em `<hermes>/pylibs`, não no site do usuário.
4. **`git status` tem de mostrar os DOIS gerados** — `bots/<bot>/extra-skills.txt` **e**
   `kiro-agents/hermes-<bot>.json`. Só um deles mexendo significa que a skill foi para a
   árvore errada, ou que você editou o gerado em vez da fonte.
5. Aí sim rode o instalador e verifique o artefato no profile (passos 3 e 4).

## Armadilhas do instalador no host Windows

- **`hermes.cmd`, `python` e `schtasks` são programas nativos: argumento de caminho vai em
  `C:/...`.** `hermes profile install /c/Users/...` responde
  `Cannot resolve distribution source` — e com `set -e` isso mata o script calado. Converta
  com `cygpath -m` e reuse a variável em todas as chamadas nativas do script.
- **Flag nativa que começa com `/` é mutilada pelo MSYS.** `schtasks //Create` é recusado
  (`Argumento/opção inválido`); use `/Create` com `MSYS_NO_PATHCONV=1` no início da linha.
- **Nunca escreva caminho com contrabarra num `.env` gravado via `awk -v`**: o awk processa os
  escapes e `C:\Users\joao...` vira `C:Usersjoao...` em disco. O arquivo fica corrompido sem
  erro, e quem lê a variável depois falha longe daqui. Use barra normal.
- Depth da fronteira MSYS ↔ nativo (scratch que os dois lados leem, aspas aninhadas,
  wrappers que chamam interpretador nativo): a skill `onboarding-projeto-plataforma` traz
  isso na referência dela sobre MSYS × nativo — carregue com
  `skill_view('onboarding-projeto-plataforma', 'references/windows-msys-nativo.md')`.

## Commit e push no repo da plataforma

Sem `AGENTS.md`, nada prescreve identidade nem branch — então **não escolha por conta própria**:

- `git config user.name/user.email` podem estar vazios (local **e** global) e o histórico ter
  mais de um autor. **Pergunte qual identidade** antes de commitar.
- HEAD normalmente está em `main`, e commit/push em `main` exige OK explícito do humano
  (`git-workflow`). Ofereça branch + PR como alternativa na mesma pergunta.
- Commit **sem** marca de bot, no cabeçalho ou no corpo (`git-workflow`).
