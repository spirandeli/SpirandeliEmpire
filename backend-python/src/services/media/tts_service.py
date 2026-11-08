import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import httpx
import edge_tts

from src.services.media.media_settings import get_ffprobe_path

logger = logging.getLogger("abvos.media.tts")

# Vozes padrão para Canal Dark
DEFAULT_EDGE_VOICE_PT = "pt-BR-AntonioNeural"  # Voz grave, profunda e imponente
DEFAULT_EDGE_VOICE_EN = "en-US-ChristopherNeural"
ELEVENLABS_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Ex: Rachel ou Adam (pNInz6obpgDQGcFmaJgB)


def get_audio_duration_seconds(audio_path: str) -> float:
    """
    Calcula a duração exata do arquivo de áudio usando ffprobe ou fallback.
    """
    ffprobe = get_ffprobe_path()
    if os.path.exists(ffprobe) and os.access(ffprobe, os.X_OK):
        cmd = [
            ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            val = float(res.stdout.strip())
            return round(val, 2)
        except Exception as e:
            logger.warning(f"Erro ao extrair duração via ffprobe: {e}")

    # Fallback estimativa por tamanho de arquivo mp3 (~160kbps ~ 20KB/s) ou 3s por frase curta
    size = os.path.getsize(audio_path)
    estimated = max(2.5, round(size / 20000, 2))
    return estimated


async def generate_speech_elevenlabs(
    text: str,
    output_path: str,
    api_key: str,
    voice_id: Optional[str] = None,
) -> bool:
    """
    Gera áudio usando a API oficial da ElevenLabs.
    """
    voice = voice_id or os.getenv("ELEVENLABS_VOICE_ID") or "pNInz6obpgDQGcFmaJgB"  # Adam / Voz imponente
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.85,
            "style": 0.55,
            "use_speaker_boost": True,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Áudio ElevenLabs gerado com sucesso: {output_path}")
                return True
            else:
                logger.warning(f"ElevenLabs retornou status {resp.status_code}: {resp.text}")
    except Exception as e:
        logger.error(f"Erro na requisição ElevenLabs: {e}")

    return False


async def generate_speech_edge(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "-2Hz",  # Levemente mais grave para atmosfera de mistério/dark
) -> bool:
    """
    Gera síntese de voz neural com Microsoft Edge TTS (sem limite de requisição, alta fidelidade).
    """
    target_voice = voice or DEFAULT_EDGE_VOICE_PT
    try:
        communicate = edge_tts.Communicate(text=text, voice=target_voice, rate=rate, pitch=pitch)
        await communicate.save(output_path)
        logger.info(f"Áudio Edge-TTS gerado com sucesso ({target_voice}): {output_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao gerar áudio com Edge-TTS: {e}")
        return False


async def synthesize_narration(
    text: str,
    output_path: str,
    elevenlabs_key: Optional[str] = None,
    preferred_voice: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pipeline unificado de TTS:
    Tenta ElevenLabs se a chave estiver configurada; caso contrário ou em caso de erro,
    executa o Edge-TTS Neural com voz imponente de alta fidelidade.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    provider_used = "edge_tts"
    success = False

    effective_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY")
    if effective_key and effective_key.strip():
        logger.info("Tentando síntese via ElevenLabs...")
        success = await generate_speech_elevenlabs(
            text=text,
            output_path=output_path,
            api_key=effective_key,
            voice_id=preferred_voice,
        )
        if success:
            provider_used = "elevenlabs"

    if not success:
        logger.info("Executando síntese de voz via Edge-TTS Neural...")
        success = await generate_speech_edge(
            text=text,
            output_path=output_path,
            voice=preferred_voice or DEFAULT_EDGE_VOICE_PT,
        )
        provider_used = "edge_tts"

    if not success or not os.path.exists(output_path):
        raise RuntimeError(f"Falha ao sintetizar áudio para o texto: {text[:50]}...")

    duration = get_audio_duration_seconds(output_path)
    return {
        "success": True,
        "provider": provider_used,
        "audio_path": output_path,
        "duration_seconds": duration,
    }

