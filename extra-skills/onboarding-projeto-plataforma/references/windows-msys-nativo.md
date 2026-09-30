# Fronteira MSYS ↔ nativo (host Windows) e chamada de API sem expor chave

O `terminal` roda bash (MSYS), mas `python`, `node`, `curl` e `git` são binários **nativos**
Windows. Path que o bash entende não é path que eles entendem, e a falha nunca diz isso.

## Regra

**Todo caminho que você passa como ARGUMENTO para um programa nativo tem de ser nativo
(`C:/...`).** Só os builtins do bash (`cd`, `.`, globs) aceitam `/c/...`.

Sintomas, todos com a mesma causa:

| Sintoma | Causa |
|---|---|
| `can't open file 'C:\c\Users\...'` (Errno 2) | `/c/Users/...` foi passado a um interpretador nativo, que o leu como relativo e prefixou o drive |
| `curl: cannot read config from '/tmp/h.conf'` | `$TMPDIR`/`/tmp` são invenções do MSYS; não existem para o curl nativo |
| `ENOENT ... AppData\Local\Temp\x.json` | o arquivo nunca foi criado, porque o passo anterior (curl) já havia falhado — não é problema de short name |

### Scratch usável pelos dois lados

```bash
NATIVE_TMP="$(printf '%s' "${LOCALAPPDATA:-$USERPROFILE/AppData/Local}" | tr '\\' '/')/Temp"
# -> C:/Users/<user>/AppData/Local/Temp   (bash escreve, curl e node leem)
```

### Wrapper que chama interpretador nativo

Um wrapper `exec python "/c/Users/.../bin/ferramenta"` falha para **todos** os projetos ao mesmo
tempo. Ao criar ou consertar um, escreva o alvo em `C:/...` e valide na hora com o subcomando
mais barato da ferramenta (`states`, `--help`), conferindo `exit 0`.

### Aspas e scripts

Pasta com espaço no nome (ex. raiz de OneDrive) trava o bash ao ser percorrida por caminho
absoluto entre aspas. Entre por glob e trabalhe com caminho relativo:

```bash
cd "$HOME"/OneDrive*/Documentos/<projeto> || exit 1
```

Comando com muitas aspas aninhadas é mutilado pelo wrapper do shell. **Escreva num `.sh` no
scratch e rode `bash arquivo.sh`** em vez de montar a linha inline.

## Chamar a API do board antes de o helper funcionar

O helper do time exige `AGENTS.md` — exatamente o arquivo que falta durante o onboarding. Para
**ler** (nunca escrever) o board nesse intervalo, sem a chave aparecer em argv, histórico ou log:

```bash
printf 'header = "Authorization: Bearer %s"\n' "$TUPLE_API_KEY" > "$NATIVE_TMP/h.conf"
curl -sS -K "$NATIVE_TMP/h.conf" "$BASE/trpc/issues.list?input=$inp" -o "$NATIVE_TMP/board.json"
rm -f "$NATIVE_TMP/h.conf"          # sempre, na linha seguinte
```

- `-K <arquivo>` mantém a chave fora da linha de comando; `-H "Authorization: ..."` a expõe.
- Apague o `h.conf` imediatamente, no mesmo script.
- Carregue a chave com `set -a; . .hermes/tuple.env; set +a` e **nunca** a ecoe nem a interpole
  numa mensagem de erro.
- url-encode do `input` por `node -e` lendo de **variável de ambiente**, não por interpolação de
  string no shell.
- Resposta de `issues.list` vem em `result.data.issues` (com `result.data.total` para paginar) —
  não em `result.data`. Ler o lugar errado devolve lista vazia e parece board vazio.
