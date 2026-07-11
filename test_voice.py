import os, requests, tempfile, subprocess
from dotenv import load_dotenv
load_dotenv(".env")

api_key = os.getenv("ELEVENLABS_API_KEY")
voice_id = os.getenv("ELEVENLABS_VOICE_ID")
text = "Olá Vasco. Sou o Morgan, o teu assistente pessoal. Como posso ajudar-te hoje?"
model = "eleven_multilingual_v2"

configs = [
    ("3 — stab=0.40, sim=0.95, style=0.35, speed=0.70", {"stability": 0.40, "similarity_boost": 0.95, "style": 0.35, "use_speaker_boost": True, "speed": 0.70}),
    ("4 — stab=0.35, sim=0.98, style=0.35, speed=0.70", {"stability": 0.35, "similarity_boost": 0.98, "style": 0.35, "use_speaker_boost": True, "speed": 0.70}),
]

for label, settings in configs:
    input(f"\nPrime ENTER para ouvir {label}...")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": model, "voice_settings": settings}
    )
    if r.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(r.content)
            subprocess.run(["afplay", f.name])
    else:
        print(f"Erro {r.status_code}: {r.text[:200]}")

print("\nConcluído.")
