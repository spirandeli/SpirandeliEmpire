"""
SpirandeliEmpire OS - TikTok Shop Affiliate Worker
Orquestra o pipeline completo de geração de vídeo para um produto TikTok Shop:
  1. Chama Ollama para gerar o roteiro de venda
  2. Chama XTTS v2 (ou fallback Piper) para sintetizar a narração
  3. Invoca o render_tiktok_video.py para compor o vídeo final
  4. Registra o job via API do core para aprovação humana

Chamado pelo n8n via Execute Command ou importado como módulo.
"""

import os
import json
import logging
import subprocess
import tempfile
import requests

logger = logging.getLogger("TikTokShopWorker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Configurações (via variáveis de ambiente) ---
OLLAMA_URL       = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL     = os.getenv("LLAMA_MODEL", "llama3:8b")
XTTS_URL         = os.getenv("XTTS_API_URL", "http://xtts-api:5021/tts")
XTTS_REF_AUDIO   = os.getenv("XTTS_REFERENCE_AUDIO", "/var/spirandeli/businesses/tiktok-shop-afiliados/assets/voice_reference.wav")
RENDER_SCRIPT    = os.getenv("TIKTOK_RENDER_SCRIPT", "/opt/ai-engine/video-processing/render_tiktok_video.py")
BROLL_DIR        = os.getenv("TIKTOK_BROLL_DIR", "/var/spirandeli/businesses/tiktok-shop-afiliados/content/broll")
OUTPUT_DIR       = os.getenv("TIKTOK_OUTPUT_DIR", "/var/spirandeli/businesses/tiktok-shop-afiliados/content/renders")
CORE_API_URL     = os.getenv("JEFFREY_API_URL", "http://core-app/api/v1")

SCRIPT_PROMPT_TEMPLATE = (
    "Escreva um roteiro curto e viral de 30 segundos para o TikTok vendendo o produto: {product_name}. "
    "Preço: {product_price}. "
    "Use um gancho de atenção impactante nos primeiros 3 segundos. "
    "Tom persuasivo, linguagem informal e brasileira. "
    "Inclua uma chamada para ação no final (ex: 'Corre pegar o seu!' ou 'Link na bio!'). "
    "Retorne apenas o texto do roteiro, sem títulos, marcações ou comentários."
)


def generate_script(product_name: str, product_price: str) -> str | None:
    """Gera roteiro de venda via Ollama (Llama 3 8B)."""
    prompt = SCRIPT_PROMPT_TEMPLATE.format(
        product_name=product_name,
        product_price=product_price
    )
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.85, "num_predict": 300}
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        script = resp.json().get("response", "").strip()
        logger.info(f"Roteiro gerado ({len(script)} chars) para '{product_name}'")
        return script
    except Exception as e:
        logger.error(f"Falha ao gerar roteiro via Ollama: {e}")
        return None


def synthesize_voice_xtts(script: str, output_path: str) -> bool:
    """Sintetiza narração via XTTS v2 com clonagem de voz de referência."""
    if not os.path.exists(XTTS_REF_AUDIO):
        logger.warning(f"Áudio de referência XTTS não encontrado: {XTTS_REF_AUDIO}. Usando fallback Piper.")
        return _fallback_piper_tts(script, output_path)

    try:
        with open(XTTS_REF_AUDIO, "rb") as ref_f:
            files = {"speaker_wav": ("voice_reference.wav", ref_f, "audio/wav")}
            data  = {"text": script, "language": "pt"}
            resp  = requests.post(XTTS_URL, files=files, data=data, timeout=180)
            resp.raise_for_status()

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(resp.content)

        logger.info(f"Narração XTTS gerada: {output_path}")
        return True
    except Exception as e:
        logger.warning(f"XTTS falhou ({e}). Tentando fallback Piper TTS.")
        return _fallback_piper_tts(script, output_path)


def _fallback_piper_tts(script: str, output_path: str) -> bool:
    """Fallback: sintetiza voz com Piper TTS local (CPU, sem clonagem)."""
    # Importa o wrapper local do Piper
    try:
        import sys
        sys.path.insert(0, "/opt/ai-engine/text-to-speech")
        from piper_tts import synthesize_speech
        return synthesize_speech(script, output_path)
    except Exception as e:
        logger.error(f"Fallback Piper TTS também falhou: {e}")
        return False


def _select_broll(category: str = "generic") -> str | None:
    """Seleciona um arquivo de b-roll disponível no diretório do negócio."""
    broll_subdir = os.path.join(BROLL_DIR, category)
    search_dirs = [broll_subdir, BROLL_DIR]

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        videos = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith((".mp4", ".mov", ".webm"))
        ]
        if videos:
            import random
            chosen = random.choice(videos)
            logger.info(f"B-roll selecionado: {chosen}")
            return chosen

    logger.error(f"Nenhum b-roll encontrado em: {BROLL_DIR}")
    return None


def run_pipeline(product: dict) -> dict:
    """
    Executa o pipeline completo para um produto TikTok Shop.

    Args:
        product: dict com chaves: name, price, affiliate_link, category (opcional)

    Returns:
        dict com status e caminho do vídeo renderizado.
    """
    product_name  = product.get("name", "Produto Incrível")
    product_price = product.get("price", "Por tempo limitado!")
    category      = product.get("category", "generic")
    slug          = product_name.lower().replace(" ", "-")[:40]

    result = {"product": product_name, "status": "failed", "output_video": None}

    # Passo 1: Gerar roteiro
    logger.info(f"[1/4] Gerando roteiro para: {product_name}")
    script = generate_script(product_name, product_price)
    if not script:
        return result

    # Passo 2: Sintetizar voz
    logger.info(f"[2/4] Sintetizando narração...")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False, dir="/tmp") as tmp_audio:
        audio_path = tmp_audio.name

    if not synthesize_voice_xtts(script, audio_path):
        return result

    # Passo 3: Selecionar b-roll
    logger.info(f"[3/4] Selecionando b-roll...")
    broll_path = _select_broll(category)
    if not broll_path:
        return result

    # Passo 4: Renderizar vídeo
    logger.info(f"[4/4] Renderizando vídeo final...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_video = os.path.join(OUTPUT_DIR, f"{slug}.mp4")

    render_cmd = [
        "python3", RENDER_SCRIPT,
        audio_path, broll_path, output_video, script
    ]
    try:
        proc = subprocess.run(render_cmd, check=True, capture_output=True, text=True, timeout=600)
        logger.info(f"Render concluído: {output_video}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Falha no render: {e.stderr}")
        return result
    finally:
        # Limpa áudio temporário
        if os.path.exists(audio_path):
            os.unlink(audio_path)

    result["status"] = "pending_review"
    result["output_video"] = output_video
    result["script"] = script

    logger.info(f"✅ Pipeline concluído. Vídeo aguardando revisão: {output_video}")
    return result


if __name__ == "__main__":
    # Exemplo de execução direta para testes
    test_product = {
        "name": "Massageador Elétrico Portátil",
        "price": "R$ 49,90",
        "affiliate_link": "https://tiktok.com/shop/product/example",
        "category": "saude-beleza"
    }
    result = run_pipeline(test_product)
    print(json.dumps(result, indent=2, ensure_ascii=False))

