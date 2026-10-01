"""Testes do `skill-review guardiao`: a catraca de modelo e a trava que não sai.

Por que existe
--------------
O guardião é um portão, e portão que ninguém exercita apodrece calado — ele passa a
dizer "ok" e ninguém descobre. Escrevendo esta catraca à mão em 01/10 ela errou três
vezes antes de acertar, e nenhum dos três erros aparecia na leitura do código:

1. A `TRAVA` tinha `aprove` e a linha do `souls/qa.md` dizia `aprova`. O guardião deixou
   passar a remoção de "Não aprova o que não rodou".
2. Os modelos eram comparados como conjunto do arquivo inteiro. Com os nove bots dentro
   do `gen_bots.py`, descer o @po de sonnet para haiku empatava o maior-que-saiu em opus
   e escondia o @pm subindo de haiku para opus no mesmo commit.
3. A marca `modelo fixado` era procurada no arquivo todo. O `gen_bots.py` carrega essa
   string dentro do próprio template, então os nove bots apareciam como fixados.

Os três são do tipo que só um caso concreto pega. Daí este arquivo.
"""
import io
import types
import unittest

from ambiente import REPO


def carregar():
    """O `skill-review` até a `main()` — as funções, sem o argparse."""
    with io.open(REPO / "bin" / "skill-review", encoding="utf-8") as f:
        fonte = f.read()
    mod = types.ModuleType("sr")
    mod.__dict__["__name__"] = "sr"
    exec(compile(fonte.split("def main(")[0], "skill-review", "exec"), mod.__dict__)
    return mod


CFG = """# Bot @%s — gerado por scripts/gen_bots.py
%smodel:
  default: "%s"
  provider: "anthropic"
"""

GERADOR = '''BOTS = {
    "orquestrador": {
        "model": "claude-opus-5", "provider": "anthropic",
        "model_fixo": "le entrada externa nao confiavel",
        "desc": "x",
    },
    "po": {
        "model": "%s", "provider": "anthropic",
        "desc": "x",
    },
    "pm": {
        "model": "%s", "provider": "anthropic",
        "desc": "x",
    },
    "qa": {
        "desc": "roda no auto do kiro, sem model declarado",
    },
}
'''


def cfg(bot, modelo, fixo=False):
    nota = "# modelo fixado (so humano troca): porque o papel exige\n" if fixo else ""
    return CFG % (bot, nota, modelo)


class Catraca(unittest.TestCase):
    """Descer o modelo é do bot; subir é do humano. A regra é assimétrica de propósito."""

    def setUp(self):
        self.sr = carregar()

    def catraca(self, arq, antes, depois):
        return self.sr._catraca_modelo(arq, antes, depois)

    # ---------------------------------------------------------------- config.yaml
    def test_descer_passa(self):
        self.assertEqual([], self.catraca("bots/po/config.yaml",
                                          cfg("po", "claude-sonnet-5-5"),
                                          cfg("po", "claude-haiku-4-5")))

    def test_subir_nega(self):
        m = self.catraca("bots/pm/config.yaml",
                         cfg("pm", "claude-haiku-4-5"),
                         cfg("pm", "claude-opus-5"))
        self.assertEqual(1, len(m))
        self.assertIn("sobe o degrau", m[0])

    def test_modelo_igual_nao_e_mudanca(self):
        self.assertEqual([], self.catraca("bots/pm/config.yaml",
                                          cfg("pm", "claude-haiku-4-5"),
                                          cfg("pm", "claude-haiku-4-5")))

    def test_modelo_fora_da_tabela_nega(self):
        # Falha fechada: degrau que falta na tabela não é autorização para subir.
        m = self.catraca("bots/pm/config.yaml",
                         cfg("pm", "claude-haiku-4-5"),
                         cfg("pm", "claude-zeta-9"))
        self.assertIn("nao conhece", m[0])

    def test_modelo_fixado_nao_desce(self):
        # O @orquestrador está em opus porque lê entrada externa não confiável. Baixar
        # ali economiza e perde o julgamento que justifica o bot — economia que custa a
        # razão de ser não é economia.
        m = self.catraca("bots/orquestrador/config.yaml",
                         cfg("orquestrador", "claude-opus-5", fixo=True),
                         cfg("orquestrador", "claude-haiku-4-5", fixo=True))
        self.assertIn("modelo fixado", m[0])

    def test_tirar_a_marca_de_fixado_no_mesmo_commit_nao_libera(self):
        # A saída óbvia seria apagar o comentário e trocar o modelo de uma vez. O lado de
        # ANTES também conta, então não libera.
        m = self.catraca("bots/orquestrador/config.yaml",
                         cfg("orquestrador", "claude-opus-5", fixo=True),
                         cfg("orquestrador", "claude-haiku-4-5", fixo=False))
        self.assertIn("modelo fixado", m[0])

    def test_sair_do_auto_do_kiro_e_decisao_humana(self):
        # `auto` não tem preço no state.db, então não há com o que comparar: trocar não é
        # "descer de nada", é mudar de conta.
        m = self.catraca("bots/qa/config.yaml",
                         cfg("qa", "auto"),
                         cfg("qa", "claude-opus-5"))
        self.assertIn("decisao sua", m[0])

    # ---------------------------------------------------------------- gen_bots.py
    def test_descida_nao_mascara_subida_no_gerador(self):
        antes = GERADOR % ("claude-sonnet-5-5", "claude-haiku-4-5")
        depois = GERADOR % ("claude-haiku-4-5", "claude-opus-5")   # po desce, pm sobe
        m = self.catraca("scripts/gen_bots.py", antes, depois)
        self.assertEqual(1, len(m), m)
        self.assertIn("@pm", m[0])
        self.assertIn("sobe o degrau", m[0])

    def test_fixado_no_gerador_e_por_bot_nao_do_arquivo(self):
        # O template do gerador carrega a string "modelo fixado": procurá-la no arquivo
        # todo marcava os nove bots como fixados e negava qualquer descida.
        antes = GERADOR % ("claude-sonnet-5-5", "claude-haiku-4-5")
        depois = GERADOR % ("claude-haiku-4-5", "claude-haiku-4-5")  # só o po desce
        self.assertEqual([], self.catraca("scripts/gen_bots.py", antes, depois))

    def test_le_fixado_de_quem_tem_e_so_de_quem_tem(self):
        lido = self.sr._modelos_de("scripts/gen_bots.py",
                                   GERADOR % ("claude-sonnet-5-5", "claude-haiku-4-5"))
        self.assertEqual(("claude-opus-5", True), lido["orquestrador"])
        self.assertEqual(("claude-sonnet-5-5", False), lido["po"])
        self.assertNotIn("qa", lido)   # sem "model": roda no auto do kiro


class TravaQueSai(unittest.TestCase):
    """Linha que existe para impedir algo não sai por decisão de bot."""

    def setUp(self):
        self.sr = carregar()

    def test_pega_conjugacao_que_a_primeira_versao_perdeu(self):
        # O caso real: a `TRAVA` tinha "aprove", a linha do souls/qa.md dizia "aprova".
        self.assertTrue(self.sr.TRAVA.search(
            "- Não aprova o que não rodou. Teste flaky → reporta como flaky."))

    def test_pega_as_formas_usadas_nos_souls(self):
        for l in ("**Você não move nada para `DONE`.**",
                  "`--by humano` é bloqueado para bot por desenho",
                  "Nunca invente link ou id de tarefa",
                  "Só humano tira de BLOCKED",
                  "Você não cria issue e não manda o gate",
                  "You must not merge"):
            self.assertTrue(self.sr.TRAVA.search(l), l)

    def test_nao_confunde_instrucao_comum_com_trava(self):
        # Falso positivo custa um `--forcar` ao humano, mas custa todo dia: linha que só
        # manda fazer algo não pode travar commit.
        for l in ("Leia o AGENTS.md antes de abrir código",
                  "Agrupe por status com emojis",
                  "Na primeira linha, classifique a natureza da call"):
            self.assertIsNone(self.sr.TRAVA.search(l), l)

    def test_entrada_de_deny_que_sai_conta_como_trava(self):
        # No config.yaml a autoridade está em forma de máquina: a entrada não diz "não"
        # em lugar nenhum, e a TRAVA, que lê português, passaria batido.
        for l in ('    - "*git*commit*"', "    - '*hermes -p * chat*'",
                  '      - "* --no-verify*"'):
            self.assertTrue(self.sr._ENTRADA_DENY.match(l), l)

    def test_nao_confunde_toolset_com_entrada_de_deny(self):
        for l in ('    - "fs_read"', "    - execute_bash", "  model: claude-sonnet-5-5"):
            self.assertIsNone(self.sr._ENTRADA_DENY.match(l), l)


if __name__ == "__main__":
    unittest.main()
