"""SpirandeliEmpire OS 3.1 — Tests for Official 14 Agents"""

import pytest
from app.agents.registry import OFFICIAL_AGENTS, get_agent_by_id


def test_official_agents_count():
    assert len(OFFICIAL_AGENTS) == 14, f"Expected 14 official agents, found {len(OFFICIAL_AGENTS)}"


def test_agent_identities_and_rooms():
    required_ids = [
        "jeffrey", "fonseca", "balsini", "jarvis", "noe", "ford", "murphy",
        "script_agent", "voice_agent", "subtitle_agent", "clipador_agent",
        "news_agent", "designer_agent", "video_agent"
    ]
    for agent_id in required_ids:
        agent = get_agent_by_id(agent_id)
        assert agent is not None
        assert agent.id == agent_id
        assert len(agent.name) > 0
        assert len(agent.system_prompt) > 20
        assert agent.office_room in [
            "ceo_office", "development", "content_office",
            "audiovisual_office", "server_room", "qa_office"
        ]

