import asyncio, sys
from pathlib import Path
import pytest
from src.tools.commands import RunCommandTool
from src.tools.models import ToolError, ToolValidationError

def python_tool(root: Path, max_output: int = 1024) -> RunCommandTool:
    return RunCommandTool(root, {sys.executable}, max_output=max_output)

def test_requires_array_allowlist_and_sandboxed_cwd(tmp_path):
    tool = python_tool(tmp_path)
    for arguments in ({"argv": "python -V"}, {"argv": ["not-allowed"]},
                      {"argv": [sys.executable], "cwd": "../"}):
        with pytest.raises(ToolValidationError): tool.validate(arguments)
    tool.validate({"argv": [sys.executable, "-c", "print('; rm harmless')"]})

@pytest.mark.asyncio
async def test_output_is_limited_and_missing_executable_is_structured(tmp_path):
    tool = python_tool(tmp_path, 20)
    result = await tool.execute({"argv": [sys.executable, "-c", "print('x'*100)"]})
    assert result["truncated"] and len(result["stdout"]) <= 20
    missing = RunCommandTool(tmp_path, {"definitely-missing"})
    with pytest.raises(ToolError) as error:
        await missing.execute({"argv": ["definitely-missing"]})
    assert error.value.code == "missing_executable"

@pytest.mark.asyncio
async def test_timeout_and_cancellation_stop_process(tmp_path):
    tool = python_tool(tmp_path)
    with pytest.raises(ToolError) as error:
        await tool.execute({"argv": [sys.executable, "-c", "import time; time.sleep(5)"], "timeout": .05})
    assert error.value.code == "timeout"
    task = asyncio.create_task(tool.execute({"argv": [sys.executable, "-c", "import time; time.sleep(5)"]}))
    await asyncio.sleep(.05); task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
