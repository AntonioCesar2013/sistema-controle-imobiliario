import unittest
from pathlib import Path
from uuid import uuid4

import src.banco as banco
from src.servicos import centavos, criar_locacao


class FluxoImobiliarioTest(unittest.TestCase):
    def setUp(self):
        self.caminho = Path(__file__).parent / f"teste-{uuid4().hex}.db"
        banco.CAMINHO_BANCO = self.caminho
        banco.inicializar()

    def tearDown(self):
        for sufixo in ("", "-wal", "-shm"):
            caminho = Path(str(self.caminho) + sufixo)
            if caminho.exists():
                caminho.unlink()

    def test_fluxo_completo_gera_mensalidades_e_bloqueia_segunda_locacao(self):
        with banco.conectar() as conexao:
            proprietario = conexao.execute(
                "INSERT INTO proprietarios(nome,cpf_cnpj) VALUES (?,?)", ("Ana", "111")
            ).lastrowid
            inquilino = conexao.execute(
                "INSERT INTO inquilinos(nome,cpf_cnpj) VALUES (?,?)", ("Bruno", "222")
            ).lastrowid
            imovel = conexao.execute(
                """INSERT INTO imoveis(proprietario_id,codigo,endereco,cidade,uf)
                VALUES (?,?,?,?,?)""", (proprietario, "IMO-1", "Rua A", "Cidade", "SP")
            ).lastrowid
        dados = {"imovel_id": imovel, "inquilino_id": inquilino,
                 "data_inicio": "2026-01-01", "data_fim": "2026-12-31",
                 "valor_aluguel": "1.500,00", "dia_vencimento": 10,
                 "finalidade": "RESIDENCIAL", "modalidade_pagamento": "POSTECIPADO"}
        codigo = criar_locacao(dados)
        with banco.conectar() as conexao:
            self.assertEqual(12, conexao.execute(
                "SELECT count(*) FROM mensalidades WHERE locacao_id=?", (codigo,)
            ).fetchone()[0])
            self.assertEqual("2026-02-10", conexao.execute(
                "SELECT vencimento FROM mensalidades ORDER BY vencimento LIMIT 1"
            ).fetchone()[0])
            self.assertEqual("LOCADO", conexao.execute(
                "SELECT status FROM imoveis WHERE id=?", (imovel,)
            ).fetchone()[0])
        with self.assertRaisesRegex(ValueError, "não está disponível"):
            criar_locacao(dados)

    def test_conversao_monetaria_brasileira(self):
        self.assertEqual(150050, centavos("1.500,50"))
        self.assertEqual(999, centavos("9,99"))


if __name__ == "__main__":
    unittest.main()
