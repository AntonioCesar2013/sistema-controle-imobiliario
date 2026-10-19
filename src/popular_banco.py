"""Gera uma carteira fictícia para demonstração e testes manuais."""

from datetime import date

from src.banco import conectar, inicializar
from src.servicos import adicionar_meses, atualizar_atrasos, criar_locacao


MARCADOR = "[DADOS DE DEMONSTRAÇÃO]"

PROPRIETARIOS = (
    ("Helena Martins", "900.000.001-00", "(11) 99911-1001", "helena@example.com", "Alameda Santos, 820 - São Paulo/SP"),
    ("Carlos Eduardo Ribeiro", "900.000.002-00", "(11) 99922-2002", "carlos@example.com", "Rua das Acácias, 45 - Campinas/SP"),
    ("Grupo Horizonte Patrimonial Ltda.", "90.000.003/0001-00", "(11) 3333-3030", "contato@horizonte.example.com", "Av. Paulista, 1500 - São Paulo/SP"),
)

INQUILINOS = (
    ("Mariana Alves", "800.000.001-00", "(11) 98811-1101", "mariana@example.com", "Arquiteta", 950000),
    ("Rafael Nogueira", "800.000.002-00", "(11) 98822-2202", "rafael@example.com", "Engenheiro", 1250000),
    ("Café Aurora Comércio Ltda.", "80.000.003/0001-00", "(11) 3222-3003", "financeiro@cafeaurora.example.com", "Comércio", 3000000),
    ("Studio Prisma Design Ltda.", "80.000.004/0001-00", "(11) 3222-4004", "contato@studioprisma.example.com", "Serviços", 2200000),
)

IMOVEIS = (
    ("DEMO-APT-001", "900.000.001-00", "APARTAMENTO", "Rua Bela Cintra, 410, ap. 82", "São Paulo", "SP", "01415-000", "Apartamento com 2 dormitórios e uma vaga."),
    ("DEMO-CAS-002", "900.000.001-00", "CASA", "Rua Harmonia, 215", "São Paulo", "SP", "05435-000", "Casa residencial com quintal."),
    ("DEMO-SAL-003", "90.000.003/0001-00", "SALA COMERCIAL", "Av. Paulista, 1000, cj. 1204", "São Paulo", "SP", "01310-100", "Sala comercial mobiliada."),
    ("DEMO-LOJ-004", "90.000.003/0001-00", "SALA COMERCIAL", "Rua Augusta, 720, loja 3", "São Paulo", "SP", "01304-001", "Loja térrea com vitrine."),
    ("DEMO-APT-005", "900.000.002-00", "APARTAMENTO", "Av. Norte-Sul, 560, ap. 31", "Campinas", "SP", "13083-852", "Apartamento residencial próximo ao centro."),
    ("DEMO-GAL-006", "900.000.002-00", "GALPÃO", "Rod. Dom Pedro I, km 132", "Campinas", "SP", "13091-901", "Galpão disponível para nova locação."),
    ("DEMO-CAS-007", "900.000.002-00", "CASA", "Rua dos Ipês, 90", "Valinhos", "SP", "13270-120", "Imóvel disponível para testar novo contrato."),
)


def primeiro_dia(dia):
    return dia.replace(day=1)


def iso(dia):
    return dia.isoformat()


def inserir_cadastros():
    with conectar() as conexao:
        conexao.executemany(
            """INSERT OR IGNORE INTO proprietarios
            (nome,cpf_cnpj,telefone,email,endereco) VALUES (?,?,?,?,?)""",
            PROPRIETARIOS,
        )
        conexao.executemany(
            """INSERT OR IGNORE INTO inquilinos
            (nome,cpf_cnpj,telefone,email,profissao,renda_centavos) VALUES (?,?,?,?,?,?)""",
            INQUILINOS,
        )
        donos = {linha["cpf_cnpj"]: linha["id"] for linha in conexao.execute(
            "SELECT id,cpf_cnpj FROM proprietarios"
        )}
        for codigo, cpf, tipo, endereco, cidade, uf, cep, descricao in IMOVEIS:
            conexao.execute(
                """INSERT OR IGNORE INTO imoveis
                (proprietario_id,codigo,tipo,endereco,cidade,uf,cep,descricao)
                VALUES (?,?,?,?,?,?,?,?)""",
                (donos[cpf], codigo, tipo, endereco, cidade, uf, cep, descricao),
            )


def ids_por(conexao, tabela, chave):
    return {linha[chave]: linha["id"] for linha in conexao.execute(
        f"SELECT id,{chave} FROM {tabela}"
    )}


def criar_se_ausente(imovel_id, dados):
    with conectar() as conexao:
        existente = conexao.execute(
            "SELECT id FROM locacoes WHERE imovel_id=? AND observacoes LIKE ?",
            (imovel_id, f"%{MARCADOR}%"),
        ).fetchone()
    return existente["id"] if existente else criar_locacao({**dados, "imovel_id": imovel_id})


def inserir_locacoes():
    hoje = date.today()
    mes = primeiro_dia(hoje)
    with conectar() as conexao:
        imoveis = ids_por(conexao, "imoveis", "codigo")
        inquilinos = ids_por(conexao, "inquilinos", "cpf_cnpj")

    cenarios = (
        ("DEMO-APT-001", "800.000.001-00", -5, 6, "2.350,00", 10, "RESIDENCIAL", "POSTECIPADO", "4.700,00", "IPCA", "Contrato residencial postecipado. Mensalidades antigas pagas."),
        ("DEMO-CAS-002", "800.000.002-00", -3, 8, "3.100,00", 5, "RESIDENCIAL", "ANTECIPADO", "9.300,00", "IGP-M", "Contrato antecipado com uma mensalidade em atraso."),
        ("DEMO-SAL-003", "80.000.003/0001-00", -7, 16, "5.800,00", 15, "COMERCIAL", "POSTECIPADO", "11.600,00", "IPCA", "Contrato comercial de 24 meses."),
        ("DEMO-LOJ-004", "80.000.004/0001-00", -1, 10, "4.250,00", 20, "COMERCIAL", "ANTECIPADO", "0,00", "INPC", "Contrato comercial sem caução."),
    )
    locacoes = []
    for codigo, cpf, ini, fim, valor, vencimento, finalidade, modalidade, caucao, indice, nota in cenarios:
        locacoes.append(criar_se_ausente(imoveis[codigo], {
            "inquilino_id": inquilinos[cpf], "data_inicio": iso(adicionar_meses(mes, ini)),
            "data_fim": iso(adicionar_meses(mes, fim)), "valor_aluguel": valor,
            "dia_vencimento": vencimento, "finalidade": finalidade,
            "modalidade_pagamento": modalidade, "deposito_caucao": caucao,
            "indice_reajuste": indice, "observacoes": f"{MARCADOR} {nota}",
        }))

    # Histórico encerrado, útil para testar listagens e contratos antigos.
    historica = criar_se_ausente(imoveis["DEMO-APT-005"], {
        "inquilino_id": inquilinos["800.000.001-00"],
        "data_inicio": iso(adicionar_meses(mes, -18)), "data_fim": iso(adicionar_meses(mes, -7)),
        "valor_aluguel": "1.900,00", "dia_vencimento": 8, "finalidade": "RESIDENCIAL",
        "modalidade_pagamento": "POSTECIPADO", "deposito_caucao": "3.800,00",
        "indice_reajuste": "IPCA", "observacoes": f"{MARCADOR} Contrato já encerrado.",
    })
    with conectar() as conexao:
        conexao.execute("UPDATE locacoes SET status='ENCERRADA' WHERE id=?", (historica,))
        conexao.execute("UPDATE imoveis SET status='DISPONIVEL' WHERE id=?", (imoveis["DEMO-APT-005"],))

        # Quita competências antigas do primeiro contrato e todo o contrato histórico.
        for locacao_id in (locacoes[0], historica):
            parcelas = conexao.execute(
                "SELECT id,vencimento,valor_centavos FROM mensalidades WHERE locacao_id=? AND vencimento<=?",
                (locacao_id, hoje.isoformat()),
            ).fetchall()
            for parcela in parcelas:
                conexao.execute(
                    """UPDATE mensalidades SET status='PAGA', pago_em=?, valor_pago_centavos=?,
                    forma_pagamento='PIX', observacoes='Recebimento fictício para demonstração.' WHERE id=?""",
                    (parcela["vencimento"], parcela["valor_centavos"], parcela["id"]),
                )
        atualizar_atrasos(conexao)


def resumo():
    with conectar() as conexao:
        linha = conexao.execute("""SELECT
            (SELECT count(*) FROM proprietarios WHERE cpf_cnpj LIKE '900.%' OR cpf_cnpj LIKE '90.%') proprietarios,
            (SELECT count(*) FROM inquilinos WHERE cpf_cnpj LIKE '800.%' OR cpf_cnpj LIKE '80.%') inquilinos,
            (SELECT count(*) FROM imoveis WHERE codigo LIKE 'DEMO-%') imoveis,
            (SELECT count(*) FROM locacoes WHERE observacoes LIKE ?) locacoes,
            (SELECT count(*) FROM mensalidades m JOIN locacoes l ON l.id=m.locacao_id
             WHERE l.observacoes LIKE ?) mensalidades""", (f"%{MARCADOR}%", f"%{MARCADOR}%")).fetchone()
        return dict(linha)


def popular():
    inicializar()
    inserir_cadastros()
    inserir_locacoes()
    return resumo()


def main():
    dados = popular()
    print("Banco populado com dados fictícios de demonstração.")
    print(f"Proprietários: {dados['proprietarios']}")
    print(f"Inquilinos: {dados['inquilinos']}")
    print(f"Imóveis: {dados['imoveis']}")
    print(f"Locações: {dados['locacoes']}")
    print(f"Mensalidades: {dados['mensalidades']}")


if __name__ == "__main__":
    main()

