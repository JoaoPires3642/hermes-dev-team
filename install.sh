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

say "Instalando kiro-pool, tuple-api, hermes-task, meetily-notes, openwhispr-notes, git-bot, bot-chat-reset, hermes-delegar e call-dispatch em $BIN_DIR"
mkdir -p "$BIN_DIR"
install -m 755 "$REPO/bin/kiro-pool" "$BIN_DIR/kiro-pool"
install -m 755 "$REPO/bin/tuple-api" "$BIN_DIR/tuple-api"
install -m 755 "$REPO/bin/hermes-task" "$BIN_DIR/hermes-task"
install -m 755 "$REPO/bin/meetily-notes" "$BIN_DIR/meetily-notes"
install -m 755 "$REPO/bin/git-bot" "$BIN_DIR/git-bot"
install -m 755 "$REPO/bin/bot-chat-reset" "$BIN_DIR/bot-chat-reset"
install -m 755 "$REPO/bin/openwhispr-notes" "$BIN_DIR/openwhispr-notes"
install -m 755 "$REPO/bin/hermes-delegar" "$BIN_DIR/hermes-delegar"
install -m 755 "$REPO/bin/call-dispatch" "$BIN_DIR/call-dispatch"
# Shebang absoluto. Dentro do terminal dos bots o primeiro `python3` do PATH é o Python
# embutido do Hermes, SEM PyYAML: com `#!/usr/bin/env python3` o hermes-task,
# hermes-delegar e call-dispatch morriam em `import yaml` justo quando um bot chamava
# (visto no @orquestrador). Fixa o python3 que acabou de passar na checagem acima.
PY3="$(command -v python3)"
for f in hermes-task hermes-delegar call-dispatch openwhispr-notes meetily-notes bot-chat-reset git-bot; do
  [[ -f "$BIN_DIR/$f" ]] && head -1 "$BIN_DIR/$f" | grep -q '^#!/usr/bin/env python3' \
    && sed -i "1s|.*|#!$PY3|" "$BIN_DIR/$f"
done
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

# onde está o repo: o call-dispatch copia templates/projeto daqui para cliente novo
set_env "$HERMES_ROOT/.env" HERMES_DEV_TEAM "$REPO"

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

  # gates humanos pelo Telegram (/aprovar, /cliente...) — só no Telegram do @orquestrador.
  # O config.yaml gerado já traz `plugins.enabled: [hermes-gates]`.
  if [[ "$b" == "orquestrador" ]]; then
    rm -rf "$prof/plugins/hermes-gates"; mkdir -p "$prof/plugins"
    cp -r "$REPO/plugins/hermes-gates" "$prof/plugins/hermes-gates"
  fi

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

# Bot Chat canonico de cada bot.
#
# `message_agent` — a unica via de um bot falar com outro — nao e um toolset: e
# injetada por um portao que exige que o TITULO da sessao seja exatamente
# "Bot Chat" (tools/bot_mode_dm.py: `_session_title(agent) == BOT_CHAT_TITLE`).
# A secao do protocolo no system prompt, que carrega o roster, tem o mesmo
# portao (agent/system_prompt.py). Sem essa sessao o bot sobe inteiro — modelo,
# skills, SOUL — e mesmo assim nao enxerga o time: fica um bot solo.
#
# O sintoma e caro por ser silencioso: o @orquestrador fecha um GATE prometendo
# "distribuo S1 para @techlead" e nao tinha como. Por isso a sessao nasce aqui,
# na instalacao, e nao quando alguem repara na falta.
#
# `-c "Bot Chat" --create-if-missing` e idempotente: reaproveita a que existir.
say "Bot Chat de cada bot (portao do message_agent)"
for b in "${BOTS[@]}"; do
  # O código de saída do ping não serve: com --max-turns 1, o bot que tenta usar uma
  # ferramenta é cortado e sai 1 mesmo com a sessão criada. Confere no state.db.
  hermes -p "$b" chat -c "Bot Chat" --create-if-missing \
    -q "ping de instalacao: responda so 'ok', sem ferramentas" --oneshot -Q --max-turns 1 >/dev/null 2>&1 || true
  if python3 -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); sys.exit(0 if c.execute("select 1 from sessions where title=?",("Bot Chat",)).fetchone() else 1)' \
      "$HERMES_ROOT/profiles/$b/state.db" 2>/dev/null; then
    say "  @$b: Bot Chat pronto"
  else
    warn "@$b: Bot Chat nao criou — sem ele este bot nao alcanca os outros"
  fi
done

# Job das calls: a cada 15 min, exporta do OpenWhispr e, SÓ se houver call nova,
# chama o call-dispatch (pergunta "de qual cliente?" no Telegram). É Python lendo
# SQLite — custo zero quando não há nada. Timer do systemd de usuário (sobrevive a
# logout com linger, que o gateway já exige).
if command -v systemctl >/dev/null && systemctl --user show-environment >/dev/null 2>&1; then
  say "Agendando o job das calls (systemd --user, a cada 15 min)"
  unit="$HOME/.config/systemd/user"; mkdir -p "$unit"
  cat >"$unit/hermes-calls.service" <<UNIT
[Unit]
Description=hermes-dev-team: exporta calls do OpenWhispr e avisa o call-dispatch

[Service]
Type=oneshot
Environment=PATH=$BIN_DIR:/usr/local/bin:/usr/bin:/bin
ExecStart=$BIN_DIR/openwhispr-notes novas --ao-criar "$BIN_DIR/call-dispatch varrer"
# de novo sempre: reenvia pergunta que não chegou (timeout do Telegram); sem call nova, não faz nada
ExecStartPost=$BIN_DIR/call-dispatch varrer
UNIT
  cat >"$unit/hermes-calls.timer" <<UNIT
[Unit]
Description=hermes-dev-team: job das calls a cada 15 min

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Persistent=true

[Install]
WantedBy=timers.target
UNIT
  systemctl --user daemon-reload
  systemctl --user enable --now hermes-calls.timer >/dev/null 2>&1 \
    || warn "não consegui ligar o hermes-calls.timer — veja: systemctl --user status hermes-calls.timer"
else
  warn "sem systemd de usuário: agende à mão a cada 15 min:"
  warn "  $BIN_DIR/openwhispr-notes novas --ao-criar \"$BIN_DIR/call-dispatch varrer\""
fi

say "Pronto: ${BOTS[*]}"
call-dispatch doctor 2>/dev/null | grep -E "✗|⚠|problema" || true
cat <<EOF

Próximos passos (uma vez por máquina):
  1. kiro-cli login                                  # conta da empresa
  2. instalar o OpenWhispr (transcrição local) e criar uma pasta por cliente dentro dele
  3. Hermes Desktop → Settings → Advanced → Warm Bot Backends = 7
  4. Telegram: hermes -p orquestrador gateway setup   # token do @BotFather
     depois:   hermes gateway install                 # gateway do host (sem -p), serve os 7
  5. HERMES_PROJETOS (pasta dos projetos) no ~/.hermes/.env — o gateway e o job das calls leem de lá.
     Routine no Desktop: só o @pm (diária). As calls já estão agendadas (hermes-calls.timer).
  6. Projeto novo: cp -r $REPO/templates/projeto \$HERMES_PROJETOS/<Projeto>
     preencher AGENTS.md, .kiro/steering/ e .hermes/tuple.env (chave DO projeto, chmod 600)
EOF
