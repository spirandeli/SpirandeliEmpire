import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.routers.media import scan_task_media_dir


@pytest.mark.asyncio
async def test_scan_task_media_dir():
    manifest = scan_task_media_dir(task_id=888, business_id=1)
    assert manifest["has_media"] is True
    assert manifest["task_id"] == 888
    assert manifest["video"] is not None
    assert manifest["video"]["name"] == "video_dark_task_888.mp4"
    assert manifest["video"]["type"] == "video"
    assert manifest["video"]["size_bytes"] > 0
    assert "/api/media/file" in manifest["video"]["url"]
    assert "/api/media/download" in manifest["video"]["download_url"]

    assert manifest["audio"] is not None
    assert manifest["audio"]["name"] == "narration.mp3"
    assert manifest["audio"]["type"] == "audio"

    assert len(manifest["scenes"]) == 20
    assert manifest["scenes"][0]["scene_number"] == 1
    assert len(manifest["subtitles"]) >= 1


@pytest.mark.asyncio
async def test_media_file_streaming_and_download():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Preview / Streaming Inline de Vídeo
        res_video = await ac.get("/api/media/file/biz_1/task_888/video_dark_task_888.mp4")
        assert res_video.status_code == 200
        assert res_video.headers["content-type"] == "video/mp4"
        assert "inline" in res_video.headers.get("content-disposition", "")

        # 2. Download Direto com Attachment
        res_down = await ac.get("/api/media/download/biz_1/task_888/video_dark_task_888.mp4")
        assert res_down.status_code == 200
        assert "attachment" in res_down.headers.get("content-disposition", "")

        # 3. Audio Streaming
        res_audio = await ac.get("/api/media/file/biz_1/task_888/narration.mp3")
        assert res_audio.status_code == 200
        assert res_audio.headers["content-type"] == "audio/mpeg"

        # 4. Imagem de Cena
        res_scene = await ac.get("/api/media/file/biz_1/task_888/scenes/scene_01.jpg")
        assert res_scene.status_code == 200
        assert res_scene.headers["content-type"] == "image/jpeg"

        # 5. Endpoint de busca de mídia por task no router media
        res_task_media = await ac.get("/api/media/tasks/888?business_id=1")
        assert res_task_media.status_code == 200
        data = res_task_media.json()["data"]
        assert data["has_media"] is True
        assert data["video"]["name"] == "video_dark_task_888.mp4"


@pytest.mark.asyncio
async def test_task_media_api_with_auth():
    rand_suffix = uuid.uuid4().hex[:8]
    email = f"media_test_{rand_suffix}@spirandeli.io"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        reg_res = await ac.post(
            "/api/auth/register",
            json={
                "name": "Media Tester",
                "email": email,
                "password": "StrongPassword123!",
                "device_name": "pytest-media",
            },
        )
        assert reg_res.status_code == 201
        token = reg_res.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Cria business e task
        biz_res = await ac.post(
            "/api/businesses",
            json={"name": "Venture Test Media", "type": "affiliate", "niche": "Dark"},
            headers=headers,
        )
        assert biz_res.status_code == 201
        biz_id = biz_res.json()["data"]["id"]

        task_res = await ac.post(
            "/api/tasks",
            json={
                "business_id": biz_id,
                "title": "Produzir Vídeo Dark 60s",
                "priority": "high",
                "assignee": "agent",
            },
            headers=headers,
        )
        assert task_res.status_code == 201
        tid = task_res.json()["data"]["id"]

        # Chama /api/tasks/{task_id}/media
        get_media_res = await ac.get(f"/api/tasks/{tid}/media", headers=headers)
        assert get_media_res.status_code == 200
        data = get_media_res.json()["data"]
        assert data["task_id"] == tid
        assert "has_media" in data

        # Chama também /api/v1/tasks/{task_id}/media
        v1_res = await ac.get(f"/api/v1/tasks/{tid}/media", headers=headers)
        assert v1_res.status_code == 200
        assert v1_res.json()["data"]["task_id"] == tid

