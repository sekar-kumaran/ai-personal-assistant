from __future__ import annotations

import argparse
from pprint import pprint

import uvicorn

from src.assistant.engine import assistant
from src.config import settings


def run_demo(message: str) -> None:
    response = assistant.process_message(message)
    pprint(response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Public showcase AI assistant")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="Run the FastAPI server")

    demo_parser = subparsers.add_parser("demo", help="Run a quick CLI demo")
    demo_parser.add_argument("message", nargs="?", default="Create a task to review my portfolio")

    args = parser.parse_args()

    if args.command == "demo":
        run_demo(args.message)
        return

    uvicorn.run(
        "src.api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
