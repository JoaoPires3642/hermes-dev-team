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
ALL_BOTS=(orquestrador po pm arquiteto techlead dev-front dev-back qa)
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

# As dependencias Python do time moram numa pasta do proprio Hermes, nao no user
# site do pip. Motivo medido nesta maquina: o Agendador de Tarefas NAO consegue ler
# %APPDATA%\Python\...\site-packages -- `os.path.isdir` devolve False la dentro,
# com USERPROFILE e APPDATA corretos e o diretorio no sys.path. O job das calls
# morria em `import yaml` a cada 15 minutos por causa disso. %LOCALAPPDATA%\hermes
# e legivel no mesmo contexto (verificado disparando a tarefa), e nao precisa de
# admin como o site-packages do sistema precisaria.
PYLIBS="$HERMES_ROOT/pylibs"
PYSITE_WIN="$(cygpath -m "$PYLIBS" 2>/dev/null || echo "$PYLIBS")"
if ! PYTHONPATH="$PYSITE_WIN" python -c "import yaml" 2>/dev/null; then
  say "Instalando PyYAML em $PYLIBS (o Agendador nao le o site do usuario)"
  python -m pip install --quiet --target "$PYLIBS" pyyaml \
    || die "nao consegui instalar PyYAML em $PYLIBS"
fi

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
# ja garantido em $PYLIBS acima; aqui so confirma que o caminho resolve
PYTHONPATH="$PYSITE_WIN" python -c "import yaml" 2>/dev/null \n  || die "PyYAML nao resolve nem em $PYLIBS"
[[ -f "$CBM_WIN" ]] || warn "codebase-memory-mcp não encontrado — @techlead/@dev-*/@qa perdem o grafo do código"

say "Ferramentas em ~/.local/bin (wrappers: o shebang python3 não existe no Windows)"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
REPO_WIN="$(cygpath -w "$REPO" 2>/dev/null || echo "$REPO")"
# Os de Python levam wrapper que chama `python`; os de bash chamam o bash do Git.
# tuple-api NÃO pode ficar de fora: sem ele o bot não fala com o TUPLE, e o
# instalador antigo só embrulhava os de Python — a falha era silenciosa.
BASH_WIN="$(cygpath -w "$(command -v bash)" 2>/dev/null || echo bash)"
CR=$'\r'

# $1 = nome do script · $2 = interpretador no bash · $3 = interpretador no cmd.exe
# REPO com barras normais: e o caminho que o python DO WINDOWS entende, e ele
# aceita barra normal sem escape nenhum -- ao contrario da contrabarra, que o
# bash come dentro de aspas.
REPO_SLASH="${REPO_WIN//\\//}"

criar_wrapper() {
  local f=$1 posix=$2 win=$3
  # O wrapper SEM extensao e o que o Git Bash pega -- e e o que o terminal dos bots
  # usa. Se ele passar o caminho MSYS (/c/Users/...) para o python do Windows, vira
  # C:\c\Users\... e o script nao abre: foi assim que o @orquestrador travou a
  # CALL-1 em RECEIVED, sem chamar o @po. Para o python vai caminho Windows; para o
  # bash (tuple-api, kiro-pool) continua o caminho POSIX, que e o que ELE entende.
  local alvo="$REPO/bin/$f"
  [[ "$posix" == python* ]] && alvo="$REPO_SLASH/bin/$f"
  {
    printf '#!/usr/bin/env bash\n'
    [[ -n "$PYSITE_WIN" ]] && printf 'export PYTHONPATH="%s;${PYTHONPATH:-}"\n' "$PYSITE_WIN"
    printf 'exec %s "%s" "$@"\n' "$posix" "$alvo"
  } >"$BIN_DIR/$f"
  chmod +x "$BIN_DIR/$f"
  # Em tres etapas, nao num printf so: `$(...)` come a quebra de linha final e a
  # linha do PYTHONPATH acabava grudada na do python, gerando um .cmd invalido.
  printf '@echo off%s\n' "$CR" >"$BIN_DIR/$f.cmd"
  [[ -n "$PYSITE_WIN" ]] && printf 'set "PYTHONPATH=%s;%%PYTHONPATH%%"%s\n' "$PYSITE_WIN" "$CR" >>"$BIN_DIR/$f.cmd"
  printf '"%s" "%s" %%*%s\n' "$win" "$REPO_WIN\\bin\\$f" "$CR" >>"$BIN_DIR/$f.cmd"
}

for f in openwhispr-notes git-bot hermes-task bot-chat-reset hermes-delegar call-dispatch resumo-do-dia; do
  [[ -f "$REPO/bin/$f" ]] && criar_wrapper "$f" python python
done
for f in tuple-api kiro-pool; do
  [[ -f "$REPO/bin/$f" ]] && criar_wrapper "$f" bash "$BASH_WIN"
done
# resto de instalação anterior: a Meetily saiu
rm -f "$BIN_DIR/meetily-notes" "$BIN_DIR/meetily-notes.cmd"
case ":$PATH:" in *":$BIN_DIR:"*) ;; *) warn "$BIN_DIR não está no PATH" ;; esac

say "Skills dos agentes Kiro em ~/.kiro/hermes-dev-team"
mkdir -p "$HOME/.kiro/agents" "$HOME/.kiro/hermes-dev-team"
for s in "$REPO"/extra-skills/*/; do
  cp "$s/SKILL.md" "$HOME/.kiro/hermes-dev-team/$(basename "$s").md"
done

# onde está o repo: o call-dispatch copia templates/projeto daqui para cliente novo
set_env "$HERMES_ROOT/.env" HERMES_DEV_TEAM "$REPO_WIN"

for b in "${BOTS[@]}"; do
  src="$REPO/bots/$b"
  [[ -d "$src" ]] || die "bot desconhecido: $b"
  say "Bot @$b"

  "$HERMES" profile install "$src" --force -y >/dev/null
  prof="$HERMES_ROOT/profiles/$b"
  [[ -d "$prof" ]] || die "profile $b não apareceu em $prof"

  # Provider deste bot vem do config.yaml gerado, não é fixo: @orquestrador, @po e @pm
  # vão direto no Claude; os que mexem em código ficam no kiro-cli.
  provedor=$(awk '/^model:/{f=1;next} f&&/provider:/{gsub(/[" ]/,"");sub(/provider:/,"");print;exit}' "$src/config.yaml")

  if [[ "$provedor" == "kiro-acp" ]]; then
    mkdir -p "$prof/plugins/model-providers/kiro-acp"
    cp "$REPO"/plugins/model-providers/kiro-acp/{__init__.py,plugin.yaml} \
       "$prof/plugins/model-providers/kiro-acp/"
  else
    # sobra de instalação anterior em que este bot usava kiro-acp
    rm -rf "$prof/plugins/model-providers/kiro-acp"
  fi

  # gates humanos pelo Telegram — só no @orquestrador (config.yaml já habilita)
  if [[ "$b" == "orquestrador" ]]; then
    rm -rf "$prof/plugins/hermes-gates"; mkdir -p "$prof/plugins"
    cp -r "$REPO/plugins/hermes-gates" "$prof/plugins/hermes-gates"
  fi

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
  if [[ "$provedor" == "kiro-acp" ]]; then
    set_env "$prof/.env" HERMES_KIRO_ACP_COMMAND "$KIRO_WIN"
    # v3 aplicaria as permissions, mas o acp recusa --agent junto com v3 (2.25.0)
    set_env "$prof/.env" HERMES_KIRO_ACP_ARGS "acp --agent hermes-$b"
  else
    sed -i '/^HERMES_KIRO_ACP_/d' "$prof/.env" 2>/dev/null || true
  fi

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
  # `python`, nao `python3`: no Git Bash deste instalador so existe `python`, e o
  # `python3` ausente faria esta checagem falhar sempre — avisando que a Bot Chat
  # nao foi criada justamente quando ela foi.
  # O código de saída do ping não serve: com --max-turns 1, o bot que tenta usar uma
  # ferramenta é cortado e sai 1 mesmo com a sessão criada. Confere no state.db.
  "$HERMES" -p "$b" chat -c "Bot Chat" --create-if-missing \
    -q "ping de instalacao: responda so 'ok', sem ferramentas" --oneshot -Q --max-turns 1 >/dev/null 2>&1 || true
  if python -c 'import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); sys.exit(0 if c.execute("select 1 from sessions where title=?",("Bot Chat",)).fetchone() else 1)' \
      "$HERMES_ROOT/profiles/$b/state.db" 2>/dev/null; then
    say "  @$b: Bot Chat pronto"
  else
    warn "@$b: Bot Chat nao criou — sem ele este bot nao alcanca os outros"
  fi
done

# Job das calls a cada 15 min (Agendador de Tarefas). Mesmo nome da tarefa que já
# existia: o /F substitui a antiga (que só acordava o @orquestrador) em vez de duplicar.
# Um .cmd próprio porque as aspas do --ao-criar dentro do /TR do schtasks não
# sobrevivem; e `python` direto, sem os wrappers, porque a tarefa roda sem o PATH do
# Git Bash.
say "Agendando o job das calls (Agendador de Tarefas, a cada 15 min)"
BIN_WIN="$(cygpath -w "$BIN_DIR" 2>/dev/null || echo "$BIN_DIR")"
printf '@echo off%s\n' "$CR" >"$BIN_DIR/hermes-calls.cmd"
# mesma armadilha do APPDATA: a tarefa agendada roda com ambiente enxuto
[[ -n "$PYSITE_WIN" ]] && printf 'set "PYTHONPATH=%s;%%PYTHONPATH%%"%s\n' "$PYSITE_WIN" "$CR" >>"$BIN_DIR/hermes-calls.cmd"
printf 'python "%s" novas --ao-criar "python \\"%s\\" varrer"%s\n' \
  "$REPO_WIN\\bin\\openwhispr-notes" "$REPO_WIN\\bin\\call-dispatch" "$CR" >>"$BIN_DIR/hermes-calls.cmd"
# de novo sempre: reenvia pergunta que não chegou (timeout do Telegram)
printf 'python "%s" varrer%s\n' "$REPO_WIN\\bin\\call-dispatch" "$CR" >>"$BIN_DIR/hermes-calls.cmd"
schtasks //Create //F //SC MINUTE //MO 15 //TN "hermes-dev-team - openwhispr-notes" //TR "\"$BIN_WIN\\hermes-calls.cmd\"" >/dev/null 2>&1 \
  || warn "não consegui agendar: rode no cmd -> schtasks /Create /F /SC MINUTE /MO 15 /TN \"hermes-dev-team - openwhispr-notes\" /TR \"$BIN_WIN\\hermes-calls.cmd\""

# Resumo do dia às 17h (dias úteis), pelo bot do @pm. HERMES_DAILY_HORA muda o horário.
printf '@echo off%s\npython "%s"%s\n' "$CR" "$REPO_WIN\\bin\\resumo-do-dia" "$CR" >"$BIN_DIR/hermes-daily.cmd"
schtasks //Create //F //SC WEEKLY //D MON,TUE,WED,THU,FRI //ST "${HERMES_DAILY_HORA:-17:00}" \
  //TN "hermes-dev-team - resumo-do-dia" //TR "\"$BIN_WIN\\hermes-daily.cmd\"" >/dev/null 2>&1 \
  || warn "não consegui agendar o resumo do dia (schtasks)"

say "Pronto: ${BOTS[*]}"
python "$REPO/bin/call-dispatch" doctor 2>/dev/null | grep -E "✗|⚠|problema" || true
cat <<EOF

Pendente neste ambiente:
  - PERMISSÕES NÃO APLICADAS: as deny rules de kiro-agents/ dependem da engine v3,
    e o acp do kiro-cli 2.24.0 não aceita --agent com --agent-engine v3. Os bots
    rodam em v2, onde as regras são ignoradas. Hoje o que segura um comando
    proibido é só o prompt/SOUL, não a engine.
  - kiro-pool (limite de 4 sessões Kiro) não foi portado: depende de flock.
    Os bots chamam o kiro-cli.exe direto, sem teto de concorrência.
EOF
