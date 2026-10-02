"""Testes da proposta do GATE 1: conferência por código e auditoria em sessão nova.

Por que existe
--------------
A proposta chegava ao Telegram com ~200 linhas — o corpo de cada issue dentro — e
esquecia pedido da call. Nada obrigava a conferir item a item: o @po improvisava a
checagem enquanto escrevia, e relia com a mesma cabeça que escreveu.

Agora são dois controles, e cada um tem teste aqui:
- o `hermes-task` recusa o move para AWAITING_APPROVAL quando evidência ficou sem destino,
  quando a proposta traz item sem evidência, quando o trecho citado não está na fonte,
  quando dúvida ficou fora de "Preciso do seu OK" e quando a proposta passa de 80 linhas;
- antes do gate sair, uma sessão NOVA do @po audita contra a call. Achou algo → volta ao
  @po (máx. 2 voltas, sem gastar os ajustes do humano); depois disso, o gate sai com o
  que sobrou escrito.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ambiente import PROPOSTA_VALIDA, VIA  # noqa: E402
from test_fluxo import Base  # noqa: E402

REFAZER = ("## Perdeu\n- o total por loja sumiu — fonte: \"com total por loja\"\n"
           "## Inventou\n- nada\n\nVeredito: refazer")


def proposta(trocar_de, trocar_para):
    return PROPOSTA_VALIDA["proposta.md"].replace(trocar_de, trocar_para)


class Conferencia(Base):
    def setUp(self):
        super().setUp()
        self.ok(self.a.task("new", str(self.a.acme), "CALL-1", "--objetivo", "t", "--agentes", "pm,po"))
        mf = self.a.acme / ".hermes" / "tasks" / "CALL-1" / "manifest.yaml"
        mf.write_text(mf.read_text().replace("estado: RECEIVED", "estado: TRIAGED"))

    def mover(self, **trocar):
        return self.a.task("move", str(self.a.acme), "CALL-1", "AWAITING_APPROVAL", "--by", "po",
                           *self.a.proposta(self.a.acme, "CALL-1", **trocar))

    def test_valida_passa_e_guarda_os_tres_artefatos(self):
        self.ok(self.mover())
        art = self.a.manifest(self.a.acme, "CALL-1")["artefatos"]
        for k in ("proposta", "evidencias", "corpos"):
            self.assertTrue(art[k].endswith(f"{k}.md"), art)

    def test_sem_evidencias_e_corpos_recusa(self):
        arq = self.a.acme / "AGENTS.md"
        self.negado(self.a.task("move", str(self.a.acme), "CALL-1", "AWAITING_APPROVAL", "--by", "po",
                                "--ev", f"proposta={arq}"), "evidencias (arquivo que exista)")

    def test_evidencia_esquecida(self):
        ev = PROPOSTA_VALIDA["evidencias.md"] + "\n## E2 · pedido\n> com total por loja\nClasse: nova\n"
        self.negado(self.mover(evidencias_md=ev), "esquecida?): E2")

    def test_item_sem_evidencia(self):
        p = proposta("## Nada a fazer", "### Nova · feat: dashboard bonito · 8h\n\n## Nada a fazer")
        self.negado(self.mover(proposta_md=p), "item da proposta sem evidência")

    def test_cita_evidencia_que_nao_existe(self):
        p = proposta("## Nada a fazer\nnenhum", "## Nada a fazer\n- E9 → já feito")
        self.negado(self.mover(proposta_md=p), "não existe: E9")

    def test_trecho_que_nao_esta_na_fonte(self):
        # paráfrase "para ficar claro" é onde o sentido muda
        ev = PROPOSTA_VALIDA["evidencias.md"].replace("quero um relatório de vendas por mês",
                                                      "o cliente precisa de relatório mensal")
        self.negado(self.mover(evidencias_md=ev), "o trecho não está na fonte")

    def test_trecho_aceita_corte_acento_e_pontuacao(self):
        ev = PROPOSTA_VALIDA["evidencias.md"].replace(
            "> quero um relatório de vendas por mês", "> Quero um RELATORIO de vendas… total por loja")
        self.ok(self.mover(evidencias_md=ev))

    def test_duvida_fora_do_preciso_do_seu_ok(self):
        ev = PROPOSTA_VALIDA["evidencias.md"] + "\n## E2 · dúvida\n> com total por loja\nClasse: dúvida\n"
        p = proposta("## Nada a fazer\nnenhum", "## Nada a fazer\n- E2 → fica para depois")
        self.negado(self.mover(evidencias_md=ev, proposta_md=p), "dúvida fora de “Preciso do seu OK”")
        p = proposta("## Preciso do seu OK\nnenhum",
                     "## Preciso do seu OK\n### D1 — total por loja entra? (E2)\nMinha premissa: sim.")
        self.ok(self.mover(evidencias_md=ev, proposta_md=p))

    def test_existente_sem_key(self):
        ev = PROPOSTA_VALIDA["evidencias.md"].replace("Classe: nova", "Classe: existente")
        self.negado(self.mover(evidencias_md=ev), "sem a KEY da issue")
        ev = PROPOSTA_VALIDA["evidencias.md"].replace("Classe: nova", "Classe: existente OUVI-147")
        self.ok(self.mover(evidencias_md=ev))

    def test_proposta_longa_demais(self):
        p = proposta("## Gap check", "\n".join(f"linha {i} (E1)" for i in range(90)) + "\n## Gap check")
        self.negado(self.mover(proposta_md=p), "máx. 80")

    def test_falta_secao(self):
        p = proposta("## Gap check\nEvidências: 1 · com destino: 1\n", "")
        self.negado(self.mover(proposta_md=p), "`## Gap check`")

    def test_auditor_so_devolve_nao_aprova(self):
        self.ok(self.mover())
        self.negado(self.a.task("move", str(self.a.acme), "CALL-1", "SPECIFYING", "--by", "auditor",
                                "--ev", "issues=x", "--ev", "via=x"), "quem pode: humano")
        self.ok(self.a.task("move", str(self.a.acme), "CALL-1", "TRIAGED", "--by", "auditor",
                            "--ev", "motivo=perdeu E2"))


class Auditoria(Base):
    def gate1(self):
        return [e["texto"] for e in self.a.envios() if e["texto"].startswith("🚦 GATE 1")]

    def test_limpa_vai_no_gate(self):
        proj = self.triar_call()
        auds = [c for c in self.a.chats() if c.get("auditoria")]
        self.assertEqual(len(auds), 1)
        # sessão nova: nome próprio, nunca a `CALL-1-po` de quem escreveu
        self.assertNotEqual(auds[0]["sessao"], "CALL-1-po")
        self.assertIn("2026-09-29-0.md", auds[0]["query"])          # leu a call original
        self.assertIn("🔎 Auditoria 1: nada perdido", self.gate1()[0])
        self.assertTrue((proj / ".hermes" / "tasks" / "CALL-1" / "auditoria-1.md").is_file())

    def test_achou_algo_volta_ao_po_antes_do_humano_ver(self):
        self.a.auditorias(REFAZER)
        proj = self.triar_call()
        m = self.a.manifest(proj, "CALL-1")
        self.assertEqual(m["estado"], "AWAITING_APPROVAL")
        # o humano só recebe UM gate: o da versão corrigida
        self.assertEqual(len(self.gate1()), 1)
        self.assertIn("🔎 Auditoria 2", self.gate1()[0])
        devolvida = [h for h in m["historico"] if h.get("por") == "auditor"]
        self.assertEqual(len(devolvida), 1)
        self.assertIn("total por loja", devolvida[0]["evidencias"]["motivo"])
        # o @po refez na MESMA sessão dele, com os achados no handoff
        po = [c for c in self.a.chats_de_bot() if c["perfil"] == "po"]
        self.assertEqual([c["sessao"] for c in po], ["CALL-1-po", "CALL-1-po"])
        self.assertIn("com total por loja", po[-1]["query"])
        self.assertTrue(list((proj / ".hermes" / "tasks" / "CALL-1" / "handoffs").glob("*-auditor-para-po.md")))

    def test_depois_de_duas_voltas_o_gate_sai_com_o_que_sobrou(self):
        self.a.auditorias(REFAZER, REFAZER, REFAZER, REFAZER)
        proj = self.triar_call()
        self.assertEqual(self.a.estado(proj, "CALL-1"), "AWAITING_APPROVAL")
        self.assertEqual(len([c for c in self.a.chats() if c.get("auditoria")]), 3)
        gate = self.gate1()
        self.assertEqual(len(gate), 1)
        self.assertIn("ainda aponta, depois de 2 volta(s)", gate[0])
        self.assertIn("total por loja", gate[0])

    def test_voltas_da_auditoria_nao_gastam_os_ajustes_do_humano(self):
        self.a.auditorias(REFAZER, REFAZER)
        proj = self.triar_call()
        for _ in range(3):
            self.ok(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "de novo"))
            self.a.esperar_rodadas(proj)
            self.assertEqual(self.a.estado(proj, "CALL-1"), "AWAITING_APPROVAL")
        self.negado(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "mais"), "Decida")

    def test_auditoria_sem_veredito_nao_segura_o_gate(self):
        self.a.auditorias("acho que está tudo certo")
        self.triar_call()
        self.assertIn("A auditoria não rodou", self.gate1()[0])

    def test_ajuste_do_humano_e_auditado_de_novo(self):
        proj = self.triar_call()
        self.ok(self.a.dispatch("ajustar", "CALL-1", "--via", VIA, "--", "tira a busca"))
        self.a.esperar_rodadas(proj)
        self.assertEqual(len([c for c in self.a.chats() if c.get("auditoria")]), 2)


if __name__ == "__main__":
    unittest.main()
