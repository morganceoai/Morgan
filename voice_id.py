"""
Voice ID — verifica se o locutor é o Vasco antes de enviar ao Claude.
Usa Resemblyzer para criar e comparar embeddings de voz.
"""
import os
import numpy as np
from pathlib import Path

PROFILE_PATH = Path(__file__).parent / "memory" / "voice_profile.npy"
THRESHOLD = 0.72  # similaridade mínima (0-1) para aceitar como Vasco

_encoder = None
_vasco_embedding = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        from resemblyzer import VoiceEncoder
        _encoder = VoiceEncoder()
    return _encoder


def _pcm_to_float(pcm_bytes: bytes) -> np.ndarray:
    """Converte PCM 16-bit para float32 normalizado."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return arr / 32768.0


def enroll_voice(audio_chunks: list[bytes]) -> bool:
    """
    Recebe lista de chunks PCM 16kHz 16-bit e cria o perfil de voz do Vasco.
    Guarda em memory/voice_profile.npy.
    """
    try:
        encoder = _get_encoder()
        combined = b"".join(audio_chunks)
        wav = _pcm_to_float(combined)

        # Resemblyzer precisa de pelo menos 1.6s a 16kHz
        if len(wav) < 16000 * 1.6:
            return False

        embedding = encoder.embed_utterance(wav)
        PROFILE_PATH.parent.mkdir(exist_ok=True)
        np.save(str(PROFILE_PATH), embedding)

        global _vasco_embedding
        _vasco_embedding = embedding
        return True
    except Exception as e:
        print(f"Voice ID enroll erro: {e}")
        return False


def load_profile() -> bool:
    """Carrega o perfil guardado. Retorna True se existir."""
    global _vasco_embedding
    if PROFILE_PATH.exists():
        _vasco_embedding = np.load(str(PROFILE_PATH))
        return True
    return False


def is_vasco(audio_chunks: list[bytes]) -> tuple[bool, float]:
    """
    Verifica se o áudio é do Vasco.
    Retorna (é_vasco, similaridade).
    Se não houver perfil, aceita sempre.
    """
    global _vasco_embedding

    # Sem perfil — aceita tudo
    if _vasco_embedding is None:
        if not load_profile():
            return True, 1.0

    try:
        encoder = _get_encoder()
        combined = b"".join(audio_chunks)
        wav = _pcm_to_float(combined)

        if len(wav) < 16000 * 0.8:
            return True, 1.0  # amostra muito curta — não rejeitar

        embedding = encoder.embed_utterance(wav)

        # Similaridade coseno
        sim = float(np.dot(embedding, _vasco_embedding) /
                    (np.linalg.norm(embedding) * np.linalg.norm(_vasco_embedding)))

        return sim >= THRESHOLD, round(sim, 3)
    except Exception as e:
        print(f"Voice ID check erro: {e}")
        return True, 1.0  # em caso de erro, não bloquear


def has_profile() -> bool:
    return PROFILE_PATH.exists()
