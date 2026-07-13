"""Command-line entry point for the local Nexus runtime."""

from __future__ import annotations

import asyncio
import logging
import sys

from src.app import RuntimeEvent, create_runtime


def _show_event(event: RuntimeEvent) -> None:
    if event.message:
        print(f"[{event.state.value}] {event.message}")


async def run() -> None:
    """Run a minimal interactive text shell over the complete runtime."""
    runtime = create_runtime()
    runtime.subscribe(_show_event)
    await runtime.start()
    try:
        while True:
            prompt = await asyncio.to_thread(input, "You: ")
            if prompt.strip().casefold() in {"exit", "quit", "välju"}:
                break
            if not prompt.strip():
                continue
            answer = await runtime.handle_text(prompt)
            print(f"Nexus: {answer}")
    finally:
        await runtime.stop()


def main() -> None:
    """Configure logging and start Nexus."""
    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "-h"}:
        print("Usage: nexus")
        print("Launch the Nexus local AI assistant runtime.")
        return
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
