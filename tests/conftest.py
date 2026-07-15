"""
Configuração global de testes do Morgan.
Mocks determinísticos para Claude, Tavily, API Football e serviços externos.
"""
import os
import sys
import pytest

# Garantir que o Morgan dir está no path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))

# Variáveis de ambiente de teste (evitam chamadas reais)
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")
os.environ.setdefault("TAVILY_API_KEY", "test-key-not-real")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-key-not-real")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-key-not-real")
os.environ.setdefault("API_FOOTBALL_KEY", "test-key-not-real")


def make_claude_response(text: str, stop_reason: str = "end_turn"):
    """Cria um objecto de resposta Claude falso mas estruturalmente correcto."""
    content_block = type("ContentBlock", (), {"text": text, "type": "text"})()
    usage = type("Usage", (), {"input_tokens": 100, "output_tokens": 50})()
    return type("Response", (), {
        "content": [content_block],
        "stop_reason": stop_reason,
        "usage": usage,
    })()


@pytest.fixture
def mock_claude(monkeypatch):
    """Mock do anthropic.Anthropic — evita chamadas reais e custos."""
    responses = {"_idx": 0, "_texts": ["Resposta de teste do Morgan."]}

    def create(**kwargs):
        texts = responses["_texts"]
        idx = responses["_idx"] % len(texts)
        responses["_idx"] += 1
        return make_claude_response(texts[idx])

    mock_inst = type("MockAnthropic", (), {
        "messages": type("Messages", (), {"create": staticmethod(create)})()
    })()

    monkeypatch.setattr("anthropic.Anthropic", lambda **kwargs: mock_inst)
    return responses  # para os testes configurarem respostas específicas


@pytest.fixture
def mock_tavily(monkeypatch):
    """Mock do TavilyClient — devolve resultados vazios por defeito."""
    def search(query, **kwargs):
        return {"results": [
            {"title": "Resultado mock", "content": "Conteúdo de teste.", "url": "https://example.com"}
        ]}

    mock_client = type("MockTavily", (), {"search": search})()
    monkeypatch.setattr("tavily.TavilyClient", lambda **kwargs: mock_client)
    return mock_client


@pytest.fixture
def mock_api_football(monkeypatch):
    """Mock do requests.get para API Football."""
    import requests

    def mock_get(url, **kwargs):
        class R:
            status_code = 200
            def json(self): return {"response": []}
        return R()

    monkeypatch.setattr(requests, "get", mock_get)
