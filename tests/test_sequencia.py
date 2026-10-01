"""Tarefas sequenciais nao rodam em paralelo: `depende_de` e allowed_paths que se tocam.

    python -m unittest discover -s tests -v

Caso real (skymark-ombudsman, 01/10): a OUVI-149 criava o `lossKind` e a OUVI-148 condicionava a
devolucao a ele, as duas no mesmo formulario. O fluxo as rodou juntas porque nada dizia que uma
esperava a outra; a 148 travou e o dev ainda atribuiu a sujeira ao humano.
"""
import sys
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ambiente import Ambiente  # noqa: E402

FORM = "web/src/components/features/cases/**"
FORM_ARQ = "web/src/components/features/cases/closure-form.tsx"
OUTRO = "web/src/app/dashboard/**"


class TestSequencia(unittest.TestCase):
    def setUp(self):
        self.a = Ambiente()
        self.p = str(self.a.acme)

    def tearDown(self):
        self.a.limpar()

    def mf(self, key):
        return self.a.acme / ".hermes" / "tasks" / key / "manifest.yaml"

    def nova(self, key, estado="SPEC_APPROVED", paths=(), depende=None):
        r = self.a.task("new", self.p, key, "--objetivo", "t", "--agentes", "dev-front")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = yaml.safe_load(self.mf(key).read_text(encoding="utf-8"))
        m["estado"] = estado
        m["branch"] = {"estrategia": "compartilhada", "nome": None, "base": "develop"}
        m["allowed_paths"] = {"dev-front": list(paths)}
        if depende is not None:
            m["depende_de"] = depende
        self.mf(key).write_text(yaml.safe_dump(m, allow_unicode=True), encoding="utf-8")

    def implementar(self, key):
        specs = self.a.acme / ".hermes" / "tasks" / key / "specs"
        specs.mkdir(exist_ok=True)
        (specs / "s.md").write_text("x", encoding="utf-8")
        return self.a.task("move", self.p, key, "IMPLEMENTING", "--by", "techlead",
                           "--ev", f"specs={specs}", "--ev", "branch=time/sprint")

    def estado(self, key):
        return yaml.safe_load(self.mf(key).read_text(encoding="utf-8"))["estado"]

    def recusado(self, r, trecho):
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(trecho, r.stdout + r.stderr)

    def liberado(self, r):
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # --- depende_de
    def test_nao_comeca_enquanto_a_dependencia_nao_foi_entregue(self):
        self.nova("ACME-149", estado="IMPLEMENTING", paths=[OUTRO])
        self.nova("ACME-148", paths=[FORM], depende=["ACME-149"])
        self.recusado(self.implementar("ACME-148"), "depende de ACME-149")
        self.assertEqual(self.estado("ACME-148"), "SPEC_APPROVED")

    def test_comeca_quando_a_dependencia_chega_em_revisao(self):
        self.nova("ACME-149", estado="AWAITING_REVIEW", paths=[FORM])
        self.nova("ACME-148", paths=[FORM], depende=["ACME-149"])
        self.liberado(self.implementar("ACME-148"))
        self.assertEqual(self.estado("ACME-148"), "IMPLEMENTING")

    def test_dependencia_que_nao_existe_e_recusada(self):
        self.nova("ACME-148", paths=[FORM], depende=["ACME-999"])
        self.recusado(self.implementar("ACME-148"), "não existe")

    def test_depende_de_aceita_string_com_virgulas_como_o_resto_do_manifest(self):
        self.nova("ACME-149", estado="IMPLEMENTING", paths=[OUTRO])
        self.nova("ACME-148", paths=[FORM], depende="ACME-149, ACME-150")
        self.recusado(self.implementar("ACME-148"), "ACME-149")

    # --- allowed_paths que se tocam
    def test_caminhos_que_se_tocam_com_outra_ativa_nao_rodam_juntos(self):
        self.nova("ACME-149", estado="IMPLEMENTING", paths=[FORM])
        self.nova("ACME-148", paths=[FORM])
        self.recusado(self.implementar("ACME-148"), "sequenciais, não paralelas")
        self.assertEqual(self.estado("ACME-148"), "SPEC_APPROVED")

    def test_arquivo_exato_dentro_da_pasta_da_outra_tambem_se_toca(self):
        self.nova("ACME-149", estado="TESTING", paths=[FORM_ARQ])
        self.nova("ACME-148", paths=[FORM])
        self.recusado(self.implementar("ACME-148"), "ACME-149")

    def test_caminhos_separados_rodam_em_paralelo(self):
        self.nova("ACME-149", estado="IMPLEMENTING", paths=[FORM])
        self.nova("ACME-154", paths=[OUTRO])
        self.liberado(self.implementar("ACME-154"))

    def test_pasta_irma_com_prefixo_parecido_nao_conta_como_toque(self):
        # cases/ x cases-extra/: o prefixo de texto casa, a pasta nao
        self.nova("ACME-149", estado="IMPLEMENTING", paths=["web/src/cases/**"])
        self.nova("ACME-154", paths=["web/src/cases-extra/**"])
        self.liberado(self.implementar("ACME-154"))

    def test_outra_ainda_nao_ativa_nao_bloqueia(self):
        self.nova("ACME-149", estado="SPEC_APPROVED", paths=[FORM])
        self.nova("ACME-148", paths=[FORM])
        self.liberado(self.implementar("ACME-148"))

    def test_outra_ja_entregue_nao_bloqueia(self):
        self.nova("ACME-149", estado="AWAITING_REVIEW", paths=[FORM])
        self.nova("ACME-148", paths=[FORM])
        self.liberado(self.implementar("ACME-148"))

    # --- set depende_de
    def test_set_recusa_depender_de_si_mesma(self):
        self.nova("ACME-148", paths=[FORM])
        r = self.a.task("set", self.p, "ACME-148", "depende_de=[ACME-148]", "--by", "techlead")
        self.recusado(r, "de si mesma")

    def test_set_recusa_dependencia_circular(self):
        self.nova("ACME-149", paths=[OUTRO], depende=["ACME-148"])
        self.nova("ACME-148", paths=[FORM])
        r = self.a.task("set", self.p, "ACME-148", "depende_de=[ACME-149]", "--by", "techlead")
        self.recusado(r, "circular")

    def test_set_recusa_dependencia_que_nao_existe(self):
        self.nova("ACME-148", paths=[FORM])
        r = self.a.task("set", self.p, "ACME-148", "depende_de=[ACME-999]", "--by", "techlead")
        self.recusado(r, "não existe")

    def test_set_aceita_dependencia_valida(self):
        self.nova("ACME-149", paths=[OUTRO])
        self.nova("ACME-148", paths=[FORM])
        r = self.a.task("set", self.p, "ACME-148", "depende_de=[ACME-149]", "--by", "techlead")
        self.liberado(r)


if __name__ == "__main__":
    unittest.main()
