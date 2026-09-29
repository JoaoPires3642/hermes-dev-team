#!/usr/bin/env bash
# Instala (ou atualiza) o time de bots de dev do Hermes nesta máquina.
# Idempotente: rodar de novo aplica a versão atual do repo sem apagar memórias/sessões.
#
#   ./install.sh                 # todos os bots
#   ./install.sh dev-back qa     # só alguns
#
# Segredos: nenhum aqui. A API key do TUPLE é POR PROJETO, em
#   $HERMES_PROJETOS/<Projeto>/.hermes/tuple.env  (chmod 600) — ver templates/projeto.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ALL_BOTS=(orquestrador po pm techlead dev-front dev-back qa)
BOTS=("${@:-${ALL_BOTS[@]}}")
HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
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
if ! command -v codebase-memory-mcp >/dev/null; then
  warn "codebase-memory-mcp não encontrado (grafo do código de @techlead/@dev/@qa). Instale só o binário:"
  warn "  curl -fsSL https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/install.sh | bash -s -- --skip-config"
fi
if ! command -v kiro-cli >/dev/null; then
  warn "kiro-cli não encontrado — instale e rode 'kiro-cli login' antes de usar os bots"
fi

# ---------------------------------------------------------------- kiro-pool + agentes Kiro
python3 -c 'import yaml' 2>/dev/null || die "hermes-task precisa de python3 com PyYAML (Arch: pacman -S python-yaml)"

say "Instalando kiro-pool, tuple-api, hermes-task, meetily-notes e git-bot em $BIN_DIR"
mkdir -p "$BIN_DIR"
install -m 755 "$REPO/bin/kiro-pool" "$BIN_DIR/kiro-pool"
install -m 755 "$REPO/bin/tuple-api" "$BIN_DIR/tuple-api"
install -m 755 "$REPO/bin/hermes-task" "$BIN_DIR/hermes-task"
install -m 755 "$REPO/bin/meetily-notes" "$BIN_DIR/meetily-notes"
install -m 755 "$REPO/bin/git-bot" "$BIN_DIR/git-bot"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR não está no PATH";; esac

say "Instalando agentes Kiro em ~/.kiro/agents"
mkdir -p "$HOME/.kiro/agents"
mkdir -p "$HOME/.kiro/hermes-dev-team"
for s in "$REPO"/extra-skills/*/; do
  install -m 644 "$s/SKILL.md" "$HOME/.kiro/hermes-dev-team/$(basename "$s").md"
done
for b in "${BOTS[@]}"; do
  sed "s#__HOME__#$HOME#g" "$REPO/kiro-agents/hermes-$b.json" >"$HOME/.kiro/agents/hermes-$b.json"
  chmod 644 "$HOME/.kiro/agents/hermes-$b.json"
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

  # skills só deste bot (extra-skills.txt)
  while read -r x; do
    [[ -n "$x" ]] || continue
    rm -rf "$prof/skills/$x"; cp -r "$REPO/extra-skills/$x" "$prof/skills/$x"
  done <"$src/extra-skills.txt"

  # .env do profile: só como chamar o Kiro (chave do TUPLE é por projeto)
  [[ -f "$prof/.env" ]] && sed -i '/^TUPLE_API_KEY=/d' "$prof/.env"
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
  2. instalar o OpenWhispr (transcrição local) e criar uma pasta por cliente dentro dele
  3. Hermes Desktop → Settings → Advanced → Warm Bot Backends = 7
  4. Telegram: hermes -p orquestrador gateway setup   # token do @BotFather
     depois:   hermes gateway install                 # gateway do host (sem -p), serve os 7
  5. Routines no Desktop: @orquestrador (meetily-notes + TUPLE) e @pm (diária)
  6. Projeto novo: cp -r $REPO/templates/projeto $HERMES_PROJETOS/<Projeto>
     preencher AGENTS.md, .kiro/steering/ e .hermes/tuple.env (chave DO projeto, chmod 600)
EOF
