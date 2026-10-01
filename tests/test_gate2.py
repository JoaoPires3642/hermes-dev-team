"""Testes do GATE 2 condicional, do lote e do `/atendido`.

Por que existe
--------------
Em 01/10 as seis issues da skymark chegaram ao GATE 2 em 70 segundos, cada uma como
mensagem própria de 40 a 51 linhas abrindo com narração interna em inglês. O humano
respondeu "aprovado" em texto livre; o @orquestrador listou os seis comandos achatando
as perguntas em seis linhas iguais; e a OUVI-154 — em que o @techlead recomendava
**cancelar**, porque o pedido já estava entregue — virou "`/aprovar OUVI-154` — lista de
casos que aguardam o coordenador". Foi aprovada no lote e um @dev-front começou a
reconstruir o que já existia.

Quatro defeitos somaram para isso, e cada um tem teste aqui: o gate mandava o stdout
inteiro em vez do resumo; o gate saía mesmo sem nada a decidir (3 das 6); saía um por
issue em vez de um por call; e não havia comando para "já está pronto".
"""
import io
import json
import types
import unittest
from pathlib import Path

from ambiente import REPO


def carregar(nome):
    """Um script de `bin/` até a `main()` — as funções, sem o argparse."""
    with io.open(REPO / "bin" / nome, encoding="utf-8") as f:
        fonte = f.read()
    mod = types.ModuleType(nome)
    mod.__dict__["__name__"] = nome
    exec(compile(fonte.split("def main(")[0], nome, "exec"), mod.__dict__)
    return mod


class Resumo(unittest.TestCase):
    """O gate manda o resumo do bot, não a sessão dele."""

    def setUp(self):
        self.hd = carregar("hermes-delegar")

    def escrever(self, texto):
        import tempfile
        f = Path(tempfile.mkdtemp()) / "saida.out.md"
        f.write_text(texto, encoding="utf-8")
        return f

    def test_corta_a_narracao_e_devolve_so_o_resumo(self):
        f = self.escrever("Let me verify the exact lines I'll cite.\n"
                          "The && routed to PowerShell again.\n"
                          "Resumo:\n"
                          "- causa em final-report-data.ts:215\n"
                          "- precisa do seu OK em D-TL-1\n")
        self.assertEqual("- causa em final-report-data.ts:215\n"
                         "- precisa do seu OK em D-TL-1",
                         self.hd.resumo_da_rodada(f))

    def test_aceita_as_formas_que_os_bots_usaram(self):
        for marca in ("Resumo:", "Resumo (OUVI-149 · @techlead):", "## Resumo",
                      "**Resumo:**", "--- resumo ---"):
            f = self.escrever("narração\n%s\no que importa\n" % marca)
            self.assertEqual("o que importa", self.hd.resumo_da_rodada(f), marca)

    def test_vale_o_ultimo_marcador(self):
        # Bot que fala de "resumo" no meio da investigação não pode cortar o texto ali.
        f = self.escrever("Vou ler o resumo da call primeiro.\n"
                          "Resumo:\n"
                          "este é o de verdade\n")
        self.assertEqual("este é o de verdade", self.hd.resumo_da_rodada(f))

    def test_sem_marcador_devolve_a_cauda(self):
        # Dois dos seis gates de 01/10 não emitiram marcador. Fallback não é luxo.
        f = self.escrever("\n".join("linha %d" % i for i in range(40)))
        r = self.hd.resumo_da_rodada(f, linhas=3)
        self.assertEqual("linha 37\nlinha 38\nlinha 39", r)

    def test_arquivo_que_nao_existe_nao_derruba_o_aviso(self):
        self.assertEqual("", self.hd.resumo_da_rodada(Path("nao-existe-nenhum.md")))


class Lote(unittest.TestCase):
    """Gates da mesma call saem numa mensagem só, quando a última irmã termina."""

    def setUp(self):
        import tempfile
        self.hd = carregar("hermes-delegar")
        self.root = Path(tempfile.mkdtemp()) / "acme"
        (self.root / ".hermes" / "tasks").mkdir(parents=True)

    def tarefa(self, key, estado, call="CALL-5"):
        d = self.root / ".hermes" / "tasks" / key
        d.mkdir(exist_ok=True)
        m = {"task_id": key, "estado": estado, "objetivo": "obj %s" % key,
             "aprovacoes": {"gate1": {"herdado_de": call}}}
        import yaml
        (d / "manifest.yaml").write_text(yaml.safe_dump(m), encoding="utf-8")
        return m

    def test_segura_enquanto_uma_irma_ainda_especifica(self):
        m = self.tarefa("A-1", "AWAITING_SPEC_APPROVAL")
        self.tarefa("A-2", "SPECIFYING")
        self.assertEqual((None, None),
                         self.hd.lote_gate2(self.root, m, "A-1", "resumo 1", None))
        guardado = json.loads((self.root / ".hermes" / "gates-pendentes" /
                               "CALL-5.json").read_text(encoding="utf-8"))
        self.assertEqual(["A-1"], sorted(guardado["itens"]))

    def test_a_ultima_irma_manda_o_lote_inteiro(self):
        m1 = self.tarefa("A-1", "AWAITING_SPEC_APPROVAL")
        self.tarefa("A-2", "SPECIFYING")
        self.hd.lote_gate2(self.root, m1, "A-1", "resumo um", "docs/s1.md")
        m2 = self.tarefa("A-2", "AWAITING_SPEC_APPROVAL")
        texto, _ = self.hd.lote_gate2(self.root, m2, "A-2", "resumo dois", None)
        self.assertIsNotNone(texto)
        self.assertIn("2 issues esperando", texto)
        self.assertIn("resumo um", texto)
        self.assertIn("resumo dois", texto)
        self.assertIn("docs/s1.md", texto)      # story de quem tinha
        self.assertIn("/atendido", texto)       # a saída que faltava em 01/10
        # some do disco: lote mandado não pode sair de novo na próxima rodada
        self.assertFalse((self.root / ".hermes" / "gates-pendentes" /
                          "CALL-5.json").exists())

    def test_uma_so_nao_diz_1_issue_s(self):
        # Com o gate condicional o lote de uma e o caso comum, nao a excecao.
        m = self.tarefa("A-1", "AWAITING_SPEC_APPROVAL")
        texto, _ = self.hd.lote_gate2(self.root, m, "A-1", "resumo", None)
        self.assertIn("1 issue esperando", texto)
        self.assertNotIn("issue(s)", texto)

    def test_issue_sem_call_pai_nao_entra_em_lote(self):
        # Issue solta não tem com quem se juntar; devolve (None, None) para quem chamou
        # mandar como sempre.
        m = {"task_id": "X-1", "estado": "AWAITING_SPEC_APPROVAL", "aprovacoes": {}}
        self.assertEqual((None, None),
                         self.hd.lote_gate2(self.root, m, "X-1", "r", None))
        self.assertFalse((self.root / ".hermes" / "gates-pendentes").exists()
                         and list((self.root / ".hermes" / "gates-pendentes").iterdir()))

    def test_irma_travada_em_specifying_nao_prende_o_lote_para_sempre(self):
        # Sem teto, uma irmã que morre em SPECIFYING faria o lote nunca sair — e o gate
        # ficaria preso num arquivo que ninguém olha.
        m1 = self.tarefa("A-1", "AWAITING_SPEC_APPROVAL")
        self.tarefa("A-2", "SPECIFYING")
        self.hd.lote_gate2(self.root, m1, "A-1", "resumo um", None)
        f = self.root / ".hermes" / "gates-pendentes" / "CALL-5.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        d["itens"]["A-1"]["em"] -= self.hd.ESPERA_LOTE + 60
        f.write_text(json.dumps(d), encoding="utf-8")
        texto, _ = self.hd.lote_gate2(self.root, m1, "A-1", "resumo um", None)
        self.assertIsNotNone(texto)
        self.assertIn("A-2", texto)             # diz quem ficou de fora
        self.assertIn("SPECIFYING", texto)


class Transicoes(unittest.TestCase):
    """A máquina de estados: sair sem gate, e os recursos do humano."""

    def setUp(self):
        self.ht = carregar("hermes-task")

    def test_techlead_sai_de_specifying_sem_gate_mas_tem_de_justificar(self):
        quem, exig = self.ht.TRANSICOES[("SPECIFYING", "SPEC_APPROVED")]
        self.assertEqual({"techlead"}, quem)
        self.assertIn("sem_decisoes", exig)     # não passa calado

    def test_pedir_o_gate_exige_dizer_o_que_se_pergunta(self):
        # Gate que não diz o que está sendo perguntado é carimbo. Três dos seis de 01/10
        # eram exatamente isso.
        _, exig = self.ht.TRANSICOES[("SPECIFYING", "AWAITING_SPEC_APPROVAL")]
        self.assertIn("decisoes", exig)

    def test_humano_traz_de_volta_o_que_dispensou_o_gate(self):
        quem, exig = self.ht.TRANSICOES[("IMPLEMENTING", "SPECIFYING")]
        self.assertEqual({"humano"}, quem)
        self.assertIn("motivo", exig)

    def test_humano_encerra_o_que_ja_esta_atendido(self):
        for de in ("IMPLEMENTING", "AWAITING_SPEC_APPROVAL"):
            quem, exig = self.ht.TRANSICOES[(de, "CLOSED")]
            self.assertEqual({"humano"}, quem, de)
            self.assertIn("atendido", exig, de)

    def test_bot_nenhum_dispensa_o_gate_de_outro(self):
        for (de, para), (quem, _) in self.ht.TRANSICOES.items():
            if para in ("SPEC_APPROVED", "SPECIFYING") and quem != {"humano"}:
                self.assertEqual({"techlead"}, quem, (de, para))


class Comandos(unittest.TestCase):
    def test_atendido_existe_e_pede_motivo(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hg", REPO / "plugins" / "hermes-gates" / "__init__.py")
        hg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hg)
        self.assertIn("atendido", hg.COMANDOS)
        _, texto_livre, _, _ = hg.COMANDOS["atendido"]
        self.assertTrue(texto_livre, "tem de exigir o motivo")
        self.assertTrue(hg.TOQUE.match("/atendido_OUVI_154"))

    def test_atendido_nao_e_a_mesma_coisa_que_rejeitar_nem_cancelar(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "hg", REPO / "plugins" / "hermes-gates" / "__init__.py")
        hg = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hg)
        # três comandos, três sentidos: spec errada · desistir do ajuste · já está pronto
        self.assertEqual(3, len({hg.COMANDOS[c][3] for c in
                                 ("rejeitar", "cancelar", "atendido")}))


if __name__ == "__main__":
    unittest.main()
