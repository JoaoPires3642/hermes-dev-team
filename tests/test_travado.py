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
import datetime as dt
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


class RodadaParada(unittest.TestCase):
    """Rodada parada x rodada lenta: o sinal e a sessao do kiro, nao o `out.md`.

    A primeira versao disto olhava `out.md` e matava rodada boa. `out.md` so e escrito
    QUANDO A RODADA TERMINA: nas quatro que deram certo em 01/10 o mtime cai nos ultimos
    segundos (OUVI-148 dev-back gravou 13:39:00 para um fim 13:39:12), e a OUVI-149
    dev-front ficou 44 minutos calada antes de escrever 15 KB de uma vez. Com um teto de
    8 min sobre esse arquivo eu matei a OUVI-149 as 14:56:06, quando a sessao do kiro
    dela tinha 351 KB escritos ate 14:56:02.

    O jsonl do kiro cresce turno a turno. As quatro rodadas que morreram naquele dia
    tinham a sessao escrita de 3 a 22 segundos antes do kill — nenhuma estava travada.
    """

    def setUp(self):
        self.hd = carregar("hermes-delegar")
        self.kiro = Path(tempfile.mkdtemp())
        self.hd._dir_kiro = lambda: self.kiro
        d = Path(tempfile.mkdtemp())
        self.reg = {"saida": str(d / "s.out.md"), "erros": str(d / "s.err.log"),
                    "timeout_min": 45, "cmd": ["x"], "rodada": "20261001-144745-dev-front",
                    "inicio": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
        for k in ("saida", "erros"):
            Path(self.reg[k]).write_text("", encoding="utf-8")

    def sessao(self, nome, primeira_linha, corpo=""):
        f = self.kiro / (nome + ".jsonl")
        f.write_text(primeira_linha + "\n" + corpo, encoding="utf-8")
        return f

    class Falso:
        def __init__(self, termina_em=None, code=0):
            self.termina_em, self.code, self.pid, self.esperas = termina_em, code, 1, 0

        def wait(self, timeout=None):
            self.esperas += 1
            if self.termina_em is not None and self.esperas >= self.termina_em:
                return self.code
            raise subprocess.TimeoutExpired("x", timeout)

    # ------------------------------------------------------------ achar a sessao
    def test_acha_pelo_id_da_rodada_que_vai_no_prompt(self):
        self.sessao("aaa", '{"kind":"Prompt","data":"... 20261001-144745-dev-front ..."}')
        f = self.hd.achar_sessao_kiro("20261001-144745-dev-front", time.time() - 60)
        self.assertIsNotNone(f)
        self.assertEqual("aaa.jsonl", f.name)

    def test_nao_confunde_sessao_de_outra_rodada(self):
        # Em 01/10 a sessao c2bd9aaf citava OUVI-148, 149 e 154 no mesmo prompt: a KEY
        # nao distingue, o id da rodada sim.
        self.sessao("outra", '{"kind":"Prompt","data":"OUVI-149 OUVI-148 OUVI-154"}')
        self.assertIsNone(self.hd.achar_sessao_kiro("20261001-144745-dev-front",
                                                    time.time() - 60))

    def test_ignora_sessao_anterior_a_rodada(self):
        # Sessao de rodada anterior com o mesmo id (retry) nao pode ser confundida com a
        # desta. `os.utime` nao mexe no creation time no Windows, entao o teste anda o
        # outro lado: pergunta por uma rodada que comecou DEPOIS do arquivo existir.
        self.sessao("velha", '{"kind":"Prompt","data":"20261001-144745-dev-front"}')
        self.assertIsNone(self.hd.achar_sessao_kiro("20261001-144745-dev-front",
                                                    time.time() + 60))

    def test_sem_diretorio_do_kiro_nao_quebra(self):
        self.hd._dir_kiro = lambda: Path(tempfile.mkdtemp()) / "nao-existe"
        self.assertIsNone(self.hd.achar_sessao_kiro("x", time.time()))

    # ------------------------------------------------------------ o teto
    def test_sessao_que_cresce_nao_e_morta(self):
        # O caso que eu matei: 351 KB em 8 minutos. Ritmo nao e parada.
        self.hd.SEM_PROGRESSO_MIN = 1.0 / 60
        f = self.sessao("viva", '{"kind":"Prompt","data":"20261001-144745-dev-front"}')
        p = self.Falso()
        passos = []

        def wait(timeout=None):
            passos.append(1)
            with open(f, "a", encoding="utf-8") as fh:
                fh.write('{"kind":"ToolResults"}\n')
            if len(passos) >= 4:
                return 0
            raise subprocess.TimeoutExpired("x", timeout)

        p.wait = wait
        self.assertEqual(0, self.hd.esperar(p, self.reg))

    def test_sessao_que_para_de_crescer_morre(self):
        self.hd.SEM_PROGRESSO_MIN = 1.0 / 60
        self.sessao("parada", '{"kind":"Prompt","data":"20261001-144745-dev-front"}')
        with self.assertRaises(self.hd.SemProgresso):
            self.hd.esperar(self.Falso(), self.reg)

    def test_bot_sem_kiro_nao_e_julgado_por_silencio(self):
        # Provider anthropic nao tem sessao de kiro. Chutar silencio como morte foi
        # exatamente o erro que isto corrige: aqui so o timeout total decide.
        self.hd.SEM_PROGRESSO_MIN = 1.0 / 60
        self.reg["timeout_min"] = 0
        with self.assertRaises(subprocess.TimeoutExpired):
            self.hd.esperar(self.Falso(), self.reg)

    def test_timeout_total_continua_valendo_para_quem_progride_sem_fim(self):
        self.hd.SEM_PROGRESSO_MIN = 999
        self.reg["timeout_min"] = 0
        self.sessao("eterna", '{"kind":"Prompt","data":"20261001-144745-dev-front"}')
        with self.assertRaises(subprocess.TimeoutExpired):
            self.hd.esperar(self.Falso(), self.reg)

    def test_processo_que_termina_devolve_o_codigo(self):
        self.assertEqual(0, self.hd.esperar(self.Falso(termina_em=2), self.reg))

    def test_registro_guarda_a_sessao_e_o_tamanho(self):
        # Para o aviso poder dizer "morta com N KB" em vez de so "morta".
        self.hd.SEM_PROGRESSO_MIN = 1.0 / 60
        self.sessao("marcada", '{"kind":"Prompt","data":"20261001-144745-dev-front"}',
                    corpo='{"kind":"ToolResults"}\n' * 20)
        with self.assertRaises(self.hd.SemProgresso):
            self.hd.esperar(self.Falso(), self.reg)
        self.assertIn("marcada.jsonl", self.reg.get("sessao_kiro", ""))
        self.assertGreater(self.reg.get("kiro_bytes", 0), 0)

    def test_o_aviso_diz_que_parou_de_progredir(self):
        reg = dict(self.reg, status="parado", projeto=str(Path(tempfile.mkdtemp())),
                   key="X-1", bot="dev-front", estado_antes="IMPLEMENTING",
                   estado_depois="IMPLEMENTING", exit=None)
        (Path(reg["projeto"]) / ".hermes").mkdir(parents=True, exist_ok=True)
        texto, _ = self.hd.aviso_final(reg, {})
        self.assertIn("parou de progredir", texto)
        self.assertNotIn("passou do tempo", texto)

    def test_grava_a_sessao_no_disco_ao_achar_nao_so_no_fim(self):
        # Sem isto o campo aparece no .json apenas quando a rodada termina, e quem olha
        # uma rodada VIVA le "ainda nao achou" sem saber se o mecanismo falhou ou se e
        # falta de persistencia. Eu cai nisso dez minutos depois de escrever o codigo.
        self.hd.SEM_PROGRESSO_MIN = 1.0 / 60
        self.sessao("gravada", '{"kind":"Prompt","data":"20261001-144745-dev-front"}')
        arq = Path(tempfile.mkdtemp()) / "run.json"
        arq.write_text("{}", encoding="utf-8")
        with self.assertRaises(self.hd.SemProgresso):
            self.hd.esperar(self.Falso(), self.reg, arq)
        import json
        gravado = json.loads(arq.read_text(encoding="utf-8"))
        self.assertIn("gravada.jsonl", gravado.get("sessao_kiro", ""))

    def test_o_aviso_diz_quanto_trabalho_havia(self):
        # Rodada morta sem isto e indistinguivel de rodada que nunca comecou, porque o
        # `out.md` so nasce no fim. Foi o que me fez diagnosticar "a sessao nao subiu".
        reg = dict(self.reg, status="timeout", projeto=str(Path(tempfile.mkdtemp())),
                   key="X-1", bot="dev-front", estado_antes="IMPLEMENTING",
                   estado_depois="IMPLEMENTING", exit=None,
                   kiro_bytes=521465, sessao_kiro=str(self.kiro / "ac95c67b.jsonl"))
        (Path(reg["projeto"]) / ".hermes").mkdir(parents=True, exist_ok=True)
        texto, _ = self.hd.aviso_final(reg, {})
        self.assertIn("ESTAVA trabalhando", texto)
        self.assertIn("509 KB", texto)
        self.assertIn("ac95c67b", texto)

    def test_aviso_sem_sessao_do_kiro_nao_inventa_evidencia(self):
        reg = dict(self.reg, status="timeout", projeto=str(Path(tempfile.mkdtemp())),
                   key="X-1", bot="po", estado_antes="TRIAGED", estado_depois="TRIAGED",
                   exit=None)
        (Path(reg["projeto"]) / ".hermes").mkdir(parents=True, exist_ok=True)
        texto, _ = self.hd.aviso_final(reg, {})
        self.assertNotIn("ESTAVA trabalhando", texto)

    def test_o_prompt_carrega_o_id_da_rodada(self):
        # Sem isso o supervisor nao reencontra a sessao.
        self.assertIn("{rodada}", self.hd.PROMPT)

    def test_timeout_total_nao_e_mais_45(self):
        # 45 cortou tres rodadas em trabalho; as que couberam levaram 28, 29 e 44 min.
        self.assertGreater(carregar("hermes-delegar").TIMEOUT_PADRAO, 45)


class DevCalado(unittest.TestCase):
    """Dev que termina sem mover e sem entregar nao pode sair calado.

    Dev ficou fora do `DEVE_MOVER` por um motivo bom: `IMPLEMENTING -> TESTING` so
    acontece quando TODOS os devs da tarefa entregaram, entao quem entrega primeiro para
    em IMPLEMENTING legitimamente. Mas a ausencia do aviso cobria tambem o caso oposto:
    em 01/10 o @dev-back da OUVI-150 trabalhou 8 minutos, escreveu "18 montador tests
    green, build green" no resumo, e terminou com `handoffs_dev: []` e a tarefa em
    IMPLEMENTING. Nenhum aviso saiu.

    `handoffs_dev` distingue: tem o meu nome -> entreguei e espero; nao tem -> nao disse
    nada a ninguem.
    """

    def setUp(self):
        self.hd = carregar("hermes-delegar")
        self.raiz = Path(tempfile.mkdtemp())
        (self.raiz / ".hermes").mkdir()
        (self.raiz / "o.md").write_text("Resumo:\nfiz o trabalho\n", encoding="utf-8")
        (self.raiz / "e.log").write_text("", encoding="utf-8")

    def aviso(self, bot, antes, depois, handoffs):
        reg = {"projeto": str(self.raiz), "key": "X-1", "status": "ok", "exit": 0,
               "saida": str(self.raiz / "o.md"), "erros": str(self.raiz / "e.log"),
               "bot": bot, "estado_antes": antes, "estado_depois": depois}
        texto, _ = self.hd.aviso_final(reg, {"handoffs_dev": handoffs,
                                             "estado": depois})
        return "terminou sem mover" in (texto or "")

    def test_dev_que_nao_entregou_nem_moveu_avisa(self):
        self.assertTrue(self.aviso("dev-back", "IMPLEMENTING", "IMPLEMENTING", []))

    def test_dev_que_entregou_e_espera_o_colega_fica_calado(self):
        # Caso legitimo: `IMPLEMENTING -> TESTING` exige os dois devs.
        self.assertFalse(self.aviso("dev-back", "IMPLEMENTING", "IMPLEMENTING",
                                    ["dev-back"]))

    def test_dev_que_moveu_nao_recebe_aviso_de_imobilidade(self):
        self.assertFalse(self.aviso("dev-back", "IMPLEMENTING", "TESTING", []))

    def test_quem_ja_era_cobrado_continua_cobrado(self):
        self.assertTrue(self.aviso("qa", "TESTING", "TESTING", []))
        self.assertTrue(self.aviso("techlead", "SPECIFYING", "SPECIFYING", []))


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
