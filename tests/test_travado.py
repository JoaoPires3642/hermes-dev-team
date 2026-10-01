"""Testes do que trava em silêncio: rodada que não sobe e tarefa sem ninguém nela.

Por que existe
--------------
01/10, 14:10. Dez tarefas paradas e nenhuma aparecendo para o humano:

- `OUVI-156` a `OUVI-162` ficaram 83 minutos em `SPECIFYING` esperando nove dúvidas de
  negócio. Nunca foram despachadas — zero arquivos em `runs/`.
- `OUVI-150`, `153` e `154` ficaram em `IMPLEMENTING` depois que os devs morreram.
- `SELL-78` estava em `TESTING` há **1241 minutos**, mais de vinte horas.

O `pendentes` não listava nenhuma: ele só olha `AWAITING_APPROVAL`,
`AWAITING_SPEC_APPROVAL` e `BLOCKED`. Estado de trabalho sem ninguém trabalhando é um
buraco — o board mostra andamento e ninguém é cobrado.

E três dos sete devs daquele dia nunca escreveram um byte: o `err.log` tinha uma linha
só, "Session <id> found but has no messages. Starting fresh.", e depois nada. Cada um
ficou os 45 minutos do timeout. 135 minutos de espera para zero trabalho.
"""
import io
import os
import subprocess
import tempfile
import time
import types
import unittest
from pathlib import Path

import yaml

from ambiente import REPO


def carregar(nome):
    with io.open(REPO / "bin" / nome, encoding="utf-8") as f:
        fonte = f.read()
    mod = types.ModuleType(nome)
    mod.__dict__["__name__"] = nome
    exec(compile(fonte.split("def main(")[0], nome, "exec"), mod.__dict__)
    return mod


class RodadaMuda(unittest.TestCase):
    """O teto de silencio existe, mas vem DESLIGADO — e a historia de por que.

    Eu liguei esse teto em 8 minutos olhando tres rodadas de 01/10 que ficaram 45 min com
    `out.md` em zero byte, e concluí que a sessao do kiro nao subia. Era conclusao errada
    sobre dado certo: o `out.md` so e escrito QUANDO A RODADA TERMINA. Nas quatro que
    deram certo no mesmo dia o mtime do arquivo cai nos ultimos segundos da rodada —
    OUVI-148 dev-back gravou 13:39:00 para um fim 13:39:12, e a OUVI-149 dev-front ficou
    44 minutos calada antes de escrever 15 KB de uma vez.

    Com o teto ligado eu matei a rodada da OUVI-149 as 14:56:06. Ela estava trabalhando:
    o jsonl da sessao do kiro tinha 351 KB e 58 entradas de Prompt/AssistantMessage/
    ToolResults, escritas ate 14:56:02 — quatro segundos antes. Teria matado as quatro
    boas tambem.

    Entao o mecanismo fica, desligado, e estes testes guardam as duas coisas: que ele nao
    dispara no padrao, e que se alguem religar com um sinal melhor ele ainda funciona.
    """

    def setUp(self):
        self.hd = carregar("hermes-delegar")
        d = Path(tempfile.mkdtemp())
        self.reg = {"saida": str(d / "s.out.md"), "erros": str(d / "s.err.log"),
                    "timeout_min": 45, "cmd": ["x"]}
        for k in ("saida", "erros"):
            Path(self.reg[k]).write_text("", encoding="utf-8")

    class Falso:
        """Processo que nunca termina, ou que termina na n-esima espera."""

        def __init__(self, termina_em=None, code=0):
            self.termina_em = termina_em
            self.code = code
            self.pid = 1
            self.esperas = 0

        def wait(self, timeout=None):
            self.esperas += 1
            if self.termina_em is not None and self.esperas >= self.termina_em:
                return self.code
            raise subprocess.TimeoutExpired("x", timeout)

    def test_vem_desligado(self):
        # O padrao e 0 e 0 quer dizer desligado — nao "mata na hora", que e o que um
        # `>= MUDO_MIN * 60` sem guarda faria.
        self.assertEqual(0, carregar("hermes-delegar").MUDO_MIN)

    def test_desligado_so_o_timeout_total_vale(self):
        self.hd.MUDO_MIN = 0
        self.reg["timeout_min"] = 0
        with self.assertRaises(subprocess.TimeoutExpired):
            self.hd.esperar(self.Falso(), self.reg)

    def test_desligado_nao_mata_rodada_calada_que_ainda_tem_prazo(self):
        # O caso real: 44 minutos de silencio e depois 15 KB de trabalho.
        self.hd.MUDO_MIN = 0
        p = self.Falso(termina_em=3)
        self.assertEqual(0, self.hd.esperar(p, self.reg))

    def test_processo_que_termina_devolve_o_codigo(self):
        self.assertEqual(0, self.hd.esperar(self.Falso(termina_em=2), self.reg))

    def test_ligado_dispara_no_silencio(self):
        self.hd.MUDO_MIN = 1.0 / 60          # um segundo, para nao depender de relogio
        with self.assertRaises(self.hd.Mudo):
            self.hd.esperar(self.Falso(), self.reg)

    def test_ligado_nao_mata_quem_escreve(self):
        self.hd.MUDO_MIN = 1.0 / 60
        p = self.Falso()
        passos = []

        def wait(timeout=None):
            passos.append(1)
            with io.open(self.reg["saida"], "a", encoding="utf-8") as f:
                f.write("linha\n")
            if len(passos) >= 4:
                return 0
            raise subprocess.TimeoutExpired("x", timeout)

        p.wait = wait
        self.assertEqual(0, self.hd.esperar(p, self.reg))

    def test_o_aviso_diz_que_a_sessao_nao_subiu(self):
        # Se alguem religar o teto, a mensagem tem de dizer a causa certa: "passou do
        # tempo" mandaria o humano procurar trabalho que nao existe.
        reg = dict(self.reg, status="mudo", projeto=str(Path(tempfile.mkdtemp())),
                   key="X-1", bot="dev-front", estado_antes="IMPLEMENTING",
                   estado_depois="IMPLEMENTING", exit=None)
        (Path(reg["projeto"]) / ".hermes").mkdir(parents=True, exist_ok=True)
        texto, _ = self.hd.aviso_final(reg, {})
        self.assertIn("nao escreveu nada", texto.replace("ão", "ao").replace("não", "nao"))


class Branch(unittest.TestCase):
    """`compartilhada` quer dizer UMA branch do time, e isso tem de ser codigo."""

    def setUp(self):
        self.ht = carregar("hermes-task")

    def test_os_seis_casos_reais_de_01_10(self):
        casos = [("OUVI-148", "compartilhada", "feature/ouvi-148-devolucao", True),
                 ("OUVI-149", "compartilhada", "develop", False),
                 ("OUVI-150", "compartilhada", "fix/ouvi-150-tipo-ativo", True),
                 ("OUVI-152", "compartilhada", None, True),
                 ("OUVI-153", "compartilhada", "develop", False),
                 ("OUVI-154", "compartilhada", "feature/ouvi-154-lista", True)]
        for key, est, nome, nega in casos:
            e = self.ht.conferir_branch(key, {"estrategia": est, "nome": nome})
            self.assertEqual(nega, e is not None, (key, est, nome, e))

    def test_por_tarefa_pode_ter_branch_propria(self):
        # A estrategia existe; o que nao pode e dizer uma e fazer a outra.
        self.assertIsNone(self.ht.conferir_branch(
            "OUVI-154", {"estrategia": "por-tarefa",
                         "nome": "feature/ouvi-154-lista"}))

    def test_sem_estrategia_nao_passa(self):
        self.assertIsNotNone(self.ht.conferir_branch("X-1", {"nome": "develop"}))
        self.assertIsNotNone(self.ht.conferir_branch("X-1", None))

    def test_a_mensagem_diz_a_causa_e_as_duas_saidas(self):
        e = self.ht.conferir_branch("OUVI-154", {"estrategia": "compartilhada",
                                                 "nome": "feature/ouvi-154-x"})
        self.assertIn("working tree", e)
        self.assertIn("por-tarefa", e)

    def test_nao_confunde_key_de_outra_tarefa_com_a_propria(self):
        # Branch do time que por acaso cite outra issue nao e branch desta tarefa.
        self.assertIsNone(self.ht.conferir_branch(
            "OUVI-154", {"estrategia": "compartilhada", "nome": "release/ouvi-900"}))


class Vagas(unittest.TestCase):
    """Sete devs de uma vez nao serve; o limite tem de estar no codigo."""

    def setUp(self):
        self.hd = carregar("hermes-delegar")
        self.root = Path(tempfile.mkdtemp()) / "acme"
        (self.root / ".hermes" / "runs").mkdir(parents=True)

    def lock(self, key, bot, pid):
        d = self.root / ".hermes" / "runs" / key
        d.mkdir(exist_ok=True)
        f = d / ("%s.lock" % bot)
        f.write_text(str(pid), encoding="utf-8")
        return f

    def test_conta_so_lock_de_processo_vivo(self):
        self.lock("A-1", "dev-front", os.getpid())
        self.lock("A-2", "dev-back", 999999999)
        self.assertEqual(1, self.hd.rodando_no_projeto(self.root))

    def test_a_propria_trava_nao_conta_contra_ela_mesma(self):
        minha = self.lock("A-1", "dev-front", os.getpid())
        self.assertEqual(0, self.hd.rodando_no_projeto(self.root, menos=minha))

    def test_com_vaga_sobrando_nao_espera(self):
        self.hd.VAGAS = 3
        self.lock("A-1", "dev-front", os.getpid())
        self.assertEqual(0, self.hd.esperar_vaga(self.root, None, limite_min=0))

    def test_cheio_desiste_de_esperar_em_vez_de_travar_para_sempre(self):
        # Lock que o vivo() nao consegue soltar derrubaria o projeto inteiro. Um bot a
        # mais e menos pior que nenhum bot nunca.
        self.hd.VAGAS = 1
        self.lock("A-1", "dev-front", os.getpid())
        self.assertEqual(0, self.hd.esperar_vaga(self.root, None, limite_min=0))

    def test_zero_desliga_o_limite(self):
        self.hd.VAGAS = 0
        for i in range(5):
            self.lock("A-%d" % i, "dev-front", os.getpid())
        self.assertEqual(0, self.hd.esperar_vaga(self.root, None, limite_min=0))

    def test_o_padrao_e_menor_que_os_sete_que_quebraram(self):
        hd = carregar("hermes-delegar")
        self.assertLess(hd.VAGAS, 7)
        self.assertGreater(hd.VAGAS, 1, "serializar nao e o pedido: o humano quer paralelo")


class TarefaSemNinguem(unittest.TestCase):
    """Estado de trabalho sem ninguém trabalhando tem de aparecer no `pendentes`."""

    def setUp(self):
        self.cd = carregar("call-dispatch")
        self.proj = Path(tempfile.mkdtemp()) / "acme"
        (self.proj / ".hermes" / "tasks").mkdir(parents=True)

    def tarefa(self, key, estado, minutos_atras=0, objetivo="obj"):
        d = self.proj / ".hermes" / "tasks" / key
        d.mkdir(exist_ok=True)
        mf = d / "manifest.yaml"
        mf.write_text(yaml.safe_dump({"task_id": key, "estado": estado,
                                      "objetivo": objetivo}), encoding="utf-8")
        if minutos_atras:
            quando = time.time() - minutos_atras * 60
            os.utime(mf, (quando, quando))
        return d

    def test_acha_a_que_esta_parada_em_estado_de_trabalho(self):
        self.tarefa("A-1", "SPECIFYING", minutos_atras=83)
        fora = self.cd._orfas(self.proj)
        self.assertEqual(1, len(fora))
        key, estado, quieta, _ = fora[0]
        self.assertEqual(("A-1", "SPECIFYING"), (key, estado))
        self.assertGreaterEqual(quieta, 83)

    def test_gate_e_blocked_nao_sao_orfas(self):
        # Esses dois o `pendentes` ja lista; contar de novo seria ruido.
        for estado in ("AWAITING_APPROVAL", "AWAITING_SPEC_APPROVAL", "BLOCKED",
                       "CLOSED", "MERGED"):
            self.tarefa("B-" + estado, estado, minutos_atras=999)
        self.assertEqual([], self.cd._orfas(self.proj))

    def test_rodada_recem_comecada_nao_e_orfa(self):
        # Rodada longa e normal; o que conta e nao ter ninguem E estar quieta.
        self.tarefa("C-1", "IMPLEMENTING", minutos_atras=2)
        self.assertEqual([], self.cd._orfas(self.proj))

    def test_lock_de_processo_vivo_protege_a_tarefa(self):
        d = self.tarefa("D-1", "IMPLEMENTING", minutos_atras=999)
        runs = self.proj / ".hermes" / "runs" / "D-1"
        runs.mkdir(parents=True)
        (runs / "dev-front.lock").write_text(str(os.getpid()), encoding="utf-8")
        self.assertEqual([], self.cd._orfas(self.proj), "pid vivo, nao e orfa")
        self.assertTrue(d.exists())

    def test_lock_orfao_nao_protege(self):
        # O supervisor apaga o lock ao morrer, mas nao sempre: pid morto com lock no
        # disco foi exatamente o estado da OUVI-154 as 14:00.
        self.tarefa("E-1", "IMPLEMENTING", minutos_atras=999)
        runs = self.proj / ".hermes" / "runs" / "E-1"
        runs.mkdir(parents=True)
        (runs / "dev-front.lock").write_text("999999999", encoding="utf-8")
        self.assertEqual(1, len(self.cd._orfas(self.proj)))

    def test_lock_ilegivel_nao_derruba_a_varredura(self):
        self.tarefa("F-1", "TESTING", minutos_atras=999)
        runs = self.proj / ".hermes" / "runs" / "F-1"
        runs.mkdir(parents=True)
        (runs / "qa.lock").write_text("nao e numero", encoding="utf-8")
        self.assertEqual(1, len(self.cd._orfas(self.proj)))

    def test_manifest_quebrado_nao_derruba_a_varredura(self):
        d = self.proj / ".hermes" / "tasks" / "G-1"
        d.mkdir()
        (d / "manifest.yaml").write_text("estado: [isto: nao: fecha", encoding="utf-8")
        self.tarefa("G-2", "SPECIFYING", minutos_atras=99)
        self.assertEqual(["G-2"], [o[0] for o in self.cd._orfas(self.proj)])

    def test_cobre_os_estados_que_prenderam_de_verdade(self):
        for e in ("SPECIFYING", "IMPLEMENTING", "TESTING"):
            self.assertIn(e, self.cd.EM_TRABALHO, e)


if __name__ == "__main__":
    unittest.main()
