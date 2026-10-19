import calendar
from datetime import date

from src.banco import conectar


def centavos(valor):
    if isinstance(valor, int):
        return valor
    texto = "".join(str(valor or "0").replace("R$", "").split())
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return round(float(texto) * 100)


def adicionar_meses(dia, quantidade):
    mes_base = dia.month - 1 + quantidade
    ano, mes = dia.year + mes_base // 12, mes_base % 12 + 1
    return date(ano, mes, min(dia.day, calendar.monthrange(ano, mes)[1]))


def gerar_mensalidades(conexao, locacao_id, inicio, fim, dia_vencimento, valor, modalidade):
    inicio, fim = date.fromisoformat(inicio), date.fromisoformat(fim)
    cursor = date(inicio.year, inicio.month, 1)
    while cursor <= fim:
        competencia = cursor.strftime("%Y-%m")
        deslocamento = 0 if modalidade == "ANTECIPADO" else 1
        mes_vencimento = adicionar_meses(cursor, deslocamento)
        vencimento = date(
            mes_vencimento.year,
            mes_vencimento.month,
            min(dia_vencimento, calendar.monthrange(mes_vencimento.year, mes_vencimento.month)[1]),
        )
        conexao.execute(
            """INSERT OR IGNORE INTO mensalidades
               (locacao_id, competencia, vencimento, valor_centavos) VALUES (?,?,?,?)""",
            (locacao_id, competencia, vencimento.isoformat(), valor),
        )
        cursor = adicionar_meses(cursor, 1)


def atualizar_atrasos(conexao):
    conexao.execute(
        "UPDATE mensalidades SET status='ATRASADA' WHERE status='ABERTA' AND vencimento < ?",
        (date.today().isoformat(),),
    )


def criar_locacao(dados):
    obrigatorios = ("imovel_id", "inquilino_id", "data_inicio", "data_fim", "valor_aluguel", "dia_vencimento")
    ausentes = [campo for campo in obrigatorios if not dados.get(campo)]
    if ausentes:
        raise ValueError("Campos obrigatórios: " + ", ".join(ausentes))
    if dados["data_fim"] <= dados["data_inicio"]:
        raise ValueError("A data final deve ser posterior à data inicial.")
    valor = centavos(dados["valor_aluguel"])
    caucao = centavos(dados.get("deposito_caucao", 0))
    with conectar() as conexao:
        imovel = conexao.execute("SELECT status FROM imoveis WHERE id=?", (dados["imovel_id"],)).fetchone()
        if not imovel or imovel["status"] != "DISPONIVEL":
            raise ValueError("O imóvel selecionado não está disponível.")
        cursor = conexao.execute(
            """INSERT INTO locacoes
            (imovel_id,inquilino_id,data_inicio,data_fim,valor_aluguel_centavos,dia_vencimento,
             finalidade,modalidade_pagamento,deposito_caucao_centavos,indice_reajuste,observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (dados["imovel_id"], dados["inquilino_id"], dados["data_inicio"], dados["data_fim"],
             valor, int(dados["dia_vencimento"]), dados.get("finalidade", "RESIDENCIAL"),
             dados.get("modalidade_pagamento", "POSTECIPADO"), caucao,
             dados.get("indice_reajuste", "IPCA"), dados.get("observacoes", "")),
        )
        locacao_id = cursor.lastrowid
        gerar_mensalidades(conexao, locacao_id, dados["data_inicio"], dados["data_fim"],
                           int(dados["dia_vencimento"]), valor,
                           dados.get("modalidade_pagamento", "POSTECIPADO"))
        conexao.execute("UPDATE imoveis SET status='LOCADO' WHERE id=?", (dados["imovel_id"],))
        return locacao_id

