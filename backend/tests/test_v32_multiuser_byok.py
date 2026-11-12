"""SpirandeliEmpire OS 3.2 — Multi-User Auth, BYOK, Model Discovery & Router Tests"""

import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import encrypt_secret, decrypt_secret, rotate_encrypted_secret, mask_secret
from app.auth.security import hash_password
from app.auth.rate_limit import reset_rate_limits
from app.database.session import AsyncSessionLocal
from app.database.models import UserModel, AIUsageRecordModel
from app.providers.adapters import DiscoveredModel, CapabilityInfo, AdapterGenerationResult
from app.providers.discovery import model_discovery_service
from app.providers.model_resolver import model_router, ModelResolutionError


@pytest.fixture(autouse=True)
def clear_limits():
    reset_rate_limits()
    yield
    reset_rate_limits()


async def _register_and_login(client: AsyncClient, email: str, password: str = "StrongPass123!") -> tuple[str, dict]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": email,
            "password": password,
            "confirm_password": password,
            "accept_terms": True,
        },
    )
    assert reg.status_code == 201, reg.text
    assert reg.json()["role"] == "USER"
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    data = login.json()
    return data["user"]["id"], {"Authorization": f"Bearer {data['access_token']}"}


@pytest.mark.asyncio
async def test_aes256_gcm_encryption_and_key_rotation():
    secret = "sk-test-super-secret-value-9999"
    enc = encrypt_secret(secret, key_version="v1")
    assert enc.startswith("gcm:v1:")
    assert secret not in enc
    assert decrypt_secret(enc) == secret
    assert mask_secret(secret) == "sk-t****9999"

    rotated_enc, ver = rotate_encrypted_secret(enc, "v2")
    assert ver == "v2"
    assert rotated_enc.startswith("gcm:v2:")
    assert decrypt_secret(rotated_enc) == secret


@pytest.mark.asyncio
async def test_registration_login_refresh_logout_and_password_reset():
    email = f"u_{uuid.uuid4().hex[:8]}@test.local"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Duplicate email rejected
        uid, headers = await _register_and_login(client, email)
        dup = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Dup",
                "email": email,
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "accept_terms": True,
            },
        )
        assert dup.status_code == 409

        # Refresh token rotation
        login2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass123!"})
        rt = login2.json()["refresh_token"]
        ref = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert ref.status_code == 200
        assert ref.json()["refresh_token"] != rt

        # Old refresh token is now invalid
        ref_reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
        assert ref_reuse.status_code == 401

        # Logout
        lo = await client.post("/api/v1/auth/logout", headers=headers)
        assert lo.status_code == 200


@pytest.mark.asyncio
async def test_mandatory_first_access_password_change():
    email = f"admin_boot_{uuid.uuid4().hex[:8]}@test.local"
    uid = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        session.add(
            UserModel(
                id=uid,
                full_name="Bootstrap Admin",
                username=f"adm_{uid[:8]}",
                email=email,
                password_hash=hash_password("140398"),
                role="ADMIN",
                is_active=True,
                must_change_password=True,
            )
        )
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={"email": email, "password": "140398"})
        assert login.status_code == 200
        assert login.json()["must_change_password"] is True
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        # Blocked from normal endpoints until password is changed
        blocked = await client.get("/api/v1/projects/", headers=headers)
        assert blocked.status_code == 403
        assert "PASSWORD_CHANGE_REQUIRED" in blocked.text

        # Weak password rejected (422 by Pydantic min_length or 400 by policy)
        weak = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "140398", "new_password": "weakpass1", "confirm_password": "weakpass1"},
            headers=headers,
        )
        assert weak.status_code == 400

        # Strong 12+ char password accepted
        ok = await client.patch(
            "/api/v1/users/me/password",
            json={
                "current_password": "140398",
                "new_password": "VeryStrongAdminPassword!2026",
                "confirm_password": "VeryStrongAdminPassword!2026",
            },
            headers=headers,
        )
        assert ok.status_code == 200

        # Old session token is revoked (401); new session token from password update is allowed (200)
        old_blocked = await client.get("/api/v1/projects/", headers=headers)
        assert old_blocked.status_code == 401
        new_headers = {"Authorization": f"Bearer {ok.json()['access_token']}"}
        allowed = await client.get("/api/v1/projects/", headers=new_headers)
        assert allowed.status_code == 200


@pytest.mark.asyncio
async def test_multi_user_isolation_credentials_projects_and_catalogs():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, headers_a = await _register_and_login(client, f"a_{uuid.uuid4().hex[:6]}@test.local")
        _, headers_b = await _register_and_login(client, f"b_{uuid.uuid4().hex[:6]}@test.local")

        # User A adds OpenAI credential
        c_res = await client.post(
            "/api/v1/ai-providers/connections",
            json={"provider": "openai", "label": "A OpenAI", "api_key": "sk-user-a-secret-key-1234", "is_default": True},
            headers=headers_a,
        )
        assert c_res.status_code == 201
        cred_a_id = c_res.json()["id"]
        assert "sk-user-a-secret-key-1234" not in c_res.text

        # User B cannot see, test, sync or delete User A's credential
        assert len((await client.get("/api/v1/ai-providers/connections", headers=headers_b)).json()) == 0
        assert (await client.post(f"/api/v1/ai-providers/connections/{cred_a_id}/test", headers=headers_b)).status_code == 404
        assert (await client.delete(f"/api/v1/ai-providers/connections/{cred_a_id}", headers=headers_b)).status_code == 404

        # User A creates project; User B cannot see it
        p_res = await client.post(
            "/api/v1/projects/",
            json={"name": "A Private Project", "description": "Secret", "auto_start_workflow": False},
            headers=headers_a,
        )
        assert p_res.status_code == 201
        proj_a_id = p_res.json()["id"]
        assert (await client.get(f"/api/v1/projects/{proj_a_id}", headers=headers_b)).status_code == 404


@pytest.mark.asyncio
async def test_dynamic_model_discovery_and_router_precedence_and_fallback():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        uid, headers = await _register_and_login(client, f"router_{uuid.uuid4().hex[:6]}@test.local")

        # Create Claude & OpenAI credentials
        c_claude = (await client.post(
            "/api/v1/ai-providers/connections",
            json={"provider": "anthropic", "label": "My Claude", "api_key": "sk-ant-test-12345678", "is_default": True},
            headers=headers,
        )).json()["id"]
        c_openai = (await client.post(
            "/api/v1/ai-providers/connections",
            json={"provider": "openai", "label": "My OpenAI", "api_key": "sk-oai-test-12345678", "is_default": True},
            headers=headers,
        )).json()["id"]

        # Sync mocked dynamic catalogs
        claude_models = [
            DiscoveredModel(
                provider="anthropic",
                model_id="claude-sonnet-4-5",
                display_name="Claude Sonnet 4.5",
                capabilities=[CapabilityInfo(capability="chat", supported=True, source="provider_api")],
            )
        ]
        openai_models = [
            DiscoveredModel(
                provider="openai",
                model_id="gpt-4o",
                display_name="GPT-4o",
                capabilities=[CapabilityInfo(capability="chat", supported=True, source="official_docs")],
            )
        ]
        with patch("app.providers.adapters.AnthropicAdapter.list_models", AsyncMock(return_value=claude_models)):
            sync_c = await model_discovery_service.sync_models(uid, c_claude, force=True)
            assert sync_c["models_count"] == 1
        with patch("app.providers.adapters.OpenAIAdapter.list_models", AsyncMock(return_value=openai_models)):
            sync_o = await model_discovery_service.sync_models(uid, c_openai, force=True)
            assert sync_o["models_count"] == 1

        # Configure global default = OpenAI gpt-4o, Jeffrey = Anthropic claude-sonnet-4-5
        await client.patch(
            "/api/v1/ai-settings/",
            json={"default_provider": "openai", "default_credential_id": c_openai, "default_model_id": "gpt-4o", "fallback_enabled": False},
            headers=headers,
        )
        await client.patch(
            "/api/v1/ai-settings/agents/jeffrey",
            json={"provider": "anthropic", "credential_id": c_claude, "model_id": "claude-sonnet-4-5"},
            headers=headers,
        )

        # Verify precedence: Jeffrey resolves to Claude, Fonseca falls back to user default OpenAI
        sel_j = await model_router.resolver.resolve(user_id=uid, agent_id="jeffrey")
        assert sel_j.provider == "anthropic" and sel_j.model_id == "claude-sonnet-4-5"
        sel_f = await model_router.resolver.resolve(user_id=uid, agent_id="fonseca")
        assert sel_f.provider == "openai" and sel_f.model_id == "gpt-4o"

        # With fallback disabled, primary error MUST raise (no silent Gemini switch)
        with patch("app.providers.adapters.AnthropicAdapter.generate", AsyncMock(side_effect=RuntimeError("Claude 503"))):
            with pytest.raises(RuntimeError, match="Claude 503"):
                await model_router.generate(user_id=uid, prompt="Hello", agent_id="jeffrey")

        # Enable fallback to OpenAI -> succeeds and logs fallback_success
        await client.patch(
            "/api/v1/ai-settings/fallback",
            json={"fallback_enabled": True, "fallback_chain": [{"provider": "openai", "credential_id": c_openai, "model_id": "gpt-4o"}]},
            headers=headers,
        )
        fb_res = AdapterGenerationResult(content="OpenAI fallback reply", input_tokens=10, output_tokens=5, total_tokens=15, model_id="gpt-4o", provider="openai", duration_ms=50)
        with patch("app.providers.adapters.AnthropicAdapter.generate", AsyncMock(side_effect=RuntimeError("Claude 503"))):
            with patch("app.providers.adapters.OpenAIAdapter.generate", AsyncMock(return_value=fb_res)):
                out = await model_router.generate(user_id=uid, prompt="Hello", agent_id="jeffrey")
                assert out["fallback_used"] is True
                assert out["provider"] == "openai"
                assert out["model_id"] == "gpt-4o"


@pytest.mark.asyncio
async def test_session_revocation_and_checkpoint_idor():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pw = "SecAuditPass!2026"
        ua_email = f"sec_a_{uuid.uuid4().hex[:6]}@test.local"
        ub_email = f"sec_b_{uuid.uuid4().hex[:6]}@test.local"
        await client.post("/api/v1/auth/register", json={"full_name": "Sec A", "email": ua_email, "password": pw, "confirm_password": pw, "accept_terms": True})
        await client.post("/api/v1/auth/register", json={"full_name": "Sec B", "email": ub_email, "password": pw, "confirm_password": pw, "accept_terms": True})

        la = (await client.post("/api/v1/auth/login", json={"email": ua_email, "password": pw})).json()
        lb = (await client.post("/api/v1/auth/login", json={"email": ub_email, "password": pw})).json()
        ha = {"Authorization": f"Bearer {la['access_token']}"}
        hb = {"Authorization": f"Bearer {lb['access_token']}"}

        # Start workflow as User A and verify User B cannot read User A's checkpoints (IDOR -> 404)
        wf = await client.post("/api/v1/workflows/start", json={"workflow_type": "development", "user_request": "IDOR test"}, headers=ha)
        assert wf.status_code == 200
        wf_id = wf.json()["workflow_id"]
        assert (await client.get(f"/api/v1/workflows/{wf_id}/checkpoints", headers=ha)).status_code == 200
        assert (await client.get(f"/api/v1/workflows/{wf_id}/checkpoints", headers=hb)).status_code == 404

        # Logout User A -> access token with revoked sid MUST be rejected (401)
        assert (await client.post("/api/v1/auth/logout", headers=ha)).status_code == 200
        assert (await client.get("/api/v1/auth/me", headers=ha)).status_code == 401
