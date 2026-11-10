import math
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
        # Separa hífens igual ao Edge-TTS (ex: 'assentar-se' -> 2 tokens)
        w_list = [w for w in re.findall(r"\w+", narr.replace("-", " "), flags=re.UNICODE) if w]
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
        for k in range(cursor, end_idx):
            if 0 <= k < total_tts_words:
                ptok = (word_timings[k].get("punctuated_text") or "").strip()
                if not ptok.endswith((".", "!", "?")):
                    word_timings[k]["sentence_end"] = False
        if 0 <= end_idx < total_tts_words:
            word_timings[end_idx]["sentence_end"] = True
        cursor = min(total_tts_words - 1, end_idx + 1)

    # Ajusta target_total_duration se a fala real ultrapassar 60s para jamais cortar as cenas finais
    last_word_end = float(word_timings[-1].get("end", target_total_duration)) if word_timings else target_total_duration
    effective_total_duration = max(target_total_duration, round(last_word_end + 0.5, 2))

    # Calcula os pontos de corte (cut_points) exatamente na pausa entre a última palavra da cena i e a primeira da cena i+1
    cut_points: List[float] = [0.0]
    for i in range(num_scenes - 1):
        _, end_i = scene_ranges[i]
        start_next, _ = scene_ranges[i + 1]
        t_end_i = float(word_timings[end_i].get("end", (i + 1) * default_dur))
        t_start_next = float(word_timings[start_next].get("start", t_end_i))
        midpoint = round((t_end_i + max(t_end_i, t_start_next)) / 2.0, 2)
        min_cut = round(cut_points[-1] + 1.0, 2)
        max_cut = round(effective_total_duration - (num_scenes - 1 - i) * 1.0, 2)
        cut_points.append(max(min_cut, min(midpoint, max_cut)))

    cut_points.append(round(effective_total_duration, 2))

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

    # Ajuste fino de centésimos na última cena para fechar exatamente em effective_total_duration
    total_calc = round(sum(item["duration"] for item in scenes_timing), 2)
    diff = round(effective_total_duration - total_calc, 2)
    if abs(diff) > 0 and scenes_timing:
        scenes_timing[-1]["duration"] = round(max(0.5, scenes_timing[-1]["duration"] + diff), 2)
        scenes_timing[-1]["end"] = round(effective_total_duration, 2)

    return scenes_timing


def _build_chunks_from_word_timings(
    word_timings: List[Dict[str, Any]],
    max_words: int = 4,
    max_chars: int = 26,
) -> List[Dict[str, Any]]:
    """
    Agrupa os eventos WordBoundary reais do TTS em blocos equilibrados de 2 a 4 palavras:
    1. Separa estritamente por frase (`sentence_end` ou pausa acústica >= 0.26s) para nunca
       juntar o fim de uma cena com o início da próxima.
    2. Divide cada frase de N palavras em blocos balanceados (ex: 7 palavras -> 4+3, 8 -> 4+4,
       9 -> 3+3+3), eliminando completamente blocos órfãos de 1 palavra ('O', 'A', 'MAIS', 'FIM').
    """
    sentences: List[List[Dict[str, Any]]] = []
    curr_sent: List[Dict[str, Any]] = []

    for item in word_timings:
        raw_w = (item.get("text") or "").strip()
        w = re.sub(r"^[.,!?;:«»\"'()\[\]]+|[.,!?;:«»\"'()\[\]]+$", "", raw_w).strip().upper()
        if not w:
            continue

        w_start = float(item.get("start", 0.0))
        w_end = float(item.get("end", w_start + 0.22))
        punct_tok = (item.get("punctuated_text") or raw_w).strip()
        is_sentence_end = bool(item.get("sentence_end")) or punct_tok.endswith((".", "!", "?", ";", ":", "…"))

        if curr_sent:
            prev_end = float(curr_sent[-1]["end"])
            if (w_start - prev_end) >= 0.26:
                sentences.append(curr_sent)
                curr_sent = []

        curr_sent.append({
            "word": w,
            "start": w_start,
            "end": max(w_end, w_start + 0.12),
            "sentence_end": is_sentence_end,
        })

        if is_sentence_end:
            sentences.append(curr_sent)
            curr_sent = []

    if curr_sent:
        sentences.append(curr_sent)

    # Se alguma frase ficou com apenas 1 palavra (ex: artigo isolado 'O' ou 'A') e a pausa para a próxima
    # for menor que 0.35s, funde com a frase seguinte; se for no final, funde com a anterior
    merged_sentences: List[List[Dict[str, Any]]] = []
    idx_s = 0
    while idx_s < len(sentences):
        s_words = sentences[idx_s]
        if len(s_words) == 1 and idx_s + 1 < len(sentences):
            gap_next = sentences[idx_s + 1][0]["start"] - s_words[-1]["end"]
            if gap_next < 0.35:
                sentences[idx_s + 1] = s_words + sentences[idx_s + 1]
                idx_s += 1
                continue
        if len(s_words) == 1 and merged_sentences:
            gap_prev = s_words[0]["start"] - merged_sentences[-1][-1]["end"]
            if gap_prev < 0.35:
                merged_sentences[-1].extend(s_words)
                idx_s += 1
                continue
        merged_sentences.append(s_words)
        idx_s += 1

    _CONNECTORS = {
        "O", "A", "OS", "AS", "UM", "UMA", "UNS", "UMAS",
        "DE", "DO", "DA", "DOS", "DAS", "EM", "NO", "NA", "NOS", "NAS",
        "PARA", "PRA", "COM", "POR", "SEM", "SOB", "QUE", "E", "OU", "AO", "AOS", "À", "ÀS",
    }

    grouped: List[Dict[str, Any]] = []
    for s_words in merged_sentences:
        n = len(s_words)
        if n == 0:
            continue
        total_chars = sum(len(x["word"]) for x in s_words) + max(0, n - 1)
        num_chunks = max(1, math.ceil(n / max(1, max_words)))
        if num_chunks * max_chars < total_chars and n >= (num_chunks + 1) * 2:
            num_chunks += 1
        # Garante que nenhuma fatia fique com 1 palavra quando n >= 2
        while num_chunks > 1 and (n // num_chunks) < 2:
            num_chunks -= 1

        base_size = n // num_chunks
        rem = n % num_chunks
        sizes = [base_size + (1 if c_idx < rem else 0) for c_idx in range(num_chunks)]

        # Ajuste prosódico: evita terminar um bloco com artigo/preposição solta quando o próximo bloco tem >= 3 palavras
        for c_idx in range(len(sizes) - 1):
            end_pos = sum(sizes[: c_idx + 1]) - 1
            if 0 <= end_pos < n and s_words[end_pos]["word"] in _CONNECTORS and sizes[c_idx] >= 3 and sizes[c_idx + 1] <= max_words:
                sizes[c_idx] -= 1
                sizes[c_idx + 1] += 1

        pos = 0
        for c_idx, c_size in enumerate(sizes):
            slice_words = s_words[pos : pos + c_size]
            pos += c_size
            if not slice_words:
                continue
            c_start = slice_words[0]["start"]
            c_end = max(slice_words[-1]["end"], c_start + 0.25)
            grouped.append({
                "text": " ".join(x["word"] for x in slice_words),
                "words": [dict(x) for x in slice_words],
                "start": round(c_start, 2),
                "end": round(c_end, 2),
                "sentence_end": (c_idx == len(sizes) - 1),
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


def _build_word_highlight_ass_events(
    chunk: Dict[str, Any],
    highlight_color: str,
    primary_color: str,
) -> List[str]:
    """
    Gera eventos ASS com destaque ativo palavra-a-palavra: enquanto o bloco permanece
    na tela, a palavra exatamente falada naquele instante recebe destaque amarelo/dourado
    e escala sutil (\\fscx108\\fscy108), mantendo as demais palavras em branco nítido.
    """
    words = chunk.get("words") or []
    c_start = float(chunk["start"])
    c_end = max(c_start + 0.25, float(chunk["end"]))
    if len(words) <= 1:
        text = chunk["text"]
        return [
            f"Dialogue: 0,{format_ass_timestamp(c_start)},{format_ass_timestamp(c_end)},HormoziYellow,,0,0,0,,{text}"
        ]

    events: List[str] = []
    for w_idx, w_item in enumerate(words):
        w_start = c_start if w_idx == 0 else max(c_start, float(w_item["start"]))
        if w_idx < len(words) - 1:
            next_w_start = float(words[w_idx + 1]["start"])
            w_end = max(w_start + 0.06, min(c_end, next_w_start))
        else:
            w_end = c_end
        if w_end <= w_start:
            continue

        parts: List[str] = []
        for j, token in enumerate(words):
            tok_text = token["word"]
            if j == w_idx:
                parts.append(f"{{\\c{highlight_color}\\fscx108\\fscy108}}{tok_text}{{\\rHormoziWhite}}")
            else:
                parts.append(f"{{\\c{primary_color}}}{tok_text}")
        line_text = " ".join(parts)
        events.append(
            f"Dialogue: 0,{format_ass_timestamp(w_start)},{format_ass_timestamp(w_end)},HormoziWhite,,0,0,0,,{line_text}"
        )
    if not events:
        events.append(
            f"Dialogue: 0,{format_ass_timestamp(c_start)},{format_ass_timestamp(c_end)},HormoziYellow,,0,0,0,,{chunk['text']}"
        )
    return events


def generate_subtitles(
    scenes_timing: List[Dict[str, Any]],
    output_srt_path: str,
    output_ass_path: str,
    highlight_color: str = "&H0024E0FF",  # Amarelo/Dourado em ASS BGR
    primary_color: str = "&H00FFFFFF",    # Branco puro
    outline_color: str = "&H00000000",    # Preto puro
    word_timings: Optional[List[Dict[str, Any]]] = None,
    style_preset: str = "hormozi_karaoke",
) -> Dict[str, Any]:
    """
    Gera arquivos .srt padrão e .ass com tipografia cinemática de alta retenção.
    No modo `hormozi_karaoke` com `word_timings`, destaca exatamente a palavra falada
    em cada milissegundo sem sobreposição nem palavras órfãs.
    """
    srt_lines = []
    ass_dialogues = []
    counter = 1

    # Cabeçalho ASS usando DejaVu Sans (instalada no container) com contorno forte e sombra nítida
    ass_header = f"""[Script Info]
Title: ABVOS Dynamic Subtitles
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

    chunks_count = 0
    if word_timings:
        timed_chunks = _build_chunks_from_word_timings(word_timings, max_words=4)
        chunks_count = len(timed_chunks)
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

            if style_preset == "hormozi_karaoke" and item.get("words"):
                ass_dialogues.extend(
                    _build_word_highlight_ass_events(
                        chunk=item,
                        highlight_color=highlight_color,
                        primary_color=primary_color,
                    )
                )
            else:
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
                chunks_count += 1
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
        "chunks_count": chunks_count,
        "events_count": len(ass_dialogues),
        "style_preset": style_preset,
    }
