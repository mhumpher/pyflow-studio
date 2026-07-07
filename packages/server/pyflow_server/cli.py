"""The `pyflow` command: `studio` (launch server), `run` (headless), `validate`."""
from __future__ import annotations

import argparse
import json
import threading
import webbrowser


def main() -> None:
    parser = argparse.ArgumentParser(prog="pyflow", description="Pyflow visual analytics")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_studio = sub.add_parser("studio", help="Launch the local Studio server")
    p_studio.add_argument("--host", default="127.0.0.1")
    p_studio.add_argument("--port", type=int, default=8710)
    p_studio.add_argument("--no-browser", action="store_true")

    p_run = sub.add_parser("run", help="Run a .pyflow workflow headless")
    p_run.add_argument("file")
    p_run.add_argument("--to", default=None, help="Run only up to this node id")

    p_val = sub.add_parser("validate", help="Validate a .pyflow workflow")
    p_val.add_argument("file")

    args = parser.parse_args()

    if args.cmd == "studio":
        import uvicorn

        url = f"http://{args.host}:{args.port}"
        if not args.no_browser:
            threading.Timer(1.2, lambda: webbrowser.open(url)).start()
        print(f"Pyflow Studio -> {url}")
        uvicorn.run("pyflow_server.app:app", host=args.host, port=args.port)

    elif args.cmd == "run":
        from pyflow_engine import Runner, WorkflowDoc

        doc = WorkflowDoc.load(args.file)
        Runner(emit=lambda e: print(json.dumps(e))).run(doc, to=args.to)

    elif args.cmd == "validate":
        from pyflow_engine import WorkflowDoc, build_default_registry
        from pyflow_engine.document import topo_sort

        doc = WorkflowDoc.load(args.file)
        reg = build_default_registry()
        try:
            topo_sort(doc)
        except ValueError as exc:
            print(f"INVALID: {exc}")
            raise SystemExit(1)

        errors = []
        for n in doc.nodes:
            try:
                reg.get(n.type).Config.model_validate(n.config)
            except Exception as exc:
                errors.append(f"  - {n.id} ({n.type}): {exc}")
        if errors:
            print("INVALID:")
            print("\n".join(errors))
            raise SystemExit(1)
        print(f"OK: {doc.name} ({len(doc.nodes)} nodes, {len(doc.edges)} edges)")


if __name__ == "__main__":
    main()
