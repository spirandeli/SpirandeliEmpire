import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import httpx
import edge_tts

from src.services.media.media_settings import get_ffprobe_path

logger = logging.getLogger("abvos.media.tts")

# Vozes padrão para Canal Dark
DEFAULT_EDGE_VOICE_PT = "pt-BR-AntonioNeural"  # Voz grave, profunda e imponente
DEFAULT_EDGE_VOICE_EN = "en-US-ChristopherNeural"
ELEVENLABS_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"


def clean_narration_for_tts(text: str) -> str:
    """
    Higieniza o texto da narração antes de enviá-lo ao motor TTS e às legendas:
    - Remove logs operacionais acidentais (ex: 'Iniciando geração de prompts... (0%)', 'Geração de Assets, TTS e FFmpeg')
    - Remove marcações de direção de palco como [pausa], [música], (fase 2), (pausa dramática)
    - Remove prefixos técnicos ('Cena 01:', 'Parte 1:') e símbolos Markdown (*, #, _)
    """
    if not text:
        return ""

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Ignora linhas de log operacional ou metadados técnicos
        if re.match(
            r"^(?:\[Progresso|(?:Iniciando|Gerando|Renderizando|Concluído|Processando)\b.*?\(\d+%\)|Geração de Assets,\s*TTS\s*e\s*FFmpeg)",
            line,
            re.IGNORECASE,
        ):
            continue
        lines.append(line)

    cleaned = " ".join(lines)
    # Remove instruções entre colchetes: [pausa], [pausa dramática], [som grave], etc.
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    # Remove anotações técnicas entre parênteses: (fase 2), (pausa), (voz grave), (0%), (100%)
    cleaned = re.sub(
        r"\((?:fase\s*\d+|pausa[^)]*|tom[^)]*|voz[^)]*|efeito[^)]*|sfx[^)]*|\d+%)\)",
        " ",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove prefixos de roteiro como "Cena 01:", "CENA 1 -", "Narrador:"
    cleaned = re.sub(
        r"\b(?:cena\s*\d+|parte\s*\d+|narrador|locutor|locução)\s*[:\-–—]\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Remove caracteres markdown
    cleaned = re.sub(r"[*_#`~>]+", "", cleaned)
    # Normaliza espaços e pontuação repetida
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


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

    size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
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
    clean_text = clean_narration_for_tts(text) or text
    voice = voice_id if (voice_id and len(voice_id) == 20 and " " not in voice_id) else (
        os.getenv("ELEVENLABS_VOICE_ID") or "pNInz6obpgDQGcFmaJgB"
    )
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": clean_text,
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
            if resp.status_code == 200 and len(resp.content) > 1024:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                logger.info(f"Áudio ElevenLabs gerado com sucesso: {output_path}")
                return True
            else:
                logger.warning(f"ElevenLabs retornou status {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Erro na requisição ElevenLabs: {e}")

    return False


def _align_word_timings_with_punctuation(
    clean_text: str,
    raw_word_timings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Alinha os eventos WordBoundary do Edge-TTS (que vêm sem pontuação e separam palavras
    hifenizadas como 'assentar-se' em dois eventos 'assentar' e 'se') com os tokens
    originais do roteiro para recuperar pontuação de pausa (vírgulas) e fim de frase
    (ponto final, exclamação, interrogação, dois-pontos), sem deslocar o índice de palavras.
    """
    if not raw_word_timings:
        return []

    # Divide tanto por espaço quanto por hífen preservando a pontuação apenas na última sub-palavra
    raw_tokens: List[str] = []
    for ws_tok in clean_text.split():
        ws_tok = ws_tok.strip()
        if not ws_tok:
            continue
        if "-" in ws_tok and len(ws_tok) > 1:
            parts = [p for p in ws_tok.split("-") if p]
            if len(parts) > 1:
                raw_tokens.extend(parts)
                continue
        raw_tokens.append(ws_tok)

    aligned: List[Dict[str, Any]] = []
    tok_idx = 0
    num_tokens = len(raw_tokens)

    def _norm(s: str) -> str:
        return re.sub(r"[^\w]", "", s, flags=re.UNICODE).lower()

    for idx, item in enumerate(raw_word_timings):
        w_raw = (item.get("text") or "").strip()
        if not w_raw:
            continue
        w_norm = _norm(w_raw)
        matched_token = w_raw

        if w_norm and tok_idx < num_tokens:
            for lookahead in range(min(4, num_tokens - tok_idx)):
                candidate = raw_tokens[tok_idx + lookahead]
                cand_norm = _norm(candidate)
                if not cand_norm:
                    continue
                if cand_norm == w_norm or w_norm == cand_norm:
                    matched_token = candidate
                    tok_idx = tok_idx + lookahead + 1
                    break
                elif len(w_norm) >= 3 and (w_norm in cand_norm or cand_norm in w_norm):
                    matched_token = candidate
                    tok_idx = tok_idx + lookahead + 1
                    break

        sentence_end = matched_token.endswith((".", "!", "?", ";", ":", "…"))
        clause_end = matched_token.endswith((",", "—", "–"))

        # Também detecta fim de frase se houver pausa acústica longa (>= 0.28s) APÓS a palavra atual
        if idx + 1 < len(raw_word_timings):
            next_start = float(raw_word_timings[idx + 1].get("start", 0.0))
            curr_end = float(item.get("end", 0.0))
            if next_start - curr_end >= 0.28:
                sentence_end = True
            elif next_start - curr_end >= 0.16:
                clause_end = True

        aligned.append({
            "text": w_raw,
            "punctuated_text": matched_token,
            "start": float(item.get("start", 0.0)),
            "end": float(item.get("end", 0.0)),
            "sentence_end": sentence_end,
            "clause_end": clause_end,
        })

    return aligned


async def generate_speech_edge_with_timings(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: str = "-3Hz",
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Gera síntese de voz neural com Microsoft Edge TTS extraindo simultaneamente
    os timestamps exatos de cada palavra (WordBoundary) e alinhando-os com a pontuação
    do texto para sincronia perfeita de legendas e cenas.
    """
    clean_text = clean_narration_for_tts(text) or text.strip()
    target_voice = voice if (voice and "Neural" in voice) else DEFAULT_EDGE_VOICE_PT
    raw_word_timings: List[Dict[str, Any]] = []

    # Ajusta cadência automaticamente com base no número de palavras e pausas de pontuação
    # para que roteiros de 20 cenas fiquem entre 54s e 59s (evitando cortes em 60s)
    auto_rate = rate is None
    if auto_rate:
        word_count = len(clean_text.split())
        sentence_count = max(1, sum(1 for ch in clean_text if ch in ".!?"))
        estimated_base_duration = (0.39 * word_count) + (0.45 * sentence_count)
        target_speech_duration = 56.0
        if estimated_base_duration > target_speech_duration:
            needed_pct = int(round(((estimated_base_duration / target_speech_duration) - 1.0) * 100))
            needed_pct = max(6, min(48, needed_pct))
            rate = f"+{needed_pct}%"
        else:
            rate = "+5%"

    try:
        for attempt in range(2):
            raw_word_timings = []
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=target_voice,
                rate=rate,
                pitch=pitch,
                boundary="WordBoundary",
            )
            with open(output_path, "wb") as audio_file:
                async for chunk in communicate.stream():
                    c_type = chunk.get("type")
                    if c_type == "audio":
                        data = chunk.get("data")
                        if data:
                            audio_file.write(data)
                    elif c_type in ("WordBoundary", "SentenceBoundary"):
                        w_text = (chunk.get("text") or "").strip()
                        offset = float(chunk.get("offset") or 0) / 10_000_000.0
                        duration = float(chunk.get("duration") or 0) / 10_000_000.0
                        if w_text:
                            raw_word_timings.append({
                                "text": w_text,
                                "start": round(offset, 3),
                                "end": round(offset + max(0.08, duration), 3),
                            })

            if auto_rate and attempt == 0 and raw_word_timings:
                last_end = float(raw_word_timings[-1].get("end", 0.0))
                if last_end > 59.2:
                    curr_pct = int(re.sub(r"[^\d]", "", rate) or "10")
                    scale = (last_end + 1.0) / 56.5
                    new_pct = min(55, max(curr_pct + 8, int(round(((1.0 + curr_pct / 100.0) * scale - 1.0) * 100))))
                    logger.info(
                        f"Narração ficou com {last_end:.2f}s em rate={rate}; reajustando rate para +{new_pct}% para caber em 60s sem cortes."
                    )
                    rate = f"+{new_pct}%"
                    continue
            break

        if os.path.exists(output_path) and os.path.getsize(output_path) > 512:
            word_timings = _align_word_timings_with_punctuation(clean_text, raw_word_timings)
            logger.info(
                f"Áudio Edge-TTS gerado com sucesso ({target_voice}, rate={rate}, {len(word_timings)} palavras sincronizadas): {output_path}"
            )
            return True, word_timings
    except Exception as e:
        logger.error(f"Erro ao gerar áudio com Edge-TTS: {e}")

    return False, []


async def generate_speech_edge(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: str = "+2%",
    pitch: str = "-3Hz",
) -> bool:
    """
    Wrapper compatível que retorna booleano de sucesso na geração Edge-TTS.
    """
    ok, _ = await generate_speech_edge_with_timings(
        text=text,
        output_path=output_path,
        voice=voice,
        rate=rate,
        pitch=pitch,
    )
    return ok


async def synthesize_narration(
    text: str,
    output_path: str,
    elevenlabs_key: Optional[str] = None,
    preferred_voice: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pipeline unificado de TTS:
    Higieniza o roteiro falado, tenta ElevenLabs se chave configurada, ou executa
    Edge-TTS Neural retornando também os timestamps palavra por palavra (word_timings).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_text = clean_narration_for_tts(text) or text.strip()
    provider_used = "edge_tts"
    success = False
    word_timings: List[Dict[str, Any]] = []

    effective_key = elevenlabs_key or os.getenv("ELEVENLABS_API_KEY")
    if effective_key and effective_key.strip():
        logger.info("Tentando síntese via ElevenLabs...")
        success = await generate_speech_elevenlabs(
            text=clean_text,
            output_path=output_path,
            api_key=effective_key,
            voice_id=preferred_voice,
        )
        if success:
            provider_used = "elevenlabs"

    if not success:
        logger.info("Executando síntese de voz neural via Edge-TTS com captura de WordBoundary...")
        success, word_timings = await generate_speech_edge_with_timings(
            text=clean_text,
            output_path=output_path,
            voice=preferred_voice or DEFAULT_EDGE_VOICE_PT,
        )
        provider_used = "edge_tts"

    if not success or not os.path.exists(output_path):
        raise RuntimeError(f"Falha ao sintetizar áudio para o texto: {clean_text[:50]}...")

    duration = get_audio_duration_seconds(output_path)
    return {
        "success": True,
        "provider": provider_used,
        "audio_path": output_path,
        "duration_seconds": duration,
        "clean_text": clean_text,
        "word_timings": word_timings,
    }
