"""git-bot: um working tree por TAREFA, para varios devs rodarem em paralelo no mesmo repo.

Caso real (skymark-ombudsman-web, 01/10): OUVI-148 preparou a branch as 13:12 e as 13:18 a
OUVI-154 trocou a branch por baixo dela; `git add -A` varreu arquivo das tres tarefas.

    python -m unittest discover -s tests -v
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GIT_BOT = Path(__file__).resolve().parent.parent / "bin" / "git-bot"


def sh(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)


class TestWorktrees(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="wt-"))
        self.env = dict(os.environ, HERMES_WORKTREES=str(self.raiz / "wts"))
        sh("git", "init", "-q", "--bare", str(self.raiz / "origin.git"))
        sh("git", "clone", "-q", str(self.raiz / "origin.git"), str(self.raiz / "web"))
        self.web = self.raiz / "web"
        for k, v in (("user.name", "t"), ("user.email", "t@t"), ("core.autocrlf", "false")):
            sh("git", "config", k, v, cwd=self.web)
        (self.web / "base.txt").write_text("base\n")
        sh("git", "add", "-A", cwd=self.web)
        sh("git", "commit", "-qm", "base", cwd=self.web)
        sh("git", "branch", "-M", "develop", cwd=self.web)
        sh("git", "push", "-q", "origin", "develop", cwd=self.web)
        sh("git", "checkout", "-q", "-b", "time/sprint", cwd=self.web)
        sh("git", "push", "-q", "-u", "origin", "time/sprint", cwd=self.web)
        sh("git", "checkout", "-q", "develop", cwd=self.web)

    def tearDown(self):
        def _rw(f, p, _):
            os.chmod(p, 0o700)
            f(p)
        shutil.rmtree(self.raiz, onerror=_rw)

    def bot(self, *args):
        return subprocess.run([sys.executable, str(GIT_BOT), *map(str, args)], capture_output=True,
                              text=True, encoding="utf-8", env=self.env)

    def preparar(self, key, estrategia="por-tarefa", repo=None, **extra):
        a = ["preparar", repo or self.web, "--key", key, "--slug", "x", "--estrategia", estrategia,
             "--base", "develop", "--nome", "t", "--email", "t@t"]
        if estrategia == "compartilhada":
            a += ["--branch", "time/sprint"]
        r = self.bot(*a)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        linha = next(l for l in r.stdout.splitlines() if l.startswith("worktree: "))
        return Path(linha[len("worktree: "):].strip())

    def branch(self, arvore):
        return sh("git", "rev-parse", "--abbrev-ref", "HEAD", cwd=arvore).stdout.strip()

    def commitar(self, arvore, key, arquivo):
        (arvore / arquivo).write_text(key)
        r = self.bot("commit", arvore, "--key", key, "--tipo", "feat", "--desc", "x")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def arquivos_do_ultimo(self, arvore):
        return set(sh("git", "show", "--name-only", "--format=", "HEAD", cwd=arvore).stdout.split())

    def test_quatro_tarefas_ao_mesmo_tempo_cada_uma_na_sua_branch(self):
        keys = ["OUVI-148", "OUVI-149", "OUVI-150", "OUVI-154"]
        arvores = {k: self.preparar(k) for k in keys}
        # a arvore principal nao foi tocada por nenhuma delas
        self.assertEqual(self.branch(self.web), "develop")
        # cada uma continua na SUA branch depois de todas terem preparado (era aqui que trocava)
        for k, a in arvores.items():
            self.assertEqual(self.branch(a), f"feature/{k.lower()}-x")
        # cada uma escreve e commita; o commit leva so o arquivo dela
        for k, a in arvores.items():
            self.commitar(a, k, f"{k}.txt")
        for k, a in arvores.items():
            self.assertEqual(self.arquivos_do_ultimo(a), {f"{k}.txt"})
            self.assertEqual(self.branch(a), f"feature/{k.lower()}-x")

    def test_push_de_branch_por_tarefa_nova_chega_no_remoto(self):
        a = self.preparar("OUVI-1")
        self.commitar(a, "OUVI-1", "f.txt")
        r = self.bot("push", a)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        heads = sh("git", "ls-remote", "--heads", "origin", cwd=self.web).stdout
        self.assertIn("refs/heads/feature/ouvi-1-x", heads)

    def test_compartilhada_duas_tarefas_publicam_na_branch_do_time(self):
        a1 = self.preparar("OUVI-1", "compartilhada")
        a2 = self.preparar("OUVI-2", "compartilhada")
        self.assertEqual((self.branch(a1), self.branch(a2)), ("wt/OUVI-1", "wt/OUVI-2"))
        self.commitar(a1, "OUVI-1", "um.txt")
        self.commitar(a2, "OUVI-2", "dois.txt")
        for a in (a1, a2):
            r = self.bot("push", a)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sh("git", "fetch", "-q", cwd=self.web)
        arquivos = set(sh("git", "ls-tree", "-r", "--name-only", "origin/time/sprint", cwd=self.web).stdout.split())
        self.assertTrue({"um.txt", "dois.txt"} <= arquivos, arquivos)
        # nada foi publicado com o nome local wt/*
        self.assertNotIn("wt/", sh("git", "ls-remote", "--heads", "origin", cwd=self.web).stdout)

    def test_commit_com_key_de_outra_tarefa_dentro_do_worktree_e_recusado(self):
        a = self.preparar("OUVI-148")
        (a / "f.txt").write_text("x")
        r = self.bot("commit", a, "--key", "OUVI-154", "--tipo", "feat", "--desc", "x")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("worktree de OUVI-148", r.stderr)

    def test_preparar_de_novo_devolve_o_mesmo_caminho_e_preserva_o_trabalho(self):
        a = self.preparar("OUVI-148")
        (a / "wip.txt").write_text("trabalho do dev")        # dev morreu no meio
        b = self.preparar("OUVI-148")
        self.assertEqual(a, b)
        self.assertEqual((b / "wip.txt").read_text(), "trabalho do dev")

    def test_worktree_sujo_nao_e_removido_sem_force(self):
        a = self.preparar("OUVI-148")
        (a / "wip.txt").write_text("x")
        r = sh("git", "worktree", "remove", str(a), cwd=self.web)
        self.assertNotEqual(r.returncode, 0)
        self.assertTrue((a / "wip.txt").exists())

    def test_sem_key_a_guarda_de_arvore_suja_continua_de_pe(self):
        # compartilhada sem --key nao cria worktree: cai no piso, que recusa trocar a branch
        # com alteracao de outro na arvore principal
        (self.web / "alheio.txt").write_text("de outro")
        r = self.bot("preparar", self.web, "--estrategia", "compartilhada", "--branch", "time/sprint",
                     "--base", "develop", "--nome", "t", "--email", "t@t")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)          # 3 = BLOCKED
        self.assertIn("alteração não commitada", r.stderr)
        self.assertEqual(self.branch(self.web), "develop")

    def test_key_com_caractere_perigoso_e_recusada(self):
        r = self.bot("preparar", self.web, "--key", "../fora", "--slug", "x", "--estrategia", "por-tarefa",
                     "--base", "develop", "--nome", "t", "--email", "t@t")
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse((self.raiz / "fora").exists())


if __name__ == "__main__":
    unittest.main()
