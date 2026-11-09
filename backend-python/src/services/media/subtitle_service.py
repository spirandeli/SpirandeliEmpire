import re
from typing import List, Dict, Any, Optional
from src.services.media.tts_service import clean_narration_for_tts


def format_srt_timestamp(seconds: float) -> str:
    """
    Converte segundos em formato SRT: HH:MM:SS,mmm
    """
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_ass_timestamp(seconds: float) -> str:
    """
    Converte segundos em formato ASS: H:MM:SS.cc (centésimos de segundo)
    """
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hours:01d}:{minutes:02d}:{secs:02d}.{centis:02d}"


def split_text_into_chunks(text: str, max_words: int = 4) -> List[str]:
    """
    Divide o texto limpo em pequenos blocos de palavras (estilo Alex Hormozi/TikTok)
    para leitura dinâmica em tela cheia.
    """
    cleaned_raw = clean_narration_for_tts(text) or text
    cleaned = re.sub(r"\s+", " ", cleaned_raw).strip().upper()
    if not cleaned:
        return []
    words = [w for w in cleaned.split(" ") if w]
    chunks = []
    current = []

    for w in words:
        current.append(w)
        if len(current) >= max_words or w.endswith((".", "!", "?", ",", ";", ":")):
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))
    return chunks


def _build_chunks_from_word_timings(
    word_timings: List[Dict[str, Any]],
    max_words: int = 4,
) -> List[Dict[str, Any]]:
    """
    Agrupa os eventos WordBoundary reais do TTS em blocos de 3 a 4 palavras,
    preservando os timestamps exatos de início e fim falados pelo narrador.
    """
    grouped: List[Dict[str, Any]] = []
    current_words: List[str] = []
    chunk_start: Optional[float] = None
    chunk_end: float = 0.0

    for item in word_timings:
        w = (item.get("text") or "").strip().upper()
        if not w:
            continue
        w_start = float(item.get("start", 0.0))
        w_end = float(item.get("end", w_start + 0.25))

        if chunk_start is None:
            chunk_start = w_start
        current_words.append(w)
        chunk_end = max(w_end, chunk_start + 0.25)

        if len(current_words) >= max_words or w.endswith((".", "!", "?", ",", ";", ":")):
            grouped.append({
                "text": " ".join(current_words),
                "start": round(chunk_start, 2),
                "end": round(chunk_end, 2),
            })
            current_words = []
            chunk_start = None

    if current_words and chunk_start is not None:
        grouped.append({
            "text": " ".join(current_words),
            "start": round(chunk_start, 2),
            "end": round(max(chunk_end, chunk_start + 0.35), 2),
        })

    # Garante que nenhum bloco sobreponha o próximo e que tenha duração mínima legível
    for idx in range(len(grouped) - 1):
        nxt_start = grouped[idx + 1]["start"]
        if grouped[idx]["end"] > nxt_start:
            grouped[idx]["end"] = nxt_start
        elif nxt_start - grouped[idx]["end"] < 0.18:
            grouped[idx]["end"] = nxt_start

    return grouped


def generate_subtitles(
    scenes_timing: List[Dict[str, Any]],
    output_srt_path: str,
    output_ass_path: str,
    highlight_color: str = "&H0024E0FF",  # Amarelo/Dourado em ASS BGR
    primary_color: str = "&H00FFFFFF",    # Branco puro
    outline_color: str = "&H00000000",    # Preto puro
    word_timings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    Gera arquivos .srt padrão e .ass com tipografia cinemática de alta retenção (Hormozi style).
    Se `word_timings` (WordBoundary do TTS) for fornecido, sincroniza cada bloco de 3-4 palavras
    exatamente com o milissegundo da fala; caso contrário, distribui proporcionalmente por cena.
    """
    srt_lines = []
    ass_dialogues = []
    counter = 1

    # Cabeçalho ASS usando DejaVu Sans (instalada no container) com contorno forte e sombra nítida
    ass_header = f"""[Script Info]
Title: ABVOS Dark Channel Dynamic Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: HormoziYellow,DejaVu Sans,68,{highlight_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,6,3,2,70,70,290,1
Style: HormoziWhite,DejaVu Sans,66,{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,1,0,1,6,3,2,70,70,290,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    if word_timings:
        timed_chunks = _build_chunks_from_word_timings(word_timings, max_words=4)
        for i, item in enumerate(timed_chunks):
            c_text = item["text"]
            c_start = item["start"]
            c_end = item["end"]
            if c_end <= c_start:
                c_end = round(c_start + 0.35, 2)

            srt_lines.append(f"{counter}")
            srt_lines.append(f"{format_srt_timestamp(c_start)} --> {format_srt_timestamp(c_end)}")
            srt_lines.append(c_text)
            srt_lines.append("")
            counter += 1

            style_name = "HormoziYellow" if (i % 2 == 0) else "HormoziWhite"
            ass_dialogues.append(
                f"Dialogue: 0,{format_ass_timestamp(c_start)},{format_ass_timestamp(c_end)},{style_name},,0,0,0,,{c_text}"
            )
    else:
        for scene in scenes_timing:
            scene_text = clean_narration_for_tts(scene.get("text", ""))
            start = float(scene.get("start", 0.0))
            end = float(scene.get("end", start + 3.0))
            total_duration = max(0.5, end - start)

            chunks = split_text_into_chunks(scene_text, max_words=4)
            if not chunks:
                continue

            chunk_duration = total_duration / len(chunks)

            for i, chunk in enumerate(chunks):
                chunk_start = start + (i * chunk_duration)
                chunk_end = start + ((i + 1) * chunk_duration)

                srt_lines.append(f"{counter}")
                srt_lines.append(f"{format_srt_timestamp(chunk_start)} --> {format_srt_timestamp(chunk_end)}")
                srt_lines.append(chunk)
                srt_lines.append("")
                counter += 1

                style_name = "HormoziYellow" if (i % 2 == 0) else "HormoziWhite"
                ass_dialogues.append(
                    f"Dialogue: 0,{format_ass_timestamp(chunk_start)},{format_ass_timestamp(chunk_end)},{style_name},,0,0,0,,{chunk}"
                )

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(ass_dialogues) + "\n")

    return {
        "srt_path": output_srt_path,
        "ass_path": output_ass_path,
    }
