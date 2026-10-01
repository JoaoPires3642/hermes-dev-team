"""Estrategia de branch x nome da branch: a contradicao e recusada por CODIGO.

    python -m unittest discover -s tests -v

Caso real (skymark-ombudsman, 01/10): seis tarefas `compartilhada` e o @techlead gravou um nome
diferente em cada uma (feature/ouvi-148-..., fix/ouvi-150-..., develop, nada). O git-bot obedecia
cada uma e trocava a branch do working tree por baixo de quem estava nele.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ambiente import Ambiente  # noqa: E402


class TestBranch(unittest.TestCase):
    def setUp(self):
        self.a = Ambiente()
        self.p = str(self.a.acme)

    def tearDown(self):
        self.a.limpar()

    def nova(self, key, estado="SPEC_APPROVED", estrategia="compartilhada", nome=None):
        r = self.a.task("new", self.p, key, "--objetivo", "t", "--agentes", "dev-front")
        self.assertEqual(r.returncode, 0, r.stderr)
        mf = self.a.acme / ".hermes" / "tasks" / key / "manifest.yaml"
        t = mf.read_text(encoding="utf-8").replace("estado: RECEIVED", f"estado: {estado}")
        t = t.replace("  estrategia: null", f"  estrategia: {estrategia}")
        if nome:
            t = t.replace("  nome: null", f"  nome: {nome}")
        t = t.replace("  base: null", "  base: develop")
        mf.write_text(t, encoding="utf-8")

    def set_(self, key, par, by="techlead"):
        return self.a.task("set", self.p, key, par, "--by", by)

    def negado(self, r, trecho):
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(trecho, r.stdout + r.stderr)

    def ok(self, r):
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_compartilhada_recusa_nome_por_tarefa_quando_ja_ha_outro(self):
        self.nova("ACME-1", nome="time/sprint-7")
        self.nova("ACME-2")
        self.negado(self.set_("ACME-2", "branch.nome=feature/acme-2-x"), "UMA só")

    def test_compartilhada_aceita_o_mesmo_nome_do_time(self):
        self.nova("ACME-1", nome="time/sprint-7")
        self.nova("ACME-2")
        self.ok(self.set_("ACME-2", "branch.nome=time/sprint-7"))

    def test_compartilhada_recusa_a_base_protegida(self):
        # OUVI-149 e OUVI-153 tinham branch.nome=develop: bot nao trabalha na base
        self.nova("ACME-1")
        self.negado(self.set_("ACME-1", "branch.nome=develop"), "base/protegida")

    def test_tarefa_encerrada_nao_obriga_as_novas(self):
        self.nova("ACME-1", estado="CLOSED", nome="feature/velha")
        self.nova("ACME-2")
        self.ok(self.set_("ACME-2", "branch.nome=time/sprint-8"))

    def test_por_tarefa_exige_a_key_no_nome(self):
        self.nova("ACME-1", estrategia="por-tarefa")
        self.negado(self.set_("ACME-1", "branch.nome=feature/outra-coisa"), "não cita ACME-1")
        self.ok(self.set_("ACME-1", "branch.nome=feature/acme-1-relatorio"))

    def test_por_tarefa_recusa_nome_ja_usado_por_outra(self):
        # a KEY de ACME-2 esta no nome, entao so a colisao com a ACME-1 pode recusar
        self.nova("ACME-1", estrategia="por-tarefa", nome="feature/acme-2-reuso")
        self.nova("ACME-2", estrategia="por-tarefa")
        self.negado(self.set_("ACME-2", "branch.nome=feature/acme-2-reuso"), "já é a branch de ACME-1")

    def test_move_para_implementing_recusa_a_contradicao(self):
        # o techlead grava o nome por --ev branch= na transicao, nao so por set
        self.nova("ACME-1", nome="time/sprint-7")
        self.nova("ACME-2")
        mf = self.a.acme / ".hermes" / "tasks" / "ACME-2"
        (mf / "specs").mkdir()
        (mf / "specs" / "s.md").write_text("x", encoding="utf-8")
        r = self.a.task("move", self.p, "ACME-2", "IMPLEMENTING", "--by", "techlead",
                        "--ev", f"specs={mf / 'specs'}", "--ev", "branch=feature/acme-2-x")
        self.negado(r, "UMA só")
        self.assertEqual(self.a.estado(self.a.acme, "ACME-2"), "SPEC_APPROVED")   # nao andou

    def test_humano_pode_corrigir(self):
        self.nova("ACME-1", nome="time/sprint-7")
        self.nova("ACME-2")
        self.ok(self.set_("ACME-2", "branch.nome=feature/acme-2-x", by="humano"))


if __name__ == "__main__":
    unittest.main()
