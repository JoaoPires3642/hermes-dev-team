#!/usr/bin/env bash
# Instala (ou atualiza) o time de bots de dev do Hermes nesta máquina.
# Idempotente: rodar de novo aplica a versão atual do repo sem apagar memórias/sessões.
#
#   ./install.sh                 # todos os bots
#   ./install.sh dev-back qa     # só alguns
#
# Segredos: ~/.config/hermes-dev-team/secrets.env (fora do git, chmod 600)
#   TUPLE_API_KEY=tpl_...

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALL_BOTS=(orquestrador po pm techlead dev-front dev-back qa)
BOTS=("${@:-${ALL_BOTS[@]}}")
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
SECRETS="${HERMES_DEV_TEAM_SECRETS:-$HOME/.config/hermes-dev-team/secrets.env}"
BIN_DIR="$HOME/.local/bin"

say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[erro]\033[0m %s\n' "$*" >&2; exit 1; }

# grava/atualiza KEY=VAL num arquivo .env sem duplicar
set_env() {
  local file=$1 key=$2 val=$3
  touch "$file"; chmod 600 "$file"
  if grep -q "^${key}=" "$file"; then
    local tmp; tmp=$(mktemp)
    awk -v k="$key" -v v="$val" 'BEGIN{FS=OFS="="} $1==k{print k"="v; next} {print}' "$file" >"$tmp"
    cat "$tmp" >"$file"; rm -f "$tmp"
  else
    printf '%s=%s\n' "$key" "$val" >>"$file"
  fi
}

# ---------------------------------------------------------------- dependências
say "Checando dependências"
for cmd in hermes git curl jq flock; do
  command -v "$cmd" >/dev/null || die "falta '$cmd' no PATH"
done
if ! command -v kiro-cli >/dev/null; then
  warn "kiro-cli não encontrado — instale e rode 'kiro-cli login' antes de usar os bots"
fi

# ---------------------------------------------------------------- segredos
if [[ ! -f "$SECRETS" ]]; then
  mkdir -p "$(dirname "$SECRETS")"
  printf 'TUPLE_API_KEY=\n' >"$SECRETS"
  chmod 600 "$SECRETS"
fi
# shellcheck disable=SC1090
source "$SECRETS"
if [[ -z "${TUPLE_API_KEY:-}" && -t 0 ]]; then
  read -rsp "TUPLE_API_KEY (fica só em $SECRETS): " TUPLE_API_KEY; echo
  set_env "$SECRETS" TUPLE_API_KEY "$TUPLE_API_KEY"
fi
[[ -n "${TUPLE_API_KEY:-}" ]] || warn "TUPLE_API_KEY vazio em $SECRETS — bots não vão conseguir usar o TUPLE"

# ---------------------------------------------------------------- kiro-pool + agentes Kiro
say "Instalando kiro-pool em $BIN_DIR"
mkdir -p "$BIN_DIR"
install -m 755 "$REPO/bin/kiro-pool" "$BIN_DIR/kiro-pool"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR não está no PATH";; esac

say "Instalando agentes Kiro em ~/.kiro/agents"
mkdir -p "$HOME/.kiro/agents"
for b in "${BOTS[@]}"; do
  install -m 644 "$REPO/kiro-agents/hermes-$b.json" "$HOME/.kiro/agents/hermes-$b.json"
done

# ---------------------------------------------------------------- bots
for b in "${BOTS[@]}"; do
  src="$REPO/bots/$b"
  [[ -d "$src" ]] || die "bot desconhecido: $b"
  prof="$HERMES_ROOT/profiles/$b"
  say "Bot @$b"

  if [[ -d "$prof" ]]; then
    hermes profile install "$src" --force -y >/dev/null
  else
    hermes profile install "$src" -y >/dev/null
  fi
  [[ -d "$prof" ]] || die "profile $b não apareceu em $prof"

  # provider kiro-acp (plugins de model-provider são por profile)
  mkdir -p "$prof/plugins/model-providers/kiro-acp"
  cp "$REPO"/plugins/model-providers/kiro-acp/{__init__.py,plugin.yaml} "$prof/plugins/model-providers/kiro-acp/"

  # skills compartilhadas
  mkdir -p "$prof/skills"
  for s in "$REPO"/shared-skills/*/; do
    name=$(basename "$s")
    rm -rf "$prof/skills/$name"
    cp -r "$s" "$prof/skills/$name"
  done

  # .env do profile (segredo + como chamar o Kiro)
  set_env "$prof/.env" TUPLE_API_KEY "${TUPLE_API_KEY:-}"
  set_env "$prof/.env" HERMES_KIRO_ACP_COMMAND "$BIN_DIR/kiro-pool"
  set_env "$prof/.env" HERMES_KIRO_ACP_ARGS "acp --agent hermes-$b"

  # pet (cosmético — não falha a instalação)
  pet=$(awk -F'"' '/slug:/{print $2; exit}' "$src/config.yaml")
  if [[ -n "$pet" ]]; then
    if hermes -p "$b" pets install "$pet" --select >/dev/null 2>&1; then
      # avatar do Bot Mode = 1º quadro do pet (assets/avatar.png)
      python3 "$REPO/scripts/pet_avatar.py" "$prof" "$pet" >/dev/null 2>&1 \
        || warn "não gerei o avatar de @$b (precisa de python3 + Pillow)"
    else
      warn "pet '$pet' não instalou para @$b"
    fi
  fi
done

say "Pronto: ${BOTS[*]}"
cat <<EOF

Próximos passos (uma vez por máquina):
  1. kiro-cli login                                  # conta da empresa
  2. hermes -p orquestrador mcp login granola        # OAuth do Granola MCP
  3. Hermes Desktop → Settings → Advanced → Warm Bot Backends = 7
  4. Telegram: hermes -p orquestrador gateway setup  (ver README)
  5. Routines no Desktop: @orquestrador (Granola + TUPLE) e @pm (diária)
  6. Pasta de cliente: cp -r $REPO/templates/cliente ~/clientes/<cliente>
EOF
