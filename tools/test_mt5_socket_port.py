from __future__ import annotations

import argparse
import socketserver
from datetime import datetime


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(level: str, message: str) -> None:
    print(f"{now()} | {level:<7} | MT5PortTest | {message}", flush=True)


class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        log("INFO", f"conectado peer={peer}")
        try:
            while True:
                data = self.request.recv(4096)
                if not data:
                    break
                preview = data[:64].hex(" ")
                log("INFO", f"bytes_recebidos peer={peer} len={len(data)} hex={preview}")
        except OSError as exc:
            log("WARN", f"erro peer={peer} err={exc}")
        finally:
            log("INFO", f"desconectado peer={peer}")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> int:
    parser = argparse.ArgumentParser(description="Test listener for MT5 SocketConnect on port 45678.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=45678)
    args = parser.parse_args()

    log("INFO", f"escutando em tcp://{args.host}:{args.port}")
    log("INFO", "deixe o EA do MT5 aberto para testar a conexao")
    try:
        with Server((args.host, args.port), Handler) as server:
            server.serve_forever()
    except OSError as exc:
        log("ERROR", f"falha ao abrir porta host={args.host} port={args.port} err={exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
