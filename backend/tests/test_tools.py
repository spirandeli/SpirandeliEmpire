"""SpirandeliEmpire OS 3.1 — Tests for Tool Registry & Executors"""

import pytest
from app.tools.registry import tool_registry


@pytest.mark.asyncio
async def test_tool_registry_system_monitor():
    res = await tool_registry.execute("system_monitor", {}, "jeffrey")
    assert res.success is True
    assert "cpu_percent" in res.output
    assert "memory" in res.output
    assert "disk" in res.output


@pytest.mark.asyncio
async def test_tool_registry_file_writer_and_reader():
    test_path = "test_deliverable.txt"
    test_content = "SpirandeliEmpire Autonomous Delivery"
    
    write_res = await tool_registry.execute(
        "file_writer",
        {"path": test_path, "content": test_content},
        "balsini"
    )
    assert write_res.success is True
    assert len(write_res.artifacts_created) > 0

    read_res = await tool_registry.execute(
        "file_reader",
        {"path": test_path},
        "fonseca"
    )
    assert read_res.success is True
    assert read_res.output["content"] == test_content


@pytest.mark.asyncio
async def test_tool_permission_denial():
    # An unauthorized agent attempting to run system_monitor should be rejected
    res = await tool_registry.execute("system_monitor", {}, "voice_agent")
    assert res.success is False
    assert "não tem permissão" in res.error


@pytest.mark.asyncio
async def test_tool_sandbox_blocks_traversal_and_external_paths():
    for bad_path in ["../.env", "../../etc/passwd", "/etc/passwd"]:
        read_res = await tool_registry.execute("file_reader", {"path": bad_path}, "balsini")
        assert read_res.success is False
        assert "Acesso negado" in (read_res.error or "")

        write_res = await tool_registry.execute(
            "file_writer", {"path": bad_path, "content": "pwn"}, "balsini"
        )
        assert write_res.success is False
        assert "Acesso negado" in (write_res.error or "")


@pytest.mark.asyncio
async def test_tool_real_media_and_explicit_tts_block():
    img_res = await tool_registry.execute(
        "image_generator",
        {"path": "artifacts/test_thumb.png", "title": "Audit Test"},
        "designer_agent",
    )
    from pathlib import Path
    assert img_res.success is True
    assert img_res.output["format"] == "png"
    assert img_res.output["width"] == 640
    assert Path(img_res.output["path"]).stat().st_size > 100

    tts_res = await tool_registry.execute(
        "tts_generator",
        {"text": "Teste TTS"},
        "voice_agent",
    )
    assert tts_res.success is False
    assert "BLOCKED" in (tts_res.error or "")


