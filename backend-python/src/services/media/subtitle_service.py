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
        has_break = w.endswith((".", "!", "?", ",", ";", ":", "—", "–"))
        clean_w = re.sub(r"^[.,!?;:«»\"'()\[\]]+|[.,!?;:«»\"'()\[\]]+$", "", w).strip()
        if clean_w:
            current.append(clean_w)
        if len(current) >= max_words or has_break:
            if current:
                chunks.append(" ".join(current))
                current = []

    if current:
        chunks.append(" ".join(current))
    return chunks


def compute_scene_timings_from_words(
    scenes: List[Dict[str, Any]],
    word_timings: List[Dict[str, Any]],
    target_total_duration: float = 60.0,
) -> List[Dict[str, Any]]:
    """
    Mapeia as frases das 20 cenas diretamente nos timestamps reais (WordBoundary) do TTS:
    1. Marca obrigatoriamente `sentence_end = True` na última palavra de cada cena para que a
       legenda nunca junte o final de uma cena com o início da próxima.
    2. Calcula o `start`, `end` e `duration` exatos de cada cena para que a troca de imagem no
       FFmpeg aconteça exatamente na pausa entre as frases narradas, totalizando `target_total_duration`.
    """
    num_scenes = len(scenes)
    if num_scenes == 0:
        return []

    default_dur = round(target_total_duration / num_scenes, 2)
    if not word_timings:
        result = []
        acc = 0.0
        for i, sc in enumerate(scenes):
            dur = default_dur if i < num_scenes - 1 else round(max(0.5, target_total_duration - acc), 2)
            result.append({
                "scene_number": i + 1,
                "text": clean_narration_for_tts(sc.get("narration") or sc.get("on_screen_text") or ""),
                "start": round(acc, 2),
                "end": round(acc + dur, 2),
                "duration": dur,
            })
            acc += dur
        return result

    total_tts_words = len(word_timings)
    scene_word_counts = []
    for sc in scenes:
        narr = clean_narration_for_tts(sc.get("narration") or "")
        w_list = [w for w in re.findall(r"\w+", narr, flags=re.UNICODE) if w]
        scene_word_counts.append(max(1, len(w_list)))

    total_expected_words = max(1, sum(scene_word_counts))
    scene_ranges: List[tuple[int, int]] = []
    cursor = 0
    acc_expected = 0

    for i, count in enumerate(scene_word_counts):
        acc_expected += count
        if i == num_scenes - 1:
            end_idx = total_tts_words - 1
        else:
            target_idx = int(round((acc_expected / total_expected_words) * total_tts_words)) - 1
            max_allowed = max(cursor, total_tts_words - (num_scenes - 1 - i) - 1)
            end_idx = max(cursor, min(target_idx, max_allowed))
        scene_ranges.append((cursor, end_idx))
        if 0 <= end_idx < total_tts_words:
            word_timings[end_idx]["sentence_end"] = True
        cursor = min(total_tts_words - 1, end_idx + 1)

    # Calcula os pontos de corte (cut_points) exatamente na pausa entre a última palavra da cena i e a primeira da cena i+1
    cut_points: List[float] = [0.0]
    for i in range(num_scenes - 1):
        _, end_i = scene_ranges[i]
        start_next, _ = scene_ranges[i + 1]
        t_end_i = float(word_timings[end_i].get("end", (i + 1) * default_dur))
        t_start_next = float(word_timings[start_next].get("start", t_end_i))
        midpoint = round((t_end_i + max(t_end_i, t_start_next)) / 2.0, 2)
        # Garante duração mínima de 1.2s por cena e folga para as cenas restantes
        min_cut = round(cut_points[-1] + 1.2, 2)
        max_cut = round(target_total_duration - (num_scenes - 1 - i) * 1.2, 2)
        cut_points.append(max(min_cut, min(midpoint, max_cut)))

    cut_points.append(round(target_total_duration, 2))

    scenes_timing: List[Dict[str, Any]] = []
    for i, sc in enumerate(scenes):
        s_start = round(cut_points[i], 2)
        s_end = round(cut_points[i + 1], 2)
        s_dur = round(max(0.5, s_end - s_start), 2)
        scenes_timing.append({
            "scene_number": i + 1,
            "text": clean_narration_for_tts(sc.get("narration") or sc.get("on_screen_text") or ""),
            "start": s_start,
            "end": s_end,
            "duration": s_dur,
        })

    # Ajuste fino de centésimos na última cena para fechar exatamente em target_total_duration
    total_calc = round(sum(item["duration"] for item in scenes_timing), 2)
    diff = round(target_total_duration - total_calc, 2)
    if abs(diff) > 0 and scenes_timing:
        scenes_timing[-1]["duration"] = round(max(0.5, scenes_timing[-1]["duration"] + diff), 2)
        scenes_timing[-1]["end"] = round(target_total_duration, 2)

    return scenes_timing


def _build_chunks_from_word_timings(
    word_timings: List[Dict[str, Any]],
    max_words: int = 4,
    max_chars: int = 26,
) -> List[Dict[str, Any]]:
    """
    Agrupa os eventos WordBoundary reais do TTS em blocos curtos (3 a 4 palavras, máx ~26 caracteres),
    preservando os timestamps exatos de início e fim falados pelo narrador e NUNCA misturando
    o fim de uma frase com o começo da próxima.
    """
    grouped: List[Dict[str, Any]] = []
    current_words: List[str] = []
    chunk_start: Optional[float] = None
    chunk_end: float = 0.0

    for item in word_timings:
        raw_w = (item.get("text") or "").strip()
        # Remove pontuação residual nas bordas para exibição limpa estilo Hormozi
        w = re.sub(r"^[.,!?;:«»\"'()\[\]]+|[.,!?;:«»\"'()\[\]]+$", "", raw_w).strip().upper()
        if not w:
            continue

        w_start = float(item.get("start", 0.0))
        w_end = float(item.get("end", w_start + 0.22))
        punct_tok = (item.get("punctuated_text") or raw_w).strip()
        is_sentence_end = bool(item.get("sentence_end")) or punct_tok.endswith((".", "!", "?", ";", ":", "…"))
        is_clause_end = bool(item.get("clause_end")) or punct_tok.endswith((",", "—", "–"))

        # Se já existe um bloco aberto e houve pausa acústica (>= 0.20s) ou se adicionar esta
        # palavra estourar o limite visual de caracteres, fecha o bloco anterior ANTES de incluir a palavra atual
        current_char_len = sum(len(cw) for cw in current_words) + max(0, len(current_words) - 1)
        if current_words and chunk_start is not None:
            gap_before = w_start - chunk_end
            would_exceed_chars = (current_char_len + 1 + len(w)) > max_chars and len(current_words) >= 2
            if gap_before >= 0.20 or would_exceed_chars:
                grouped.append({
                    "text": " ".join(current_words),
                    "start": round(chunk_start, 2),
                    "end": round(max(chunk_end, chunk_start + 0.22), 2),
                    "sentence_end": gap_before >= 0.20,
                })
                current_words = []
                chunk_start = None

        if chunk_start is None:
            chunk_start = w_start
        current_words.append(w)
        chunk_end = max(w_end, chunk_start + 0.20)

        # Fecha o bloco imediatamente ao atingir fim de frase, vírgula (com >= 2 palavras) ou limite de palavras
        should_close = (
            is_sentence_end
            or (is_clause_end and len(current_words) >= 2)
            or len(current_words) >= max_words
        )
        if should_close:
            grouped.append({
                "text": " ".join(current_words),
                "start": round(chunk_start, 2),
                "end": round(max(chunk_end, chunk_start + 0.22), 2),
                "sentence_end": is_sentence_end,
            })
            current_words = []
            chunk_start = None

    if current_words and chunk_start is not None:
        grouped.append({
            "text": " ".join(current_words),
            "start": round(chunk_start, 2),
            "end": round(max(chunk_end, chunk_start + 0.30), 2),
            "sentence_end": True,
        })

    # Garante que o primeiro bloco apareça desde o início (0.0s) se a fala começar nos primeiros 300ms
    if grouped and grouped[0]["start"] <= 0.30:
        grouped[0]["start"] = 0.0

    # Garante que nenhum bloco sobreponha o próximo e une micro-gaps dentro da mesma frase para evitar flicker
    for idx in range(len(grouped) - 1):
        nxt_start = grouped[idx + 1]["start"]
        if grouped[idx]["end"] > nxt_start:
            grouped[idx]["end"] = nxt_start
        elif not grouped[idx].get("sentence_end") and (nxt_start - grouped[idx]["end"] < 0.22):
            grouped[idx]["end"] = nxt_start
        elif grouped[idx].get("sentence_end") and (nxt_start - grouped[idx]["end"] < 0.12):
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
