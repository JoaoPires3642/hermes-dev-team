"""Testes do fluxo call → gates → bots, sem Hermes, Telegram nem modelo de verdade.

    python3 -m unittest discover -s tests -v

Cada teste monta um Ambiente isolado (tests/ambiente.py). Os bugs que estes testes
cobrem já aconteceram de verdade nesta base — o comentário de cada um diz qual.
"""
import importlib.util
import json
import os
import shutil
import sys
import time
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ambiente import REPO, UID, VIA, Ambiente  # noqa: E402


class Base(unittest.TestCase):
    def setUp(self):
        self.a = Ambiente()

    def tearDown(self):
        self.a.limpar()

    def ok(self, r):
        self.assertEqual(r.returncode, 0, f"stdout={r.stdout}\nstderr={r.stderr}")
        return r

    def negado(self, r, trecho):
        self.assertNotEqual(r.returncode, 0, f"devia ter sido negado: {r.stdout}{r.stderr}")
        self.assertIn(trecho, r.stdout + r.stderr)
        return r

    def triar_call(self, cliente="acme"):
        """call nova → /cliente → orquestrador (resumo) → po (proposta) → GATE 1."""
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))
        self.a.acoes(orquestrador=[("TRIAGED", "resumo")], po=[("AWAITING_APPROVAL", "proposta")])
        # o orquestrador falso não chama o po sozinho: o teste faz o papel dele
        self.ok(self.a.dispatch("cliente", "CALL-1", cliente, "--via", VIA))
        proj = self.a.projetos / cliente
        self.a.esperar_rodadas(proj)
        h = proj / ".hermes" / "tasks" / "CALL-1" / "handoffs" / "01-orquestrador-para-po.md"
        h.write_text("resumo pronto", encoding="utf-8")
        self.ok(self.a.delegar("po", str(proj), "CALL-1", str(h), "--esperar"))
        self.assertEqual(self.a.estado(proj, "CALL-1"), "AWAITING_APPROVAL")
        return proj


# ====================================================================== call-dispatch
class TestVarrer(Base):
    def test_registra_call_e_pergunta_com_toques(self):
        self.a.novo_projeto("Acme Corp")
        self.a.nova_nota(titulo="Relatório de vendas")
        r = self.ok(self.a.dispatch("varrer"))
        self.assertIn("CALL-1", r.stdout)
        texto = self.a.envios()[0]["texto"]
        for toque in ("/cliente_CALL_1_acme", "/cliente_CALL_1_acme_corp", "/novo_CALL_1", "/ignorar_CALL_1"):
            self.assertIn(toque, texto)
        self.assertEqual(self.a.call("CALL-1")["estado"], "AGUARDANDO_CLIENTE")

    def test_nao_duplica_a_mesma_nota(self):
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))
        self.ok(self.a.dispatch("varrer"))
        self.assertEqual(len(list((self.a.calls / ".dispatch").glob("CALL-*.json"))), 1)
        self.assertEqual(len(self.a.envios()), 1)

    def test_reenvia_pergunta_que_nao_chegou(self):
        # CALL-6: um "Timed out" isolado do Telegram engoliu a pergunta, sem nova tentativa
        self.a.falhar_envios(3)          # as 3 tentativas da 1ª rodada falham
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))
        self.assertFalse(self.a.call("CALL-1")["avisada"])
        self.ok(self.a.dispatch("varrer"))   # próxima rodada do job reenvia
        self.assertTrue(self.a.call("CALL-1")["avisada"])
        self.assertEqual(len(self.a.envios()), 1)

    def test_nova_tentativa_dentro_do_mesmo_envio(self):
        self.a.falhar_envios(1)
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))
        self.assertTrue(self.a.call("CALL-1")["avisada"])


class TestVia(Base):
    def setUp(self):
        super().setUp()
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))

    def test_usuario_nao_autorizado(self):
        self.negado(self.a.dispatch("cliente", "CALL-1", "acme", "--via", "telegram:999:1"),
                    "não está em TELEGRAM_ALLOWED_USERS")

    def test_so_vale_pelo_telegram(self):
        self.negado(self.a.dispatch("cliente", "CALL-1", "acme", "--via", f"desktop:{UID}:1"),
                    "só vale vinda do Telegram")

    def test_ignorar(self):
        self.ok(self.a.dispatch("ignorar", "CALL-1", "--via", VIA))
        self.assertEqual(self.a.call("CALL-1")["estado"], "IGNORADA")
        self.assertEqual(self.a.chats(), [])   # nada rodou


class TestCliente(Base):
    def setUp(self):
        super().setUp()
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))

    def test_projeto_inexistente_lista_os_que_existem(self):
        r = self.negado(self.a.dispatch("cliente", "CALL-1", "beta", "--via", VIA), "Existem: acme")
        self.assertIn("não há projeto", r.stdout)

    def test_nome_do_toque_casa_com_nome_com_espaco(self):
        proj = self.a.novo_projeto("Acme Corp")
        self.ok(self.a.dispatch("cliente", "CALL-1", "acme_corp", "--via", VIA))
        self.assertTrue((proj / ".hermes" / "tasks" / "CALL-1" / "manifest.yaml").is_file())

    def test_dispara_orquestrador_em_sessao_da_call_na_pasta_do_cliente(self):
        self.ok(self.a.dispatch("cliente", "CALL-1", "acme", "--via", VIA))
        self.a.esperar_rodadas(self.a.acme)
        chat = self.a.chats()[0]
        self.assertEqual((chat["perfil"], chat["sessao"], chat["projeto"]),
                         ("orquestrador", "CALL-1-orquestrador", str(self.a.acme)))
        self.assertIn("Não quebre em story/task", chat["query"])   # a quebra é do @po
        self.assertEqual(self.a.call("CALL-1")["estado"], "NO_PROJETO")

    def test_nova_tentativa_reaproveita_tarefa_que_nao_rodou(self):
        # disparo falhou depois de criar a tarefa: tentar de novo não pode travar em "já existe"
        self.a.env["PATH"] = self.a.env["PATH"].replace(str(self.a.bin), str(self.a.raiz / "sem-bin"))
        shutil.move(self.a.bin / "hermes-delegar", self.a.raiz / "hd")
        self.assertNotEqual(self.a.dispatch("cliente", "CALL-1", "acme", "--via", VIA).returncode, 0)
        shutil.move(self.a.raiz / "hd", self.a.bin / "hermes-delegar")
        self.a.env["PATH"] = self.a.env["PATH"].replace(str(self.a.raiz / "sem-bin"), str(self.a.bin))
        self.ok(self.a.dispatch("cliente", "CALL-1", "acme", "--via", VIA))


class TestNovo(Base):
    def setUp(self):
        super().setUp()
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))

    def test_nome_invalido(self):
        self.negado(self.a.dispatch("novo", "CALL-1", "--via", VIA, "--", "../fora"), "nome inválido")

    def test_parecido_com_existente_devolve_o_link(self):
        self.negado(self.a.dispatch("novo", "CALL-1", "--via", VIA, "--", "ACME"), "/cliente_CALL_1_acme")

    def test_cria_pasta_marcada_e_aprovar_espera_configurar(self):
        self.a.acoes(orquestrador=[("TRIAGED", "resumo")], po=[("AWAITING_APPROVAL", "proposta")])
        self.ok(self.a.dispatch("novo", "CALL-1", "--via", VIA, "--", "Padaria Silva"))
        proj = self.a.projetos / "Padaria Silva"
        self.assertIn("projeto novo, a preencher", (proj / "AGENTS.md").read_text())
        self.a.esperar_rodadas(proj)
        h = proj / ".hermes" / "tasks" / "CALL-1" / "handoffs" / "01-orquestrador-para-po.md"
        h.write_text("x")
        self.ok(self.a.delegar("po", str(proj), "CALL-1", str(h), "--esperar"))
        gate = next(e["texto"] for e in self.a.envios() if e["texto"].startswith("🚦 GATE 1"))
        self.assertIn("Projeto novo", gate)
        self.negado(self.a.dispatch("aprovar", "CALL-1", "--via", VIA), "ainda não está pronto")
        agents = proj / "AGENTS.md"
        agents.write_text(agents.read_text().replace("<!-- hermes: projeto novo, a preencher -->\n", ""))
        (proj / ".hermes" / "tuple.env").write_text("TUPLE_API_KEY=x\nTUPLE_WORKSPACE_ID=y\n")
        self.ok(self.a.dispatch("aprovar", "CALL-1", "--via", VIA))
        self.assertEqual(self.a.estado(proj, "CALL-1"), "SPECIFYING")


class TestGates(Base):
    def test_gate1_chega_com_toques_e_proposta_anexada(self):
        self.triar_call()
        textos = [e["texto"] for e in self.a.envios()]
        gate = next(t for t in textos if t.startswith("🚦 GATE 1"))
        for toque in ("/aprovar_CALL_1", "/ajustar_CALL_1", "/rejeitar_CALL_1"):
            self.assertIn(toque, gate)
        self.assertTrue(any(t.startswith("MEDIA:") and t.endswith("proposta.md") for t in textos))

    def test_aprovar_registra_humano_e_chama_pm(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("aprovar", "CALL-1", "--via", VIA))
        m = self.a.manifest(proj, "CALL-1")
        self.assertEqual(m["estado"], "SPECIFYING")
        self.assertEqual(m["aprovacoes"]["gate1"]["via"], VIA)
        self.a.esperar_rodadas(proj)
        self.assertEqual(self.a.chats()[-1]["perfil"], "pm")

    def test_aprovar_repetido_retoma_disparo_que_falhou(self):
        # o gate foi registrado mas o @pm nunca rodou: o 2º /aprovar tem que retomar
        proj = self.triar_call()
        (self.a.home / "profiles" / "pm" / "config.yaml").write_text("model:\n  provider: kiro-acp\n")
        if shutil.which("kiro-cli", path=self.a.env["PATH"]):
            self.skipTest("kiro-cli instalado nesta máquina")
        r = self.negado(self.a.dispatch("aprovar", "CALL-1", "--via", VIA), "registrado, mas o disparo")
        self.assertIn("/aprovar_CALL_1", r.stdout)
        (self.a.home / "profiles" / "pm" / "config.yaml").write_text("model:\n  provider: anthropic\n")
        r = self.ok(self.a.dispatch("aprovar", "CALL-1", "--via", VIA))
        self.assertIn("retomado", r.stdout)
        self.a.esperar_rodadas(proj)
        self.negado(self.a.dispatch("aprovar", "CALL-1", "--via", VIA), "não há gate")

    def test_ajustar_vai_para_o_po_por_padrao(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "tira a busca"))
        self.assertEqual(self.a.estado(proj, "CALL-1"), "TRIAGED")
        self.a.esperar_rodadas(proj)
        self.assertEqual(self.a.chats()[-1]["perfil"], "po")
        self.assertIn("tira a busca", self.a.chats()[-1]["query"])

    def test_ajustar_com_prefixo_vai_para_o_orquestrador(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "orquestrador: o cliente é outro"))
        self.a.esperar_rodadas(proj)
        chat = self.a.chats()[-1]
        self.assertEqual(chat["perfil"], "orquestrador")
        self.assertIn("o cliente é outro", chat["query"])
        self.assertNotIn("orquestrador: o cliente", chat["query"])

    def test_ajuste_tem_limite(self):
        proj = self.triar_call()
        for _ in range(3):   # cada ajuste volta ao @po, que refaz e move de novo para o gate
            self.ok(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "de novo"))
            self.a.esperar_rodadas(proj)
            self.assertEqual(self.a.estado(proj, "CALL-1"), "AWAITING_APPROVAL")
        self.negado(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "mais"), "Decida")

    def test_rejeitar_encerra(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("rejeitar", "CALL-1", "--via", VIA, "--", "não vamos fazer"))
        self.assertEqual(self.a.estado(proj, "CALL-1"), "CLOSED")


# ====================================================================== hermes-task
class TestHermesTask(Base):
    def nova(self, key, estado=None):
        self.ok(self.a.task("new", str(self.a.acme), key, "--objetivo", "t", "--agentes", "pm,po"))
        if estado:
            mf = self.a.acme / ".hermes" / "tasks" / key / "manifest.yaml"
            mf.write_text(mf.read_text().replace("estado: RECEIVED", f"estado: {estado}"))

    def test_proposta_do_gate1_so_pelo_po(self):
        self.nova("CALL-1", "TRIAGED")
        arq = self.a.acme / "AGENTS.md"
        self.negado(self.a.task("move", str(self.a.acme), "CALL-1", "AWAITING_APPROVAL",
                                "--by", "orquestrador", "--ev", f"proposta={arq}"), "quem pode: po")
        self.ok(self.a.task("move", str(self.a.acme), "CALL-1", "AWAITING_APPROVAL",
                            "--by", "po", "--ev", f"proposta={arq}"))

    def test_herda_gate1_so_de_call_aprovada(self):
        self.nova("CALL-1", "TRIAGED")
        self.negado(self.a.task("new", str(self.a.acme), "ACME-1", "--objetivo", "t", "--agentes",
                                "dev-back", "--herda-gate1", "CALL-1"), "não tem GATE 1")

    def test_herda_gate1_nasce_em_specifying(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("aprovar", "CALL-1", "--via", VIA))
        self.ok(self.a.task("new", str(proj), "ACME-1", "--objetivo", "t", "--agentes", "dev-back",
                            "--herda-gate1", "CALL-1"))
        m = self.a.manifest(proj, "ACME-1")
        self.assertEqual(m["estado"], "SPECIFYING")
        self.assertEqual(m["aprovacoes"]["gate1"]["herdado_de"], "CALL-1")

    def test_fechar_so_call_e_so_pelo_po(self):
        self.nova("CALL-9", "SPECIFYING")
        self.nova("ACME-9", "SPECIFYING")
        self.negado(self.a.task("move", str(self.a.acme), "ACME-9", "CLOSED", "--by", "po",
                                "--ev", "issues=X"), "só a tarefa de uma call")
        self.negado(self.a.task("move", str(self.a.acme), "CALL-9", "CLOSED", "--by", "pm",
                                "--ev", "issues=X"), "quem pode: po")
        r = self.ok(self.a.task("move", str(self.a.acme), "CALL-9", "CLOSED", "--by", "po", "--ev", "issues=X"))
        self.assertIn("não existe no TUPLE", r.stdout)


# ====================================================================== hermes-delegar
class TestDelegar(Base):
    def setUp(self):
        super().setUp()
        self.ok(self.a.task("new", str(self.a.acme), "ACME-1", "--objetivo", "t", "--agentes", "dev-back"))
        self.h = self.a.acme / ".hermes" / "tasks" / "ACME-1" / "handoffs" / "01-x.md"
        self.h.write_text("handoff")

    def test_fora_da_vez_do_bot(self):
        self.negado(self.a.delegar("dev-back", str(self.a.acme), "ACME-1", str(self.h)), "não entra em ACME-1")

    def test_handoff_fora_da_pasta_da_tarefa(self):
        fora = self.a.raiz / "h.md"
        fora.write_text("x")
        self.negado(self.a.delegar("orquestrador", str(self.a.acme), "ACME-1", str(fora)), "handoff tem que existir")

    def test_projeto_fora_de_hermes_projetos(self):
        outro = self.a.raiz / "outro"
        (outro / ".hermes").mkdir(parents=True)
        (outro / "AGENTS.md").write_text("x")
        self.negado(self.a.delegar("orquestrador", str(outro), "ACME-1", str(self.h)), "fora de $HERMES_PROJETOS")

    def test_bot_desconhecido(self):
        self.negado(self.a.delegar("mallory", str(self.a.acme), "ACME-1", str(self.h)), "bot desconhecido")

    def test_ja_rodando(self):
        runs = self.a.acme / ".hermes" / "runs" / "ACME-1"
        runs.mkdir(parents=True)
        (runs / "orquestrador.lock").write_text(str(os.getpid()))     # processo vivo
        r = self.a.delegar("orquestrador", str(self.a.acme), "ACME-1", str(self.h))
        self.assertEqual(r.returncode, 4, r.stderr)

    def test_kiro_ausente_recusa_na_hora_com_um_aviso_so(self):
        if shutil.which("kiro-cli", path=self.a.env["PATH"]):
            self.skipTest("kiro-cli instalado nesta máquina")
        for key in ("ACME-2", "ACME-3"):
            self.ok(self.a.task("new", str(self.a.acme), key, "--objetivo", "t", "--agentes", "dev-back"))
            mf = self.a.acme / ".hermes" / "tasks" / key / "manifest.yaml"
            mf.write_text(mf.read_text().replace("estado: RECEIVED", "estado: SPECIFYING"))
            h = mf.parent / "handoffs" / "01.md"
            h.write_text("x")
            self.negado(self.a.delegar("techlead", str(self.a.acme), key, str(h)), "kiro-cli")
        self.assertEqual(len(self.a.envios()), 1)
        self.assertEqual(self.a.chats(), [])

    def test_falhas_iguais_viram_um_aviso(self):
        # o teste da Clínica Vida mandou 5 avisos idênticos, um por issue
        self.a.chat_sai_com(1)
        for key in ("ACME-2", "ACME-3", "ACME-4"):
            self.ok(self.a.task("new", str(self.a.acme), key, "--objetivo", "t", "--agentes", "dev-back"))
            h = self.a.acme / ".hermes" / "tasks" / key / "handoffs" / "01.md"
            h.write_text("x")
            self.a.delegar("orquestrador", str(self.a.acme), key, str(h), "--esperar")
        falhas = [e for e in self.a.envios() if e["texto"].startswith("❌")]
        self.assertEqual(len(falhas), 1)

    def test_terminar_sem_mover_avisa(self):
        self.a.delegar("orquestrador", str(self.a.acme), "ACME-1", str(self.h), "--esperar")
        self.assertIn("terminou sem mover", self.a.envios()[-1]["texto"])

    def test_rodada_perdida_e_reconciliada(self):
        runs = self.a.acme / ".hermes" / "runs" / "ACME-1"
        runs.mkdir(parents=True)
        f = runs / "20260101-000000-po.json"
        f.write_text(json.dumps({"bot": "po", "projeto": str(self.a.acme), "key": "ACME-1", "status": "rodando",
                                 "supervisor_pid": 999999, "estado_antes": "SPECIFYING", "estado_depois": None,
                                 "criado": "2026-01-01T00:00:00-03:00", "trava": str(runs / "po.lock"),
                                 "saida": os.devnull, "erros": os.devnull}))
        self.ok(self.a.delegar("reconciliar"))
        self.assertEqual(json.loads(f.read_text())["status"], "perdida")
        self.assertIn("morreu sem terminar", self.a.envios()[-1]["texto"])
        self.ok(self.a.delegar("reconciliar"))
        self.assertEqual(len(self.a.envios()), 1)


# ====================================================================== plugin hermes-gates
class TestPlugin(Base):
    def setUp(self):
        super().setUp()
        spec = importlib.util.spec_from_file_location("hermes_gates", REPO / "plugins" / "hermes-gates" / "__init__.py")
        self.g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.g)
        self.pend = self.a.raiz / "pendente.json"
        self.g._arq_pendente = lambda: self.pend
        # o gateway entrega a identidade por get_session_env; aqui ela é fixa
        self.sessao = {"HERMES_SESSION_PLATFORM": "telegram", "HERMES_SESSION_USER_ID": UID,
                       "HERMES_SESSION_MESSAGE_ID": "7"}
        mod = types.ModuleType("gateway.session_context")
        mod.get_session_env = lambda nome, padrao="": self.sessao.get(nome, padrao)
        sys.modules["gateway"] = types.ModuleType("gateway")
        sys.modules["gateway.session_context"] = mod
        self.g._dispatch = lambda: [sys.executable, str(self.a.bin / "call-dispatch")]
        self._env = dict(os.environ)
        os.environ.update(self.a.env)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        for m in ("gateway", "gateway.session_context"):
            sys.modules.pop(m, None)
        super().tearDown()

    def test_toques_traduzidos(self):
        casos = {
            "/aprovar_CALL_1": "/aprovar CALL-1",
            "/aprovar_STORY_1_1@meu_bot": "/aprovar STORY-1-1",
            "/cliente_CALL_12_acme_corp": "/cliente CALL-12 acme_corp",
            "/ignorar_CALL_3": "/ignorar CALL-3",
            "/novo_CALL_4": "/novo CALL-4",
            "/aprovar CALL-1": None,
            "oi": None,
        }
        for entrada, esperado in casos.items():
            self.assertEqual(self.g._traduzir(entrada, UID), esperado, entrada)

    def test_hook_so_reescreve_no_telegram(self):
        class Fonte:
            user_id = UID
            platform = type("P", (), {"value": "telegram"})()
        evento = type("E", (), {"text": "/aprovar_CALL_1", "source": Fonte()})()
        self.assertEqual(self.g._hook(event=evento), {"action": "rewrite", "text": "/aprovar CALL-1"})
        Fonte.platform = type("P", (), {"value": "discord"})()
        self.assertIsNone(self.g._hook(event=evento))

    def test_ajuste_pendente_so_do_dono_uma_vez(self):
        r = self.g._fazer("ajustar")("CALL-1")
        self.assertIn("próxima mensagem", r)
        self.assertIsNone(self.g._traduzir("tira a busca", "999"))
        self.assertEqual(self.g._traduzir("tira a busca", UID), "/ajustar CALL-1 tira a busca")
        self.assertIsNone(self.g._traduzir("de novo", UID))

    def test_pendente_expira(self):
        self.g._gravar_pendentes({UID: {"cmd": "ajustar", "key": "CALL-1", "ate": time.time() - 1}})
        self.assertIsNone(self.g._traduzir("atrasado", UID))

    def test_comando_chega_ao_dispatch_com_prova(self):
        self.a.nova_nota()
        self.ok(self.a.dispatch("varrer"))
        r = self.g._fazer("ignorar")("CALL-1")
        self.assertIn("ignorada", r)
        self.assertEqual(self.a.call("CALL-1")["ignorada_via"], f"telegram:{UID}:7")

    def test_fora_do_telegram_nao_vale(self):
        self.sessao["HERMES_SESSION_PLATFORM"] = "desktop"
        self.assertIn("só vale pelo Telegram", self.g._fazer("aprovar")("CALL-1"))


# ====================================================================== resumo-do-dia
class TestResumo(Base):
    def test_fatos_trazem_commits_e_ignoram_cliente_parado(self):
        self.a.repo_com_commits(self.a.acme, "feat: bloqueia CPF duplicado", "fix: busca mais rápida")
        self.a.novo_projeto("parado")
        r = self.ok(self.a.resumo("--so-fatos"))
        self.assertIn("bloqueia CPF duplicado", r.stdout)
        self.assertNotIn("parado", r.stdout)
        self.assertEqual(self.a.chats(), [])          # --so-fatos não chama modelo

    def test_uma_rodada_por_cliente_em_sessao_propria(self):
        self.a.repo_com_commits(self.a.acme, "feat: relatório")
        outro = self.a.novo_projeto("beta")
        self.a.repo_com_commits(outro, "feat: agenda")
        self.ok(self.a.resumo())
        chats = self.a.chats()
        self.assertEqual({c["projeto"] for c in chats}, {str(self.a.acme), str(outro)})
        self.assertTrue(all(c["perfil"] == "pm" and c["sessao"].startswith("daily-") for c in chats))
        self.assertNotIn("agenda", next(c for c in chats if c["projeto"] == str(self.a.acme))["query"])
        self.assertEqual(len(self.a.envios()), 2)

    def test_so_pendencia_sai_sem_modelo_e_com_o_toque(self):
        proj = self.triar_call()                    # CALL-1 esperando o GATE 1
        antes = len(self.a.chats())
        (proj / ".hermes" / "audit.jsonl").unlink()   # sem movimento no período
        self.ok(self.a.resumo())
        self.assertEqual(len(self.a.chats()), antes)
        self.assertIn("/aprovar_CALL_1", self.a.envios()[-1]["texto"])

    def test_pendencia_e_falha_sao_acrescentadas_pelo_script(self):
        proj = self.triar_call()
        self.ok(self.a.resumo())
        texto = self.a.envios()[-1]["texto"]
        self.assertIn("resumo de teste do @pm", texto)       # o que o modelo escreveu
        self.assertIn("Precisa de você:", texto)             # o que o script acrescentou
        self.assertIn("/aprovar_CALL_1", texto)

    def test_linha_vazia_do_modelo_some(self):
        from importlib.machinery import SourceFileLoader
        carregador = SourceFileLoader("rd", str(self.a.bin / "resumo-do-dia"))
        rd = importlib.util.module_from_spec(importlib.util.spec_from_loader("rd", carregador))
        carregador.exec_module(rd)
        fatos = {"falhas": [], "espera": []}
        texto = rd.montar("📋 x\nFeito: a; b\nEm andamento: (nada)\nPrecisa de você: nenhum bloqueador", fatos)
        self.assertEqual(texto, "📋 x\nFeito: a; b")

    def test_modelo_falhou_manda_os_fatos_crus(self):
        self.a.repo_com_commits(self.a.acme, "feat: exporta Excel")
        self.a.chat_sai_com(1)
        self.ok(self.a.resumo())
        texto = self.a.envios()[-1]["texto"]
        self.assertIn("os fatos crus", texto)
        self.assertIn("exporta Excel", texto)

    def test_sem_nada_em_lugar_nenhum_avisa_curto(self):
        self.ok(self.a.resumo())
        self.assertIn("nenhum cliente teve movimento", self.a.envios()[-1]["texto"])

    def test_marca_so_avanca_quando_tudo_foi_entregue(self):
        self.a.repo_com_commits(self.a.acme, "feat: x")
        self.a.falhar_envios(10)
        self.assertNotEqual(self.a.resumo().returncode, 0)
        self.assertFalse((self.a.home / "resumo-do-dia.json").exists())
        self.a.falhar_envios(0)
        self.ok(self.a.resumo())
        self.assertTrue((self.a.home / "resumo-do-dia.json").exists())


if __name__ == "__main__":
    unittest.main()
