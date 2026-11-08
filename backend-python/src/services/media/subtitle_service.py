import re
from typing import List, Dict, Any


def format_srt_timestamp(seconds: float) -> str:
    """
    Converte segundos em formato SRT: HH:MM:SS,mmm
    """
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
    Divide o texto em pequenos blocos de palavras (estilo Alex Hormozi/TikTok)
    para leitura dinâmica em tela cheia.
    """
    cleaned = re.sub(r"\s+", " ", text).strip().upper()
    words = cleaned.split(" ")
    chunks = []
    current = []

    for w in words:
        current.append(w)
        if len(current) >= max_words or w.endswith((".", "!", "?", ",", ";", ":")):
            chunks.append(" ".join(current))
            current = []

    if current:
        chunks.append(" ".join(current))
    return chunks or [text.upper()]


def generate_subtitles(
    scenes_timing: List[Dict[str, Any]],
    output_srt_path: str,
    output_ass_path: str,
    highlight_color: str = "&H0024E0FF",  # Amarelo/Dourado em ASS BGR
    primary_color: str = "&H00FFFFFF",    # Branco puro
    outline_color: str = "&H00000000",    # Preto puro
) -> Dict[str, str]:
    """
    Gera arquivos .srt padrão e .ass com tipografia cinemática de alta retenção (Hormozi style).
    scenes_timing: lista de dicts com {'text': str, 'start': float, 'end': float}
    """
    srt_lines = []
    ass_dialogues = []
    counter = 1

    # Cabeçalho do arquivo ASS com estilos cinemáticos para 1080x1920 (9:16)
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
Style: HormoziYellow,Impact,74,{highlight_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,2,0,1,6,3,2,60,60,340,1
Style: HormoziWhite,Impact,72,{primary_color},&H000000FF,{outline_color},&H80000000,-1,0,0,0,100,100,2,0,1,6,3,2,60,60,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    for scene in scenes_timing:
        scene_text = scene.get("text", "").strip()
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

            # Entrada SRT
            srt_lines.append(f"{counter}")
            srt_lines.append(f"{format_srt_timestamp(chunk_start)} --> {format_srt_timestamp(chunk_end)}")
            srt_lines.append(chunk)
            srt_lines.append("")
            counter += 1

            # Entrada ASS (Alterna estilo para dinamismo visual)
            style_name = "HormoziYellow" if (i % 2 == 0) else "HormoziWhite"
            ass_dialogues.append(
                f"Dialogue: 0,{format_ass_timestamp(chunk_start)},{format_ass_timestamp(chunk_end)},{style_name},,0,0,0,,{chunk}"
            )

    # Grava .srt
    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))

    # Grava .ass
    with open(output_ass_path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(ass_dialogues) + "\n")

    return {
        "srt_path": output_srt_path,
        "ass_path": output_ass_path,
    }

