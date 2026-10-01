"""Testes do openwhispr-notes: o que vira call, o que vira continuação e o que fica quieto.

    python3 -m unittest discover -s tests -v

Banco SQLite sintético, script rodado de verdade. Cada teste cobre algo que o dado real mostrou
(nota 7 do agregador: anexaram fala numa nota já exportada e ela nunca mais saiu).
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "bin" / "openwhispr-notes"


def seg(texto, quem="speaker_1", fonte="system"):
    return {"text": texto, "source": fonte, "speaker": quem, "timestamp": 0}


def fala(n, base="a configuracao do parceiro precisa ficar no front"):
    """Fala longa e determinística: `n` identifica qual, para não haver acréscimo 'parecido'."""
    return f"{base} item {n} " + ("com detalhe de negocio " * 14)


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="owh-teste-"))
        self.db = self.d / "transcriptions.db"
        self.inbox = self.d / "inbox"
        con = sqlite3.connect(self.db)
        con.executescript("""
            create table folders (id integer primary key, name text);
            create table notes (id integer primary key, title text, content text, transcript text,
                enhanced_content text, folder_id integer, created_at text, updated_at text,
                deleted_at text, audio_duration_seconds real, participants text);
            insert into folders values (1, 'Acme');
        """)
        con.commit()
        con.close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.d, ignore_errors=True)

    def nota(self, id=1, falas=(), criado="2026-09-30 13:00:00", atualizado=None, titulo="Daily", deletada=None):
        con = sqlite3.connect(self.db)
        con.execute("insert or replace into notes (id,title,transcript,folder_id,created_at,updated_at,deleted_at)"
                    " values (?,?,?,?,?,?,?)",
                    (id, titulo, json.dumps(list(falas)) if falas else "", 1, criado, atualizado or criado, deletada))
        con.commit()
        con.close()

    def exportar(self, comando="novas"):
        r = subprocess.run([sys.executable, str(SCRIPT), comando, "--db", str(self.db), "--inbox", str(self.inbox)],
                           capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(r.returncode, 0, r.stderr)
        fila = self.inbox / ".novas.txt"
        return [l for l in fila.read_text(encoding="utf-8").splitlines() if l.strip()] if fila.exists() else []

    def log(self):
        f = self.inbox / ".openwhispr-notes.log"
        return f.read_text(encoding="utf-8") if f.exists() else ""


class TestExportador(Base):
    def test_nota_nova_sai_uma_vez(self):
        self.nota(falas=[seg(fala(1))])
        self.assertEqual(len(self.exportar()), 1)
        self.assertEqual(self.exportar(), [])                       # 2ª rodada: nada novo

    def test_nota_que_cresceu_vira_parte_so_com_o_trecho_novo(self):
        # o caso real: anexaram conversa nova numa nota já exportada e o orquestrador não via
        self.nota(falas=[seg(fala(1)), seg(fala(2), "speaker_2")])
        primeira = self.exportar()
        self.assertEqual(len(primeira), 1)
        self.nota(falas=[seg(fala(1)), seg(fala(2), "speaker_2"), seg(fala(3)), seg(fala(4), "speaker_2")],
                  atualizado="2026-10-01 10:00:00")
        segunda = self.exportar()
        self.assertEqual(len(segunda), 1)
        parte = Path(segunda[0])
        self.assertIn("parte-2", parte.name)
        texto = parte.read_text(encoding="utf-8")
        self.assertIn("item 3", texto)
        self.assertIn("item 4", texto)
        self.assertNotIn("item 1", texto)                          # o que já foi triado não volta
        self.assertNotIn("item 2", texto)
        self.assertIn("continuacao_da_nota: 1", texto)
        self.assertIn("Só o trecho novo", texto)
        self.assertEqual(self.exportar(), [])                       # e não repete na rodada seguinte

    def test_crescer_de_novo_gera_outra_parte_sem_sobrescrever(self):
        self.nota(falas=[seg(fala(1))])
        self.exportar()
        self.nota(falas=[seg(fala(1)), seg(fala(2))], atualizado="2026-10-01 10:00:00")
        p2 = Path(self.exportar()[0])
        self.nota(falas=[seg(fala(1)), seg(fala(2)), seg(fala(3))], atualizado="2026-10-01 11:00:00")
        p3 = Path(self.exportar()[0])
        self.assertNotEqual(p2, p3)
        self.assertIn("item 2", p2.read_text(encoding="utf-8"))
        self.assertNotIn("item 2", p3.read_text(encoding="utf-8"))
        self.assertIn("item 3", p3.read_text(encoding="utf-8"))

    def test_acrescimo_pequeno_acumula_em_vez_de_virar_call(self):
        # corrigir uma palavra ou dizer "ok" não é conversa nova
        self.nota(falas=[seg(fala(1))])
        self.exportar()
        self.nota(falas=[seg(fala(1)), seg("ok, certo")], atualizado="2026-10-01 10:00:00")
        self.assertEqual(self.exportar(), [])
        self.assertIn("espero acumular", self.log())
        # quando o acúmulo passa do limite, sai tudo o que ficou represado
        self.nota(falas=[seg(fala(1)), seg("ok, certo"), seg(fala(2))], atualizado="2026-10-01 11:00:00")
        achou = self.exportar()
        self.assertEqual(len(achou), 1)
        self.assertIn("ok, certo", Path(achou[0]).read_text(encoding="utf-8"))

    def test_texto_alterado_no_meio_nao_vira_call_e_vira_a_nova_referencia(self):
        # editar o que já foi dito não é conversa nova: exportar de novo seria call duplicada
        self.nota(falas=[seg(fala(1)), seg(fala(2))])
        self.exportar()
        self.nota(falas=[seg("texto corrigido a mao " * 10), seg(fala(2))], atualizado="2026-10-01 10:00:00")
        self.assertEqual(self.exportar(), [])
        self.assertIn("alterado", self.log())
        self.assertEqual(self.exportar(), [])                       # e não fica reclamando

    def test_diarizacao_refeita_nao_e_conversa_nova(self):
        # dado real da nota 7: o OpenWhispr refaz as vozes depois, a mesma fala troca de rótulo
        # e o texto renderizado diverge — mas ninguém disse nada de novo.
        self.nota(falas=[seg(fala(1), "speaker_16"), seg(fala(2), "speaker_1")])
        self.exportar()
        self.nota(falas=[seg(fala(1), "speaker_1"), seg(fala(2), "speaker_1")], atualizado="2026-10-01 10:00:00")
        self.assertEqual(self.exportar(), [])

    def test_acrescimo_com_diarizacao_diferente_ainda_acha_o_trecho_novo(self):
        self.nota(falas=[seg(fala(1), "speaker_16"), seg(fala(2), "speaker_1")])
        self.exportar()
        self.nota(falas=[seg(fala(1), "speaker_1"), seg(fala(2), "speaker_1"), seg(fala(3), "speaker_2")],
                  atualizado="2026-10-01 10:00:00")
        achou = self.exportar()
        self.assertEqual(len(achou), 1)
        texto = Path(achou[0]).read_text(encoding="utf-8")
        self.assertIn("item 3", texto)
        self.assertNotIn("item 1", texto)

    def test_marca_antiga_sem_registro_usa_o_md_ja_exportado(self):
        # o job real estava com uma marca só de {"ate","exportado_em"}: a 1ª rodada nova precisa
        # reconhecer o que já saiu pelo próprio .md, senão reexportaria a nota inteira como call.
        self.nota(falas=[seg(fala(1)), seg(fala(2))])
        self.exportar()
        marca = self.inbox / ".ultima-exportacao-openwhispr.json"
        antiga = json.loads(marca.read_text(encoding="utf-8"))
        antiga.pop("notas")
        marca.write_text(json.dumps(antiga), encoding="utf-8")
        self.assertEqual(self.exportar(), [])                       # nada mudou: fica quieto
        marca.write_text(json.dumps(antiga), encoding="utf-8")
        self.nota(falas=[seg(fala(1)), seg(fala(2)), seg(fala(3))], atualizado="2026-10-01 10:00:00")
        achou = self.exportar()
        self.assertEqual(len(achou), 1)
        self.assertNotIn("item 1", Path(achou[0]).read_text(encoding="utf-8"))

    def test_nota_apagada_e_vazia_nao_viram_call(self):
        self.nota(id=1, falas=[seg(fala(1))], deletada="2026-10-01 09:00:00")
        self.nota(id=2, falas=[])
        self.assertEqual(self.exportar(), [])

    def test_comando_todas_continua_reexportando_tudo(self):
        self.nota(falas=[seg(fala(1))])
        self.exportar()
        self.assertEqual(len(self.exportar("todas")), 1)


if __name__ == "__main__":
    unittest.main()
