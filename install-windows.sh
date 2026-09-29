#!/usr/bin/env bash
# Instala (ou atualiza) o time de bots no WINDOWS. Equivalente do install.sh, com
# as diferenças que o Windows exige:
#
#   1. o CLI do Hermes é hermes.cmd (o Git Bash não resolve .cmd sozinho)
#   2. HERMES_HOME fica em %LOCALAPPDATA%\hermes, não em ~/.hermes
#   3. o provider aponta direto para kiro-cli.exe (sem kiro-pool: precisa de flock)
#   4. ATENÇÃO — as regras "permissions" dos agentes Kiro NÃO são aplicadas aqui.
#      Elas só valem na engine v3, e o kiro-cli 2.24.0 (última versão) recusa
#      "acp --agent-engine v3 --agent <nome>": as duas flags são mutuamente
#      exclusivas. Como o desenho exige um agente Kiro por bot, o ACP fica em v2,
#      onde as deny rules são ignoradas em silêncio. Verificado nesta máquina.
#   5. codebase-memory-mcp pelo caminho absoluto do .exe
#
#   ./install-windows.sh              # todos os bots
#   ./install-windows.sh dev-back qa  # só alguns
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALL_BOTS=(orquestrador po pm techlead dev-front dev-back qa)
BOTS=("${@:-${ALL_BOTS[@]}}")

HERMES_ROOT="${HERMES_HOME:-$LOCALAPPDATA/hermes}"
HERMES="${HERMES_CMD:-$LOCALAPPDATA/hermes/bin/hermes.cmd}"
KIRO_EXE="$LOCALAPPDATA/Kiro-Cli/kiro-cli.exe"
# Barras normais de propósito: o Windows aceita, e contrabarra em .env é armadilha.
# O set_env passa o valor por `awk -v`, que processa escapes — "C:\Users\..." vira
# "C:Users..." porque \U, \A, \L são comidos. O .env fica corrompido em disco e o
# provider falha com "Could not find the kiro-acp CLI command".
KIRO_WIN="$LOCALAPPDATA/Kiro-Cli/kiro-cli.exe"
CBM_WIN="$LOCALAPPDATA/Programs/codebase-memory-mcp/codebase-memory-mcp.exe"
KIRO_WIN="${KIRO_WIN//\\//}"
CBM_WIN="${CBM_WIN//\\//}"

# grava/atualiza KEY=VAL sem apagar o resto do arquivo. Reinstalar NÃO pode derrubar o
# que o usuário configurou depois (token do gateway, etc.) — o README promete que
# memórias e sessões sobrevivem, e o .env entra nessa promessa.
set_env() {
  local arquivo=$1 chave=$2 valor=$3
  touch "$arquivo"
  if grep -q "^${chave}=" "$arquivo" 2>/dev/null; then
    local tmp; tmp=$(mktemp)
    awk -v k="$chave" -v v="$valor" 'BEGIN{FS=OFS="="} $1==k{print k"="v; next} {print}' \
      "$arquivo" >"$tmp"
    cat "$tmp" >"$arquivo"; rm -f "$tmp"
  else
    printf '%s=%s\n' "$chave" "$valor" >>"$arquivo"
  fi
}

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

say "Checando dependências"
[[ -f "$HERMES"   ]] || die "hermes.cmd não encontrado em $HERMES"
[[ -x "$KIRO_EXE" ]] || die "kiro-cli.exe não encontrado em $KIRO_EXE"
python -c 'import yaml' 2>/dev/null || die "hermes-task precisa de python com PyYAML"
[[ -f "${CBM_WIN//\//}" ]] || warn "codebase-memory-mcp não encontrado — @techlead/@dev-*/@qa perdem o grafo do código"

say "Ferramentas em ~/.local/bin (wrappers: o shebang python3 não existe no Windows)"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
REPO_WIN="$(cygpath -w "$REPO" 2>/dev/null || echo "$REPO")"
# só os de Python: tuple-api e kiro-pool são bash e não levam wrapper de python
for f in meetily-notes git-bot hermes-task; do
  [[ -f "$REPO/bin/$f" ]] || continue
  # o shell dos bots (Git Bash / MSYS)
  printf '#!/usr/bin/env bash\nexec python "%s" "$@"\n' "$REPO_WIN\\bin\\$f" >"$BIN_DIR/$f"
  chmod +x "$BIN_DIR/$f"
  # cmd.exe / PowerShell
  printf '@echo off\r\npython "%s" %%*\r\n' "$REPO_WIN\\bin\\$f" >"$BIN_DIR/$f.cmd"
done
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR não está no PATH" ;; esac

say "Skills dos agentes Kiro em ~/.kiro/hermes-dev-team"
mkdir -p "$HOME/.kiro/agents" "$HOME/.kiro/hermes-dev-team"
for s in "$REPO"/extra-skills/*/; do
  cp "$s/SKILL.md" "$HOME/.kiro/hermes-dev-team/$(basename "$s").md"
done

for b in "${BOTS[@]}"; do
  src="$REPO/bots/$b"
  [[ -d "$src" ]] || die "bot desconhecido: $b"
  say "Bot @$b"

  "$HERMES" profile install "$src" --force -y >/dev/null
  prof="$HERMES_ROOT/profiles/$b"
  [[ -d "$prof" ]] || die "profile $b não apareceu em $prof"

  # provider kiro-acp (model-provider é por profile)
  mkdir -p "$prof/plugins/model-providers/kiro-acp"
  cp "$REPO"/plugins/model-providers/kiro-acp/{__init__.py,plugin.yaml} \
     "$prof/plugins/model-providers/kiro-acp/"

  # skills compartilhadas + as específicas do bot
  mkdir -p "$prof/skills"
  for s in "$REPO"/shared-skills/*/; do
    n=$(basename "$s"); rm -rf "$prof/skills/$n"; cp -r "$s" "$prof/skills/$n"
  done
  while read -r x; do
    x="${x%$'\r'}"; [[ -n "$x" ]] || continue
    rm -rf "$prof/skills/$x"; cp -r "$REPO/extra-skills/$x" "$prof/skills/$x"
  done <"$src/extra-skills.txt"

  # .env: chave do TUPLE é por projeto, nunca aqui
  [[ -f "$prof/.env" ]] && sed -i '/^TUPLE_API_KEY=/d' "$prof/.env" || true
  [[ -f "$prof/.env" ]] && sed -i '/^TUPLE_API_KEY=/d' "$prof/.env" || true
  set_env "$prof/.env" HERMES_KIRO_ACP_COMMAND "$KIRO_WIN"
  # v3 aplicaria as permissions, mas o acp não aceita --agent junto com v3 (2.24.0)
  set_env "$prof/.env" HERMES_KIRO_ACP_ARGS "acp --agent hermes-$b"

  # agente Kiro, com o caminho absoluto do codebase-memory-mcp
  python - "$REPO/kiro-agents/hermes-$b.json" "$HOME/.kiro/agents/hermes-$b.json" "$HOME" "$CBM_WIN" <<'PY'
import json, sys
src, dst, home, cbm = sys.argv[1:5]
a = json.loads(open(src, encoding="utf-8").read().replace("__HOME__", home.replace("\\", "/")))
for srv in a.get("mcpServers", {}).values():
    if srv.get("command") == "codebase-memory-mcp":
        srv["command"] = cbm
open(dst, "w", encoding="utf-8").write(json.dumps(a, indent=2, ensure_ascii=False))
PY

  # pet (cosmético — nunca falha a instalação)
  pet=$(awk -F'"' '/slug:/{print $2; exit}' "$src/config.yaml")
  if [[ -n "$pet" ]]; then
    "$HERMES" -p "$b" pets install "$pet" --select >/dev/null 2>&1 \
      && python "$REPO/scripts/pet_avatar.py" "$prof" "$pet" >/dev/null 2>&1 \
      || warn "pet/avatar de @$b não instalou (precisa de Pillow) — cosmético"
  fi
done

say "Pronto: ${BOTS[*]}"
cat <<EOF

Pendente neste ambiente:
  - PERMISSÕES NÃO APLICADAS: as deny rules de kiro-agents/ dependem da engine v3,
    e o acp do kiro-cli 2.24.0 não aceita --agent com --agent-engine v3. Os bots
    rodam em v2, onde as regras são ignoradas. Hoje o que segura um comando
    proibido é só o prompt/SOUL, não a engine.
  - kiro-pool (limite de 4 sessões Kiro) não foi portado: depende de flock.
    Os bots chamam o kiro-cli.exe direto, sem teto de concorrência.
EOF
