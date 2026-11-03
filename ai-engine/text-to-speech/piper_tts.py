"""
SpirandeliEmpire OS - Piper Neural Local TTS Wrapper
Generates fast, high quality Portuguese (Brazil) voiceovers with 0 external API costs.
"""
import os
import subprocess
import logging

logger = logging.getLogger("PiperTTS")

DEFAULT_MODEL_PATH = os.getenv("PIPER_VOICE_MODEL", "/opt/ai-engine/models/pt_BR-faber-medium.onnx")
PIPER_BINARY = os.getenv("PIPER_TTS_BINARY", "piper")

def synthesize_speech(text: str, output_wav_path: str, model_path: str = DEFAULT_MODEL_PATH) -> bool:
    """
    Synthesizes speech using local Piper binary on CPU.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    
    cmd = [
        PIPER_BINARY,
        "--model", model_path,
        "--output_file", output_wav_path
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=text)
        
        if process.returncode == 0 and os.path.exists(output_wav_path):
            logger.info(f"Audio voiceover generated successfully: {output_wav_path}")
            return True
        else:
            logger.error(f"Piper TTS generation failed: {stderr}")
            return False
    except Exception as e:
        logger.error(f"Failed to execute Piper TTS: {e}")
        return False

