#!/usr/bin/env bash
# board-resumo.sh <pasta-do-projeto>
#
# Resumo read-only do board do projeto: totais por status/tipo e uma linha por issue.
# Serve para o intervalo em que o helper do time ainda recusa a pasta (sem AGENTS.md).
# A chave NUNCA aparece em argv, log ou saída — vai por arquivo de config do curl, apagado em
# seguida. Não escreve nada no board.
set -euo pipefail

dir=${1:?uso: board-resumo.sh <pasta-do-projeto>}
dir=${dir%/}
[[ -r "$dir/.hermes/tuple.env" ]] || { echo "board-resumo: sem $dir/.hermes/tuple.env" >&2; exit 2; }

# Scratch legível por curl/node nativos (paths MSYS como /tmp não existem para eles).
NATIVE_TMP="$(printf '%s' "${LOCALAPPDATA:-$USERPROFILE/AppData/Local}" | tr '\\' '/')/Temp"
mkdir -p "$NATIVE_TMP"
conf="$NATIVE_TMP/h.$$.conf"; out="$NATIVE_TMP/board.$$.json"
trap 'rm -f "$conf" "$out"' EXIT

ler() { sed -n "s/^$1=//p" "$2" 2>/dev/null | tail -1 | tr -d '\r"'"'"' '; }

key=$(ler TUPLE_API_KEY "$dir/.hermes/tuple.env")
[[ -n "$key" ]] || { echo "board-resumo: TUPLE_API_KEY vazio" >&2; exit 2; }

ids="$dir/.hermes/tuple.env"
WS=$(ler TUPLE_WORKSPACE_ID "$ids"); PJ=$(ler TUPLE_PROJECT_ID "$ids")
if [[ -z "$WS" && -r "$dir/.hermes/tuple-ids.env" ]]; then
  ids="$dir/.hermes/tuple-ids.env"
  WS=$(ler TUPLE_WORKSPACE_ID "$ids"); PJ=$(ler TUPLE_PROJECT_ID "$ids")
  echo "board-resumo: IDs vindos de tuple-ids.env — consolide no tuple.env (o helper só lê esse)." >&2
fi
[[ -n "$WS" ]] || { echo "board-resumo: TUPLE_WORKSPACE_ID ausente (não é descobrível por API)" >&2; exit 2; }
base=$(ler TUPLE_API_BASE "$ids"); base=${base:-https://api.tuple.hypesoft.com.br}

# url-encode via env var, nunca por interpolação de string no shell.
inp=$(WS="$WS" PJ="$PJ" node -e 'const q={workspaceId:process.env.WS,limit:100};if(process.env.PJ)q.projectId=process.env.PJ;console.log(encodeURIComponent(JSON.stringify(q)))')

printf 'header = "Authorization: Bearer %s"\n' "$key" > "$conf"
curl -sS -K "$conf" "$base/trpc/issues.list?input=$inp" -o "$out"
rm -f "$conf"

OUT="$out" node -e '
const d=JSON.parse(require("fs").readFileSync(process.env.OUT,"utf8"));
const r=d.result&&d.result.data;              // issues.list -> result.data.issues, nao result.data
const iss=(r&&r.issues)||[];
if(!iss.length){console.error("board-resumo: nenhuma issue; resposta: "+JSON.stringify(d).slice(0,300));process.exit(1)}
console.log("total: "+r.total+"  lidas: "+iss.length+(r.total>iss.length?"  (pagine com offset)":""));
const by=k=>iss.reduce((a,i)=>(a[i[k]]=(a[i[k]]||0)+1,a),{});
console.log("status: "+JSON.stringify(by("status")));
console.log("type:   "+JSON.stringify(by("type")));
const n=k=>+String(k).split("-")[1]||0;
iss.sort((a,b)=>n(a.key)-n(b.key)).forEach(i=>console.log(
  [i.key,i.type,i.status,i.priority,i.estimate==null?"-":i.estimate,i.parentId?"child":"ROOT",i.title].join(" | ")));
'
