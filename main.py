import os
import sys
import threading

from src.servidor import criar_servidor


TITULO = "ImobGestão — Controle Imobiliário"


def main():
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        "--renderer-process-limit=1 --disable-background-networking --no-first-run",
    )
    try:
        import webview
    except ImportError as erro:
        raise SystemExit("Instale as dependências com: python -m pip install -r requirements.txt") from erro

    servidor, endereco = criar_servidor()
    thread = threading.Thread(target=servidor.serve_forever, daemon=True, name="servidor-imobiliaria")
    thread.start()
    try:
        janela = webview.create_window(
            TITULO, endereco, width=1360, height=850, min_size=(1050, 680), maximized=True
        )
        janela.events.closed += servidor.shutdown
        webview.start(gui="edgechromium", debug=False)
    finally:
        servidor.shutdown()
        servidor.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()

