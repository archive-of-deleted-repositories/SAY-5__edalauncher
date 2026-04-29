"""CLI: `edalauncher serve` runs the dev Flask server."""

from __future__ import annotations

import sys

from edalauncher.app import create_app


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args or args[0] != "serve":
        print("usage: edalauncher serve [--host 127.0.0.1] [--port 5000]", file=sys.stderr)
        return 2
    host = "127.0.0.1"
    port = 5000
    a = iter(args[1:])
    for tok in a:
        if tok == "--host":
            host = next(a, host)
        elif tok == "--port":
            port = int(next(a, str(port)))
    app = create_app()
    app.run(host=host, port=port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
