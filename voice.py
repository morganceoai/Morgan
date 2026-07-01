import os
import sys
import tempfile
import threading
from datetime import date
from dotenv import load_dotenv
import anthropic
import sounddevice as sd
import soundfile as sf
import numpy as np
from deepgram import DeepgramClient
from elevenlabs.client import ElevenLabs
import subprocess
from tools import TOOLS, TOOL_FUNCTIONS

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

TODAY = date.today().strftime("%d de %B de %Y")

SYSTEM_PROMPT = f"""O teu nome é Morgan. És o assistente pessoal de confiança do Vasco Botelho da Costa — treinador de futebol português.

A data de hoje é {TODAY}. Usa sempre esta data como referência. Quando pesquisares, inclui sempre o ano 2026 nas queries para obteres resultados atuais.

O teu papel é ser o braço direito do Vasco. Não és apenas um motor de busca — és um interlocutor de confiança com quem ele pode pensar em voz alta, tomar decisões, e aprender.

As tuas três áreas principais:
1. Apoio ao trabalho como treinador — táticas, gestão de plantel, preparação de jogos, decisões difíceis
2. Primeira Liga portuguesa — acompanhas a competição, equipas, adversários, e notícias
3. Inteligência artificial — filtras e explicas evoluções relevantes de forma clara e prática

Tom e personalidade:
- Firme e direto em questões de trabalho importantes
- Compreensivo e de apoio quando o Vasco precisa de ser ouvido
- Breve por defeito — não enches linguiça, expandas quando pedido
- Sempre em português europeu
- Trata o Vasco pelo primeiro nome

Estás a responder por voz — mantém as respostas concisas e naturais para serem ouvidas, não lidas."""

conversation_history = []
SAMPLE_RATE = 16000
is_playing = False


def run_tool(tool_name: str, tool_input: dict) -> str:
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return f"Ferramenta '{tool_name}' não encontrada."
    try:
        if tool_input:
            return func(**tool_input)
        else:
            return func()
    except Exception as e:
        return f"Erro ao executar '{tool_name}': {e}"


def transcribe(audio_data: np.ndarray) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        sf.write(f.name, audio_data, SAMPLE_RATE)
        tmp_path = f.name

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()

    os.unlink(tmp_path)

    options = {
        "model": "nova-3",
        "language": "pt",
        "smart_format": True,
    }
    response = deepgram_client.listen.rest.v("1").transcribe_file(
        {"buffer": audio_bytes, "mimetype": "audio/wav"},
        options
    )
    return response.results.channels[0].alternatives[0].transcript


def speak(text: str):
    global is_playing
    is_playing = True
    try:
        audio = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=text,
            model_id="eleven_multilingual_v2",
        )
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            for chunk in audio:
                f.write(chunk)
            tmp_path = f.name
        if os.path.getsize(tmp_path) > 0:
            subprocess.run(["afplay", tmp_path])
        os.unlink(tmp_path)
    finally:
        is_playing = False


def get_reply(user_input: str) -> str:
    conversation_history.append({"role": "user", "content": user_input})

    while True:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        )

        if response.stop_reason == "tool_use":
            conversation_history.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [a usar ferramenta: {block.name}...]")
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            conversation_history.append({"role": "user", "content": tool_results})
            continue

        reply = response.content[0].text
        conversation_history.append({"role": "assistant", "content": reply})
        return reply


def record_while_key_held() -> np.ndarray:
    print("\nSegura ESPAÇO para falar, larga para enviar. (Ctrl+C para sair)\n")
    import tty
    import termios

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    recording = []
    recording_active = threading.Event()

    def audio_callback(indata, frames, time, status):
        if recording_active.is_set():
            recording.append(indata.copy())

    try:
        tty.setraw(fd)
        stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32', callback=audio_callback)
        stream.start()

        while True:
            ch = sys.stdin.read(1)

            if ch == ' ' and not recording_active.is_set():
                recording.clear()
                recording_active.set()
                print("A gravar...", end='', flush=True)

            elif ch == ' ' and recording_active.is_set():
                recording_active.clear()
                stream.stop()
                stream.close()
                print(" gravado.")
                if recording:
                    return np.concatenate(recording, axis=0).flatten()
                return np.array([])

            elif ch == '\x03':  # Ctrl+C
                stream.stop()
                stream.close()
                raise KeyboardInterrupt

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def text_mode():
    print("=" * 50)
    print("Morgan Voz — modo texto")
    print("Escreve a mensagem e o Morgan responde em voz.")
    print("Escreve 'sair' para terminar.")
    print("=" * 50)

    while True:
        try:
            user_input = input("\nTu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo, Vasco.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("sair", "exit", "quit"):
            print("Morgan: Até logo, Vasco.")
            break

        try:
            print("Morgan a pensar...", end='', flush=True)
            reply = get_reply(user_input)
            print(f"\nMorgan: {reply}\n")
            speak_thread = threading.Thread(target=speak, args=(reply,))
            speak_thread.start()
            speak_thread.join()
        except Exception as e:
            print(f"\nErro: {e}\n")


def voice_mode():
    print("=" * 50)
    print("Morgan Voz — modo voz")
    print("Segura ESPAÇO para falar, larga para enviar.")
    print("Ctrl+C para terminar.")
    print("=" * 50)

    while True:
        try:
            audio = record_while_key_held()

            if len(audio) < SAMPLE_RATE * 0.5:
                print("(muito curto, tenta de novo)")
                continue

            print("A transcrever...", end='', flush=True)
            transcript = transcribe(audio)

            if not transcript.strip():
                print(" não percebi nada, tenta de novo.")
                continue

            print(f"\nTu: {transcript}")
            print("Morgan a pensar...", end='', flush=True)

            reply = get_reply(transcript)
            print(f"\nMorgan: {reply}\n")

            speak_thread = threading.Thread(target=speak, args=(reply,))
            speak_thread.start()
            speak_thread.join()

        except KeyboardInterrupt:
            print("\nAté logo, Vasco.")
            break
        except Exception as e:
            print(f"\nErro: {e}\n")


def main():
    print("Morgan Voz — como queres falar?")
    print("  1 - Escrever (Morgan responde em voz)")
    print("  2 - Falar (push-to-talk)")
    escolha = input("Escolha (1 ou 2): ").strip()

    if escolha == "2":
        voice_mode()
    else:
        text_mode()


if __name__ == "__main__":
    main()
