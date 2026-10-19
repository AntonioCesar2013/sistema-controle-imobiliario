import json
import mimetypes
import sqlite3
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.banco import conectar, inicializar
from src.servicos import centavos, criar_locacao, atualizar_atrasos


RAIZ = Path(__file__).resolve().parents[1]
FRONTEND = RAIZ / "frontend"


def linhas(resultado):
    return [dict(linha) for linha in resultado.fetchall()]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, formato, *args):
        return

    def responder(self, dados, status=200, tipo="application/json; charset=utf-8"):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8") if not isinstance(dados, bytes) else dados
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def corpo_json(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(tamanho) or b"{}")

    def do_GET(self):
        caminho = urlparse(self.path).path
        try:
            if caminho.startswith("/api/"):
                return self.api_get(caminho)
            arquivo = FRONTEND / (caminho.lstrip("/") or "index.html")
            if not arquivo.is_file() or FRONTEND not in arquivo.resolve().parents:
                arquivo = FRONTEND / "index.html"
            return self.responder(arquivo.read_bytes(), tipo=mimetypes.guess_type(arquivo)[0] or "application/octet-stream")
        except Exception as erro:
            return self.responder({"erro": str(erro)}, 500)

    def do_POST(self):
        try:
            self.api_post(urlparse(self.path).path, self.corpo_json())
        except (ValueError, sqlite3.IntegrityError) as erro:
            self.responder({"erro": str(erro)}, 400)
        except Exception as erro:
            self.responder({"erro": str(erro)}, 500)

    def api_get(self, caminho):
        with conectar() as c:
            atualizar_atrasos(c)
            if caminho == "/api/dashboard":
                hoje, limite = date.today().isoformat(), (date.today() + timedelta(days=7)).isoformat()
                dados = dict(c.execute("""SELECT
                    (SELECT count(*) FROM imoveis) imoveis,
                    (SELECT count(*) FROM imoveis WHERE status='LOCADO') locados,
                    (SELECT count(*) FROM locacoes WHERE status='ATIVA') locacoes_ativas,
                    (SELECT count(*) FROM mensalidades WHERE status='ATRASADA') atrasadas,
                    (SELECT coalesce(sum(valor_centavos),0) FROM mensalidades WHERE status IN ('ABERTA','ATRASADA')) a_receber_centavos,
                    (SELECT coalesce(sum(valor_pago_centavos),0) FROM mensalidades WHERE status='PAGA' AND substr(pago_em,1,7)=substr(date('now'),1,7)) recebido_mes_centavos
                """).fetchone())
                dados["proximos"] = linhas(c.execute("""SELECT m.*, i.codigo imovel, q.nome inquilino
                    FROM mensalidades m JOIN locacoes l ON l.id=m.locacao_id
                    JOIN imoveis i ON i.id=l.imovel_id JOIN inquilinos q ON q.id=l.inquilino_id
                    WHERE m.status IN ('ABERTA','ATRASADA') AND m.vencimento<=?
                    ORDER BY m.vencimento LIMIT 8""", (limite,)))
                return self.responder(dados)
            mapas = {
                "/api/proprietarios": "SELECT * FROM proprietarios ORDER BY nome",
                "/api/inquilinos": "SELECT * FROM inquilinos ORDER BY nome",
                "/api/imoveis": """SELECT i.*, p.nome proprietario FROM imoveis i
                    JOIN proprietarios p ON p.id=i.proprietario_id ORDER BY i.codigo""",
                "/api/locacoes": """SELECT l.*, i.codigo imovel, i.endereco, q.nome inquilino, p.nome proprietario
                    FROM locacoes l JOIN imoveis i ON i.id=l.imovel_id
                    JOIN inquilinos q ON q.id=l.inquilino_id
                    JOIN proprietarios p ON p.id=i.proprietario_id ORDER BY l.id DESC""",
                "/api/mensalidades": """SELECT m.*, i.codigo imovel, q.nome inquilino
                    FROM mensalidades m JOIN locacoes l ON l.id=m.locacao_id
                    JOIN imoveis i ON i.id=l.imovel_id JOIN inquilinos q ON q.id=l.inquilino_id
                    ORDER BY m.vencimento DESC LIMIT 300""",
            }
            if caminho in mapas:
                return self.responder(linhas(c.execute(mapas[caminho])))
            if caminho.startswith("/api/contrato/"):
                codigo = caminho.rsplit("/", 1)[1]
                contrato = c.execute("""SELECT l.*, i.codigo, i.tipo tipo_imovel, i.endereco, i.cidade, i.uf,
                    q.nome inquilino, q.cpf_cnpj cpf_inquilino,
                    p.nome proprietario, p.cpf_cnpj cpf_proprietario
                    FROM locacoes l JOIN imoveis i ON i.id=l.imovel_id
                    JOIN inquilinos q ON q.id=l.inquilino_id JOIN proprietarios p ON p.id=i.proprietario_id
                    WHERE l.id=?""", (codigo,)).fetchone()
                if not contrato:
                    return self.responder({"erro": "Contrato não encontrado"}, 404)
                return self.responder(dict(contrato))
        return self.responder({"erro": "Rota não encontrada"}, 404)

    def api_post(self, caminho, dados):
        if caminho == "/api/locacoes":
            return self.responder({"id": criar_locacao(dados)}, 201)
        if caminho.startswith("/api/mensalidades/") and caminho.endswith("/pagar"):
            codigo = caminho.split("/")[3]
            with conectar() as c:
                c.execute("""UPDATE mensalidades SET status='PAGA', pago_em=?, valor_pago_centavos=?,
                    forma_pagamento=?, observacoes=? WHERE id=? AND status IN ('ABERTA','ATRASADA')""",
                    (dados.get("pago_em", date.today().isoformat()), centavos(dados["valor_pago"]),
                     dados.get("forma_pagamento", "PIX"), dados.get("observacoes", ""), codigo))
            return self.responder({"ok": True})
        tabelas = {
            "/api/proprietarios": ("proprietarios", ("nome","cpf_cnpj","telefone","email","endereco")),
            "/api/inquilinos": ("inquilinos", ("nome","cpf_cnpj","telefone","email","profissao")),
            "/api/imoveis": ("imoveis", ("proprietario_id","codigo","tipo","endereco","cidade","uf","cep","descricao")),
        }
        if caminho in tabelas:
            tabela, campos = tabelas[caminho]
            valores = [dados.get(campo, "") for campo in campos]
            if not dados.get("nome") and caminho != "/api/imoveis":
                raise ValueError("Informe o nome.")
            with conectar() as c:
                cursor = c.execute(f"INSERT INTO {tabela} ({','.join(campos)}) VALUES ({','.join('?' for _ in campos)})", valores)
                codigo = cursor.lastrowid
            return self.responder({"id": codigo}, 201)
        return self.responder({"erro": "Rota não encontrada"}, 404)


def criar_servidor():
    inicializar()
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    return servidor, f"http://127.0.0.1:{servidor.server_port}"

