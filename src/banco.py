import sqlite3
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BANCO = RAIZ / "dados" / "imobiliaria.db"


class Conexao(sqlite3.Connection):
    """Transação que também libera o arquivo ao sair do bloco ``with``."""

    def __exit__(self, tipo, valor, traceback):
        try:
            return super().__exit__(tipo, valor, traceback)
        finally:
            self.close()


def conectar():
    CAMINHO_BANCO.parent.mkdir(exist_ok=True)
    conexao = sqlite3.connect(CAMINHO_BANCO, timeout=20, factory=Conexao)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 20000")
    return conexao


SCHEMA = """
CREATE TABLE IF NOT EXISTS proprietarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL, cpf_cnpj TEXT NOT NULL UNIQUE, telefone TEXT,
    email TEXT, endereco TEXT, ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS inquilinos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL, cpf_cnpj TEXT NOT NULL UNIQUE, telefone TEXT,
    email TEXT, profissao TEXT, renda_centavos INTEGER NOT NULL DEFAULT 0,
    ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS imoveis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proprietario_id INTEGER NOT NULL, codigo TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL DEFAULT 'CASA', endereco TEXT NOT NULL,
    cidade TEXT NOT NULL, uf TEXT NOT NULL, cep TEXT, descricao TEXT,
    quartos INTEGER, suites INTEGER, banheiros INTEGER, vagas_garagem INTEGER,
    area_imovel_m2 REAL, area_terreno_m2 REAL, cozinha_planejada INTEGER,
    mobiliado INTEGER, andar INTEGER, possui_elevador INTEGER,
    valor_condominio_centavos INTEGER, salas INTEGER, possui_recepcao INTEGER,
    possui_copa INTEGER, possui_ar_condicionado INTEGER, pe_direito_m REAL,
    docas INTEGER, possui_escritorio INTEGER, energia_trifasica INTEGER,
    largura_terreno_m REAL, comprimento_terreno_m REAL, topografia TEXT,
    terreno_murado INTEGER,
    status TEXT NOT NULL DEFAULT 'DISPONIVEL'
        CHECK(status IN ('DISPONIVEL','LOCADO','MANUTENCAO','INATIVO')),
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(proprietario_id) REFERENCES proprietarios(id)
);
CREATE TABLE IF NOT EXISTS locacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imovel_id INTEGER NOT NULL, inquilino_id INTEGER NOT NULL,
    data_inicio TEXT NOT NULL, data_fim TEXT NOT NULL,
    valor_aluguel_centavos INTEGER NOT NULL CHECK(valor_aluguel_centavos > 0),
    dia_vencimento INTEGER NOT NULL CHECK(dia_vencimento BETWEEN 1 AND 28),
    finalidade TEXT NOT NULL CHECK(finalidade IN ('RESIDENCIAL','COMERCIAL')),
    modalidade_pagamento TEXT NOT NULL CHECK(modalidade_pagamento IN ('ANTECIPADO','POSTECIPADO')),
    deposito_caucao_centavos INTEGER NOT NULL DEFAULT 0,
    indice_reajuste TEXT NOT NULL DEFAULT 'IPCA', observacoes TEXT,
    status TEXT NOT NULL DEFAULT 'ATIVA' CHECK(status IN ('ATIVA','ENCERRADA','CANCELADA')),
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(imovel_id) REFERENCES imoveis(id),
    FOREIGN KEY(inquilino_id) REFERENCES inquilinos(id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uma_locacao_ativa_por_imovel
ON locacoes(imovel_id) WHERE status = 'ATIVA';
CREATE TABLE IF NOT EXISTS mensalidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT, locacao_id INTEGER NOT NULL,
    competencia TEXT NOT NULL, vencimento TEXT NOT NULL,
    valor_centavos INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'ABERTA'
        CHECK(status IN ('ABERTA','PAGA','ATRASADA','CANCELADA')),
    pago_em TEXT, valor_pago_centavos INTEGER, forma_pagamento TEXT, observacoes TEXT,
    UNIQUE(locacao_id, competencia),
    FOREIGN KEY(locacao_id) REFERENCES locacoes(id)
);
CREATE INDEX IF NOT EXISTS idx_mensalidades_vencimento ON mensalidades(status, vencimento);
"""


def inicializar():
    with conectar() as conexao:
        conexao.executescript(SCHEMA)
        colunas = {linha["name"] for linha in conexao.execute("PRAGMA table_info(imoveis)")}
        novas_colunas = {
            "quartos": "INTEGER", "suites": "INTEGER", "banheiros": "INTEGER",
            "vagas_garagem": "INTEGER", "area_imovel_m2": "REAL",
            "area_terreno_m2": "REAL", "cozinha_planejada": "INTEGER",
            "mobiliado": "INTEGER", "andar": "INTEGER", "possui_elevador": "INTEGER",
            "valor_condominio_centavos": "INTEGER", "salas": "INTEGER",
            "possui_recepcao": "INTEGER", "possui_copa": "INTEGER",
            "possui_ar_condicionado": "INTEGER", "pe_direito_m": "REAL",
            "docas": "INTEGER", "possui_escritorio": "INTEGER",
            "energia_trifasica": "INTEGER", "largura_terreno_m": "REAL",
            "comprimento_terreno_m": "REAL", "topografia": "TEXT",
            "terreno_murado": "INTEGER",
        }
        for nome, definicao in novas_colunas.items():
            if nome not in colunas:
                conexao.execute(f"ALTER TABLE imoveis ADD COLUMN {nome} {definicao}")

