import unittest
from pathlib import Path
from uuid import uuid4

import src.banco as banco
from src.popular_banco import popular
from src.servicos import centavos, criar_imovel, criar_locacao


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
        self.assertEqual(580000, centavos("R$ 5.800,00"))
        self.assertEqual(580000, centavos("R$\u00a05.800,00"))

    def test_cadastro_de_imovel_gera_codigo_e_salva_caracteristicas(self):
        with banco.conectar() as conexao:
            proprietario = conexao.execute(
                "INSERT INTO proprietarios(nome,cpf_cnpj) VALUES (?,?)", ("Ana", "333")
            ).lastrowid
        identificador, codigo = criar_imovel({
            "proprietario_id": proprietario, "tipo": "CASA", "endereco": "Rua B, 20",
            "cidade": "Cidade", "uf": "sp", "cep": "00000-000", "quartos": "3",
            "suites": "1", "banheiros": "2", "vagas_garagem": "2",
            "area_imovel_m2": "145,50", "area_terreno_m2": "250",
            "cozinha_planejada": "1", "mobiliado": "0",
        })
        self.assertEqual("IMO-0001", codigo)
        with banco.conectar() as conexao:
            imovel = conexao.execute("SELECT * FROM imoveis WHERE id=?", (identificador,)).fetchone()
        self.assertEqual(3, imovel["quartos"])
        self.assertEqual(145.5, imovel["area_imovel_m2"])
        self.assertEqual(1, imovel["cozinha_planejada"])

    def test_populador_e_idempotente_e_cobre_cenarios(self):
        primeiro = popular()
        segundo = popular()
        self.assertEqual(primeiro, segundo)
        self.assertEqual(3, segundo["proprietarios"])
        self.assertEqual(4, segundo["inquilinos"])
        self.assertEqual(7, segundo["imoveis"])
        self.assertEqual(5, segundo["locacoes"])
        with banco.conectar() as conexao:
            modalidades = {linha[0] for linha in conexao.execute(
                "SELECT DISTINCT modalidade_pagamento FROM locacoes"
            )}
            finalidades = {linha[0] for linha in conexao.execute(
                "SELECT DISTINCT finalidade FROM locacoes"
            )}
            status = {linha[0] for linha in conexao.execute(
                "SELECT DISTINCT status FROM mensalidades"
            )}
        self.assertEqual({"ANTECIPADO", "POSTECIPADO"}, modalidades)
        self.assertEqual({"RESIDENCIAL", "COMERCIAL"}, finalidades)
        self.assertTrue({"PAGA", "ATRASADA"}.issubset(status))


if __name__ == "__main__":
    unittest.main()
