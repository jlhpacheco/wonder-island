#!/usr/bin/env python3
"""connect-tunnel.py — SSH ProxyCommand helper (Wonder Island Vast kit).

Usage (as an ssh ProxyCommand):  connect-tunnel.py <host> <port>

Opens an HTTP CONNECT tunnel to <host>:<port> through the egress proxy
named in the https_proxy environment variable (the route documented in
vast-migration/MAPPING.md: from this VM, outbound SSH must ride the
runtime egress proxy). The proxy's credentials are read from the
environment at runtime and are never written to disk, printed, or passed
on a command line. stdio is relayed to the tunnel once CONNECT succeeds.

Python 3 standard library only.
"""

import base64
import os
import select
import socket
import sys
from urllib.parse import urlparse


def fail(msg: str) -> int:
    print(f"connect-tunnel: {msg}", file=sys.stderr)
    return 1


def main(argv) -> int:
    if len(argv) != 3:
        return fail("usage: connect-tunnel.py <host> <port>")
    host, port = argv[1], int(argv[2])

    raw = os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY") or ""
    proxy = urlparse(raw)
    if not proxy.hostname or not proxy.port:
        return fail("no usable https_proxy in the environment")

    try:
        sock = socket.create_connection((proxy.hostname, proxy.port), timeout=20)
    except OSError as exc:
        return fail(f"cannot reach egress proxy: {exc}")

    lines = [f"CONNECT {host}:{port} HTTP/1.1", f"Host: {host}:{port}"]
    if proxy.username:
        creds = f"{proxy.username}:{proxy.password or ''}".encode("utf-8")
        lines.append("Proxy-Authorization: Basic "
                     + base64.b64encode(creds).decode("ascii"))
    try:
        sock.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                return fail("proxy closed the connection during CONNECT")
            buf += chunk
    except OSError as exc:
        return fail(f"CONNECT exchange failed: {exc}")
    status = buf.split(b"\r\n", 1)[0]
    if b" 200" not in status:
        return fail(f"CONNECT refused: {status!r}")
    leftover = buf.split(b"\r\n\r\n", 1)[1]

    stdin_fd = sys.stdin.buffer.fileno()
    stdout_fd = sys.stdout.buffer.fileno()
    if leftover:
        os.write(stdout_fd, leftover)
    sock.setblocking(False)
    stdin_open = True
    while True:
        rlist = [sock] + ([stdin_fd] if stdin_open else [])
        try:
            ready, _, _ = select.select(rlist, [], [], 60)
        except (OSError, ValueError):
            break
        if not ready:
            continue
        if sock in ready:
            try:
                data = sock.recv(65536)
            except OSError:
                break
            if not data:
                break
            os.write(stdout_fd, data)
        if stdin_open and stdin_fd in ready:
            data = os.read(stdin_fd, 65536)
            if not data:
                stdin_open = False
                try:
                    sock.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
            else:
                try:
                    sock.sendall(data)
                except OSError:
                    break
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
