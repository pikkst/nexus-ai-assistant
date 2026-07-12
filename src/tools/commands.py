"""Allowlisted, shell-free local command execution."""
from __future__ import annotations
import asyncio, os, time
from pathlib import Path
from typing import Any
from .filesystem import _RootedTool
from .models import RiskLevel, ToolError, ToolValidationError

class CommandExecutor:
    def __init__(self, root: Path | str, allowed: set[str], *, max_output: int = 131_072) -> None:
        self.root, self.allowed, self.max_output = Path(root).resolve(), allowed, max_output
    async def run(self, argv: list[str], cwd: Path, timeout: float) -> dict[str, Any]:
        started = time.monotonic()
        try:
            process = await asyncio.create_subprocess_exec(*argv, cwd=cwd, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE, creationflags=0x08000000 if os.name == "nt" else 0)
        except FileNotFoundError as exc:
            raise ToolError(f"executable not found: {argv[0]}", code="missing_executable") from exc
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except asyncio.CancelledError:
            process.kill(); await process.wait(); raise
        except TimeoutError:
            process.kill(); await process.wait()
            raise ToolError("command timed out", code="timeout")
        total = len(stdout) + len(stderr); truncated = total > self.max_output
        if truncated:
            stdout = stdout[:self.max_output]; stderr = stderr[:max(0, self.max_output - len(stdout))]
        return {"argv": argv, "exit_code": process.returncode, "stdout": stdout.decode(errors="replace"),
            "stderr": stderr.decode(errors="replace"), "duration_seconds": round(time.monotonic()-started, 3),
            "truncated": truncated}

class RunCommandTool(_RootedTool):
    name, description, risk = "development.run_command", "Run an allowlisted command without a shell.", RiskLevel.LOCAL_WRITE
    parameters = {"type": "object", "properties": {"argv": {"type": "array", "items": {"type": "string"}},
        "cwd": {"type": "string"}, "timeout": {"type": "number"}}, "required": ["argv"], "additionalProperties": False}
    def __init__(self, root: Path | str, allowed: set[str], *, max_output: int = 131_072) -> None:
        super().__init__(root); self.executor = CommandExecutor(root, allowed, max_output=max_output)
    def validate(self, arguments: dict[str, Any]) -> None:
        argv = arguments.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise ToolValidationError("argv must be a non-empty array of strings")
        requested = Path(argv[0])
        names = {item.casefold() for item in self.executor.allowed if Path(item).name == item}
        paths = {str(Path(item).resolve()).casefold() for item in self.executor.allowed if Path(item).name != item}
        if ((requested.name != argv[0] or requested.is_absolute()) and str(requested.resolve()).casefold() not in paths) or (
            requested.name == argv[0] and argv[0].casefold() not in names):
            raise ToolValidationError("executable is not allowlisted")
        if not self._resolve(arguments.get("cwd", ".")).is_dir(): raise ToolValidationError("cwd must be a directory")
        if float(arguments.get("timeout", 30)) <= 0: raise ToolValidationError("timeout must be positive")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.executor.run(arguments["argv"], self._resolve(arguments.get("cwd", ".")),
                                       float(arguments.get("timeout", 30)))

class EvidenceCommandTool(RunCommandTool):
    def __init__(self, root: Path | str, name: str, description: str, argv: list[str], risk: RiskLevel) -> None:
        super().__init__(root, {argv[0]}); self.name, self.description, self.argv, self.risk = name, description, argv, risk
        self.parameters = {"type": "object", "properties": {}, "additionalProperties": False}
    def validate(self, arguments: dict[str, Any]) -> None:
        if arguments: raise ToolValidationError(f"{self.name} does not accept arguments")
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self.executor.run(self.argv, self.root, 60); result["passed"] = result["exit_code"] == 0
        return result
