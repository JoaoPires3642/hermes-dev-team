"""hermes-gates — os gates humanos pelo Telegram, sem passar pelo modelo.

Comando de plugin roda no gateway DEPOIS da autorização (só TELEGRAM_ALLOWED_USERS
chega aqui) e ANTES de qualquer turno do agente: o texto que você digitou vira uma
chamada ao `call-dispatch`, com o seu id e o id da mensagem como prova (`--via`).
Nenhum bot decide que você aprovou — quem registra `--by humano` é o call-dispatch.

Por que não deixar o @orquestrador ler "aprovado" na conversa: aí a aprovação seria
a palavra do bot, e ele é justamente quem lê transcrição de cliente (entrada não
confiável). Aqui não há modelo no caminho.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# comando → (quantos argumentos fixos, aceita texto livre no fim, dica)
COMANDOS = {
    "cliente": (2, False, "<CALL-N> <projeto>", "Diz de qual cliente é a call e dispara a triagem"),
    "ignorar": (1, False, "<CALL-N>", "Descarta a call sem rodar nenhum bot"),
    "aprovar": (1, False, "<KEY>", "Aprova o GATE 1 (call) ou o GATE 2 (issue)"),
    "ajustar": (1, True, "<KEY> <o que mudar>", "Devolve o gate com o ajuste pedido"),
    "rejeitar": (1, True, "<KEY> <motivo>", "Rejeita o gate"),
    "pendentes": (0, False, "", "Lista o que espera por você"),
}


def _dispatch() -> list[str] | None:
    achado = shutil.which("call-dispatch") or str(Path.home() / ".local" / "bin" / "call-dispatch")
    return [achado] if Path(achado).is_file() else None


def _prova() -> str | None:
    from gateway.session_context import get_session_env

    plataforma = get_session_env("HERMES_SESSION_PLATFORM", "")
    uid = get_session_env("HERMES_SESSION_USER_ID", "")
    msg = get_session_env("HERMES_SESSION_MESSAGE_ID", "")
    if plataforma != "telegram" or not uid:
        return None
    return f"telegram:{uid}:{msg}"


def _fazer(nome: str):
    fixos, livre, dica, _ = COMANDOS[nome]

    def handler(raw_args: str) -> str:
        cmd = _dispatch()
        if not cmd:
            return "call-dispatch não está instalado nesta máquina (rode o install.sh do hermes-dev-team)."
        partes = (raw_args or "").split(None, fixos) if fixos else []
        fixas, resto = partes[:fixos], " ".join(partes[fixos:]).strip()
        if len(fixas) < fixos or (resto and not livre) or (livre and not resto):
            return f"Uso: /{nome} {dica}".rstrip()
        args = cmd + [nome]
        if nome != "pendentes":
            via = _prova()
            if not via:
                return "Gate só vale pelo Telegram."
            args += ["--via", via, *fixas]
            if livre:
                args += ["--", resto]
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=25,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        except subprocess.TimeoutExpired:
            return f"/{nome}: o call-dispatch não respondeu em 25s. Veja `call-dispatch pendentes`."
        return (r.stdout or r.stderr or "").strip() or f"/{nome}: sem resposta (código {r.returncode})"

    return handler


def register(ctx) -> None:
    for nome, (_, _, dica, desc) in COMANDOS.items():
        ctx.register_command(nome, handler=_fazer(nome), description=desc, args_hint=dica)
