"""Ambiente isolado para os testes: nada aqui toca o Hermes, o Telegram ou o ~/.hermes reais.

Cada teste ganha uma pasta temporária com:
  bin/       cópias de call-dispatch, hermes-delegar, hermes-task e um `hermes` FALSO
  hermes/    HERMES_HOME com os profiles dos 7 bots (config.yaml + .env do orquestrador)
  projetos/  HERMES_PROJETOS, com o projeto `acme` pronto
  _calls/    HERMES_CALLS
  fake/      o que o hermes falso registrou (sends.jsonl, chats.jsonl) e como deve agir

O PATH do teste é só bin/ + o Python + /usr/bin:/bin — SEM ~/.local/bin. Os scripts
procuram os irmãos primeiro ao lado de si (em bin/), e mesmo o fallback pelo PATH não
alcança os instalados. Foi a falta disso que já disparou uma rodada real do Opus.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UID = "5057406158"
VIA = f"telegram:{UID}:1"
BOTS = {"orquestrador": "anthropic", "po": "anthropic", "pm": "anthropic",
        "techlead": "kiro-acp", "dev-front": "kiro-acp", "dev-back": "kiro-acp", "qa": "kiro-acp"}

# O hermes falso. `send` registra a mensagem (e falha as N primeiras vezes, se pedido);
# `chat` registra a rodada e faz o que fake/acoes.json manda aquele bot fazer — mover o
# estado da tarefa pelo hermes-task, como o bot de verdade faria.
HERMES_FALSO = r'''#!{python}
import json, os, subprocess, sys
from pathlib import Path
fake = Path(os.environ["FAKE_DIR"])
a = sys.argv[1:]
perfil = a[a.index("-p") + 1] if "-p" in a else None

def log(nome, dados):
    with open(fake / nome, "a", encoding="utf-8") as f:
        f.write(json.dumps(dados, ensure_ascii=False) + "\n")

if "send" in a:
    texto = sys.stdin.read() if "--file" in a else a[-1]
    falhas = fake / "send_falhas"
    n = int(falhas.read_text()) if falhas.exists() else 0
    if n > 0:
        falhas.write_text(str(n - 1))
        log("sends_falhos.jsonl", {{"perfil": perfil, "texto": texto}})
        sys.exit(1)
    log("sends.jsonl", {{"perfil": perfil, "texto": texto}})
    sys.exit(0)

if "chat" in a:
    proj = Path(a[a.index("--in") + 1])
    sessao = a[a.index("--continue") + 1]
    key = sessao[: -(len(perfil) + 1)]
    log("chats.jsonl", {{"perfil": perfil, "projeto": str(proj), "sessao": sessao, "key": key,
                         "query": Path(a[a.index("--query-file") + 1]).read_text(encoding="utf-8")}})
    acoes = json.loads((fake / "acoes.json").read_text()) if (fake / "acoes.json").exists() else {{}}
    for estado, ev in acoes.get(perfil, []):
        arq = proj / ".hermes" / "tasks" / key / f"{{ev}}.md"
        arq.write_text(f"{{ev}} de teste", encoding="utf-8")
        subprocess.run([sys.executable, str(Path(__file__).parent / "hermes-task"), "move", str(proj), key,
                        estado, "--by", perfil, "--ev", f"{{ev}}={{arq}}"], check=True, capture_output=True)
    print(f"resumo de teste do @{{perfil}}")
    codigo = fake / "chat_exit"
    sys.exit(int(codigo.read_text()) if codigo.exists() else 0)
sys.exit(0)
'''


class Ambiente:
    def __init__(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="hermes-teste-"))
        self.bin = self.raiz / "bin"
        self.home = self.raiz / "hermes"
        self.projetos = self.raiz / "projetos"
        self.calls = self.raiz / "_calls"
        self.fake = self.raiz / "fake"
        for d in (self.bin, self.home, self.projetos, self.calls, self.fake, self.raiz / "casa"):
            d.mkdir(parents=True)
        for nome in ("call-dispatch", "hermes-delegar", "hermes-task", "resumo-do-dia"):
            shutil.copy(REPO / "bin" / nome, self.bin / nome)
        falso = self.bin / "hermes"
        falso.write_text(HERMES_FALSO.format(python=sys.executable), encoding="utf-8")
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)
        for bot, provedor in BOTS.items():
            prof = self.home / "profiles" / bot
            prof.mkdir(parents=True)
            (prof / "config.yaml").write_text(f"model:\n  provider: {provedor}\n", encoding="utf-8")
        (self.home / "profiles" / "orquestrador" / ".env").write_text(
            f"TELEGRAM_BOT_TOKEN=falso\nTELEGRAM_ALLOWED_USERS={UID}\nTELEGRAM_HOME_CHANNEL={UID}\n",
            encoding="utf-8")
        self.acme = self.novo_projeto("acme")
        self.env = {
            "PATH": os.pathsep.join([str(self.bin), str(Path(sys.executable).parent), "/usr/bin", "/bin"]),
            "HOME": str(self.raiz / "casa"),
            "HERMES_HOME": str(self.home),
            "HERMES_PROJETOS": str(self.projetos),
            "HERMES_CALLS": str(self.calls),
            "HERMES_DEV_TEAM": str(REPO),
            "FAKE_DIR": str(self.fake),
            "PYTHONIOENCODING": "utf-8",
            # sem espera entre tentativas de aviso: a suite nao testa a rede,
            # e o backoff de 3s/6s dominava o tempo total da rodada
            "HERMES_ESPERA_AVISO": "0",
        }
        # O env é montado do zero para isolar, mas no Windows um punhado de variáveis
        # não é "ambiente do usuário", é infraestrutura do próprio Python:
        # APPDATA é onde mora o site-packages do usuário (é lá que o pip instala sem
        # admin), e sem ela `import yaml` falha mesmo com o PyYAML instalado — 42 dos
        # 48 testes quebravam assim, apontando para uma dependência que existia.
        # SystemRoot/COMSPEC/PATHEXT/TEMP são exigidas por socket, subprocess e tempfile.
        # LOCALAPPDATA fica DE FORA de propósito: é onde vive o Hermes de verdade, e
        # repassá-la abriria caminho para um teste enxergar a instalação real.
        for nome in ("APPDATA", "SystemRoot", "SYSTEMROOT", "windir", "COMSPEC",
                     "PATHEXT", "TEMP", "TMP", "PROCESSOR_ARCHITECTURE"):
            if nome in os.environ:
                self.env.setdefault(nome, os.environ[nome])

    def limpar(self):
        shutil.rmtree(self.raiz, ignore_errors=True)

    # ------------------------------------------------------------ montagem
    def novo_projeto(self, nome, pronto=True):
        p = self.projetos / nome
        (p / ".hermes").mkdir(parents=True)
        (p / "AGENTS.md").write_text(f"# {nome}\nprojeto de teste\n", encoding="utf-8")
        if pronto:
            (p / ".hermes" / "tuple.env").write_text("TUPLE_API_KEY=x\nTUPLE_WORKSPACE_ID=y\n", encoding="utf-8")
        return p

    def nova_nota(self, titulo="Call de teste", cliente="acme"):
        d = self.calls / cliente
        d.mkdir(parents=True, exist_ok=True)
        n = d / f"2026-09-29-{len(list(d.iterdir()))}.md"
        n.write_text(f"---\ncliente: {cliente}\ntitulo: {titulo}\ncriado_em: 2026-09-29T10:00:00\n"
                     f"vozes: Ana\n---\n\n**Ana:** quero um relatório.\n", encoding="utf-8")
        (self.calls / ".novas.txt").write_text(str(n) + "\n", encoding="utf-8")
        return n

    def acoes(self, **por_bot):
        """acoes(orquestrador=[("TRIAGED", "resumo")]): o que cada bot falso faz na rodada."""
        (self.fake / "acoes.json").write_text(json.dumps(por_bot), encoding="utf-8")

    def falhar_envios(self, n):
        (self.fake / "send_falhas").write_text(str(n))

    def chat_sai_com(self, codigo):
        (self.fake / "chat_exit").write_text(str(codigo))

    # ------------------------------------------------------------ execução
    def rodar(self, script, *args, entrada=None, extra_env=None):
        env = {**self.env, **(extra_env or {})}
        # encoding explícito: `text=True` sozinho decodifica com o codec padrão do
        # console, que no Windows é cp1252 — e a primeira saída acentuada derruba a
        # thread leitora do subprocess com UnicodeDecodeError, não o teste. O filho já
        # escreve UTF-8 por PYTHONIOENCODING; o pai precisa ler igual.
        return subprocess.run([sys.executable, str(self.bin / script), *args], env=env, input=entrada,
                              capture_output=True, text=True, timeout=120,
                              encoding="utf-8", errors="replace")

    def dispatch(self, *args, **kw):
        return self.rodar("call-dispatch", *args, **kw)

    def resumo(self, *args, **kw):
        return self.rodar("resumo-do-dia", *args, **kw)

    def repo_com_commits(self, projeto, *mensagens):
        repo = projeto / "repos" / "app"
        repo.mkdir(parents=True)
        g = ["git", "-C", str(repo), "-c", "user.name=Teste", "-c", "user.email=t@t"]
        subprocess.run(g[:3] + ["init", "-q"], check=True)
        for i, msg in enumerate(mensagens):
            (repo / f"f{i}.txt").write_text(msg)
            subprocess.run(g + ["add", "."], check=True)
            subprocess.run(g + ["commit", "-q", "-m", msg], check=True)
        return repo

    def task(self, *args):
        return self.rodar("hermes-task", *args)

    def delegar(self, *args, **kw):
        return self.rodar("hermes-delegar", *args, **kw)

    def esperar_rodadas(self, projeto, prazo=30):
        """hermes-delegar solta um supervisor destacado: espera todas as rodadas terminarem."""
        fim = time.time() + prazo
        while time.time() < fim:
            regs = [json.loads(f.read_text(encoding="utf-8"))
                    for f in (projeto / ".hermes" / "runs").glob("*/*.json")]
            if regs and all(r["status"] not in ("agendado", "rodando") for r in regs):
                return regs
            time.sleep(0.2)
        raise AssertionError(f"rodadas não terminaram em {prazo}s: {projeto}")

    # ------------------------------------------------------------ leitura
    def _jsonl(self, nome):
        f = self.fake / nome
        return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def envios(self):
        return self._jsonl("sends.jsonl")

    def chats(self):
        return self._jsonl("chats.jsonl")

    def call(self, cid):
        return json.loads((self.calls / ".dispatch" / f"{cid}.json").read_text(encoding="utf-8"))

    def estado(self, projeto, key):
        import yaml
        return yaml.safe_load((projeto / ".hermes" / "tasks" / key / "manifest.yaml").read_text())["estado"]

    def manifest(self, projeto, key):
        import yaml
        return yaml.safe_load((projeto / ".hermes" / "tasks" / key / "manifest.yaml").read_text())
