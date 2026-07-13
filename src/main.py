"""Command-line entry point for the local Nexus runtime."""

from __future__ import annotations

import asyncio
import logging
import sys
import threading

from src.app import RuntimeEvent, create_runtime
from src.ui.workspace import WorkspaceApp, create_workspace


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


def _run_ui() -> None:
    """Launch the graphical Nexus workspace."""
    runtime = create_runtime()
    app = create_workspace(runtime=runtime)

    loop = asyncio.new_event_loop()
    runtime_ready = threading.Event()
    runtime_error: list[Exception] = []

    def _start_background() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(runtime.start())
            runtime_ready.set()
        except Exception as exc:
            runtime_error.append(exc)
            runtime_ready.set()

    thread = threading.Thread(target=_start_background, daemon=True)
    thread.start()
    runtime_ready.wait(timeout=30)

    if runtime_error:
        print(f"Nexus Runtime error: {runtime_error[0]}", flush=True)

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        if loop.is_running():
            loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)


def main() -> None:
    """Configure logging and start Nexus."""
    if len(sys.argv) > 1 and sys.argv[1] in {"--help", "-h"}:
        print("Usage: nexus [--ui]")
        print("Launch the Nexus local AI assistant runtime.")
        print("  --ui    Start the graphical workspace instead of the text shell")
        return
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
        datefmt="%H:%M:%S",
    )
    for name in ("src", "piper", "faster_whisper", "httpx", "uvicorn", "chromadb", "ollama"):
        logging.getLogger(name).setLevel(logging.DEBUG)
    if len(sys.argv) > 1 and sys.argv[1] == "--ui":
        _run_ui()
        return
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
