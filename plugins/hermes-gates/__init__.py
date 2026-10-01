"""hermes-gates — os gates humanos pelo Telegram, sem passar pelo modelo.

Comando de plugin roda no gateway DEPOIS da autorização (só TELEGRAM_ALLOWED_USERS
chega aqui) e ANTES de qualquer turno do agente: o texto que você digitou vira uma
chamada ao `call-dispatch`, com o seu id e o id da mensagem como prova (`--via`).
Nenhum bot decide que você aprovou — quem registra `--by humano` é o call-dispatch.

Por que não deixar o @orquestrador ler "aprovado" na conversa: aí a aprovação seria
a palavra do bot, e ele é justamente quem lê transcrição de cliente (entrada não
confiável). Aqui não há modelo no caminho.

Toque em vez de digitar
-----------------------
As mensagens trazem os comandos prontos — `/aprovar_CALL_1`, `/cliente_CALL_1_acme`.
O Telegram transforma `/palavra` em link e manda ao tocar, mas só aceita letra,
número e `_`. O hook `pre_gateway_dispatch` traduz de volta (`/aprovar CALL-1`)
antes da autorização, que continua valendo igual para o texto traduzido.

`/ajustar_X`, `/rejeitar_X` e `/novo_CALL_N` precisam de texto: tocar deixa um pedido pendente
(10 min) e a sua PRÓXIMA mensagem vira o texto. O pendente só nasce no handler —
depois da autorização —, então remetente estranho não consegue armar um.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

# comando → (quantos argumentos fixos, aceita texto livre no fim, dica, descrição)
COMANDOS = {
    "cliente": (2, False, "<CALL-N> <projeto>", "Diz de qual cliente é a call e dispara a triagem"),
    "novo": (1, True, "<CALL-N> <nome do cliente>", "Cliente novo: cria a pasta do projeto e dispara a triagem"),
    "ignorar": (1, False, "<CALL-N>", "Descarta a call sem rodar nenhum bot"),
    "aprovar": (1, False, "<KEY>", "Aprova o GATE 1 (call) ou o GATE 2 (issue)"),
    "ajustar": (1, True, "<KEY> <o que mudar>", "Devolve o gate com o ajuste pedido"),
    "rejeitar": (1, True, "<KEY> <motivo>", "Rejeita o gate"),
    "atendido": (1, True, "<KEY> <motivo>", "Encerra: o trabalho já está pronto, não construa"),
    "pendentes": (0, False, "", "Lista o que espera por você"),
    "cancelar": (0, False, "", "Desiste do ajuste/rejeição pendente"),
}
PENDENTE_SEG = 600
TOQUE = re.compile(r"^/(aprovar|ignorar|ajustar|rejeitar|atendido|cliente|novo)_([A-Za-z0-9_]+?)(?:@\w+)?\s*$")


# ------------------------------------------------------------------ pendente
def _arq_pendente() -> Path:
    try:
        from hermes_constants import get_hermes_home
        base = Path(get_hermes_home())
    except Exception:
        base = Path.home() / ".hermes"
    return base / "hermes-gates-pendente.json"


def _ler_pendentes() -> dict:
    try:
        dados = json.loads(_arq_pendente().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    agora = time.time()
    return {k: v for k, v in dados.items() if v.get("ate", 0) > agora}


def _gravar_pendentes(dados: dict) -> None:
    f = _arq_pendente()
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados), encoding="utf-8")
    os.replace(tmp, f)


# ------------------------------------------------------------------ toque → comando
def _traduzir(texto: str, uid: str) -> str | None:
    """`/aprovar_CALL_1` → `/aprovar CALL-1`; texto livre com pendente → `/ajustar KEY texto`."""
    m = TOQUE.match(texto)
    if m:
        cmd, resto = m.groups()
        if cmd == "cliente":
            c = re.match(r"(CALL)_(\d+)_(\w+)$", resto, re.I)
            return f"/cliente CALL-{c.group(2)} {c.group(3)}" if c else None
        return f"/{cmd} {resto.replace('_', '-')}"
    if texto.startswith("/") or not uid:
        return None
    pend = _ler_pendentes()
    p = pend.pop(uid, None)
    if not p:
        return None
    _gravar_pendentes(pend)
    return f"/{p['cmd']} {p['key']} {texto}"


def _hook(event=None, **_kw):
    try:
        texto = (getattr(event, "text", "") or "").strip()
        fonte = getattr(event, "source", None)
        plataforma = getattr(getattr(fonte, "platform", None), "value", "")
        uid = str(getattr(fonte, "user_id", "") or "")
        if plataforma != "telegram" or not texto:
            return None
        novo = _traduzir(texto, uid)
        return {"action": "rewrite", "text": novo} if novo else None
    except Exception:
        return None   # nunca derrubar a mensagem por causa do atalho


# ------------------------------------------------------------------ comandos
def _dispatch() -> list[str] | None:
    achado = shutil.which("call-dispatch") or str(Path.home() / ".local" / "bin" / "call-dispatch")
    return [achado] if Path(achado).is_file() else None


def _sessao(nome: str) -> str:
    from gateway.session_context import get_session_env
    return get_session_env(nome, "")


def _prova() -> str | None:
    uid = _sessao("HERMES_SESSION_USER_ID")
    if _sessao("HERMES_SESSION_PLATFORM") != "telegram" or not uid:
        return None
    return f"telegram:{uid}:{_sessao('HERMES_SESSION_MESSAGE_ID')}"


def _fazer(nome: str):
    fixos, livre, dica, _ = COMANDOS[nome]

    def handler(raw_args: str) -> str:
        if nome == "cancelar":
            pend = _ler_pendentes()
            some = pend.pop(_sessao("HERMES_SESSION_USER_ID"), None)
            _gravar_pendentes(pend)
            return "Cancelado." if some else "Nada pendente."
        cmd = _dispatch()
        if not cmd:
            return "call-dispatch não está instalado nesta máquina (rode o install.sh do hermes-dev-team)."
        partes = (raw_args or "").split(None, fixos) if fixos else []
        fixas, resto = partes[:fixos], " ".join(partes[fixos:]).strip()
        if len(fixas) < fixos or (resto and not livre):
            return f"Uso: /{nome} {dica}".rstrip()
        via = None
        if nome != "pendentes":
            via = _prova()
            if not via:
                return "Gate só vale pelo Telegram."
        if livre and not resto:
            # veio do toque em /ajustar_X: a próxima mensagem é o texto
            uid = via.split(":")[1]
            pend = _ler_pendentes()
            pend[uid] = {"cmd": nome, "key": fixas[0], "ate": time.time() + PENDENTE_SEG}
            _gravar_pendentes(pend)
            o_que = {"ajustar": "o que mudar", "rejeitar": "o motivo",
                     "atendido": "por que já está atendido",
                     "novo": "o nome do cliente novo (vira a pasta do projeto)"}[nome]
            dica = ("\nÉ sobre o entendimento da call, e não sobre a quebra? Comece com “orquestrador:”."
                    if nome == "ajustar" and fixas[0].upper().startswith("CALL-") else "")
            return f"✍️ Manda na próxima mensagem {o_que} em {fixas[0]}. (vale 10 min · /cancelar){dica}"
        args = cmd + [nome]
        if via:
            args += ["--via", via, *fixas]
            if livre:
                args += ["--", resto]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=25,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        except subprocess.TimeoutExpired:
            return f"/{nome}: o call-dispatch não respondeu em 25s. Veja /pendentes."
        return (r.stdout or r.stderr or "").strip() or f"/{nome}: sem resposta (código {r.returncode})"

    return handler


def register(ctx) -> None:
    for nome, (_, _, dica, desc) in COMANDOS.items():
        ctx.register_command(nome, handler=_fazer(nome), description=desc, args_hint=dica)
    ctx.register_hook("pre_gateway_dispatch", _hook)
