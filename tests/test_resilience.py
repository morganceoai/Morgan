"""
T7-T10 — Testes de caos: comportamento quando APIs externas falham.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestChaos:
    def test_morgan_sobrevive_anthropic_offline(self, monkeypatch):
        """CEO deve retornar mensagem de erro amigável se Claude falhar."""
        def crash(**kwargs):
            raise ConnectionError("Anthropic offline — simulado")

        mock_inst = type("M", (), {
            "messages": type("Ms", (), {"create": staticmethod(crash)})()
        })()
        monkeypatch.setattr("anthropic.Anthropic", lambda **kwargs: mock_inst)

        from desktop_server import chat_with_morgan
        try:
            reply = chat_with_morgan("teste")
            assert isinstance(reply, str)
        except Exception as e:
            # Se lançar excepção, deve ser capturada pelo servidor, não aqui
            pytest.fail(f"chat_with_morgan não capturou o erro do Claude: {e}")

    def test_tavily_offline_nao_quebra_pesquisa(self, monkeypatch):
        """pesquisar_web deve retornar mensagem de erro, não lançar excepção."""
        def crash(query, **kwargs):
            raise ConnectionError("Tavily offline — simulado")

        mock_client = type("M", (), {"search": staticmethod(crash)})()
        monkeypatch.setattr("tavily.TavilyClient", lambda **kwargs: mock_client)

        from tools import pesquisar_web
        result = pesquisar_web("qualquer coisa")
        assert isinstance(result, str)
        assert len(result) > 0  # deve retornar mensagem, não string vazia

    def test_api_football_offline_nao_quebra_coach(self, monkeypatch):
        """Coach deve responder mesmo sem API Football."""
        import requests

        def crash(*args, **kwargs):
            raise ConnectionError("API Football offline — simulado")

        monkeypatch.setattr(requests, "get", crash)

        from coach_agent import _fetch_moreirense_fixtures
        result = _fetch_moreirense_fixtures()
        assert isinstance(result, str)  # vazia ou com dados Tavily — nunca excepção

    def test_google_trends_sem_pytrends(self, mock_tavily):
        """google_trends deve funcionar sem pytrends (que está arquivado)."""
        from tools import google_trends
        result = google_trends(["ai tools", "saas"])
        assert isinstance(result, str)
        assert len(result) > 5

    def test_solver_diagnosticar_estado_inicial(self, mock_claude):
        """solver_diagnosticar deve retornar dict com campo relatorio."""
        mock_claude["_texts"] = [
            "DIAGNÓSTICO: ok\nCONFIANÇA_DIAGNÓSTICO: 80%\nREVERSÍVEL: sim\nIMPACTO: isolado",
            "PLANO: ok\nCONFIANÇA_SOLUÇÃO: 95%\nREQUER_APROVAÇÃO: não\nMOTIVO_APROVAÇÃO: simples",
            "EXECUÇÃO: ok\nCONFIANÇA_EXECUÇÃO: 90%",
            "RESULTADO: RESOLVIDO\nCONFIANÇA_VERIFICAÇÃO: 90%\nDETALHES: ok",
            "Relatório concluído.",
        ]
        from solver_graph import solver_diagnosticar
        estado = solver_diagnosticar("problema de teste")
        assert isinstance(estado, dict)
        assert "relatorio" in estado
        assert isinstance(estado["relatorio"], str)


class TestHealth:
    def test_health_endpoint_importavel(self):
        """O endpoint /health deve ser importável sem erros."""
        import importlib
        spec = importlib.util.spec_from_file_location(
            "desktop_server",
            __import__("pathlib").Path(__file__).parent.parent / "desktop_server.py"
        )
        # Apenas validar que o módulo tem a função health
        # (import completo requer todas as dependências)
        import ast
        src = (__import__("pathlib").Path(__file__).parent.parent / "desktop_server.py").read_text()
        tree = ast.parse(src)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)]
        assert "health" in funcs, "Endpoint /health não encontrado em desktop_server.py"

    def test_run_solver_alias_correcto(self):
        """run_solver deve delegar para solver_diagnosticar e retornar string."""
        import inspect
        import solver_graph
        assert hasattr(solver_graph, "run_solver"), "run_solver não existe em solver_graph.py"
        assert hasattr(solver_graph, "solver_diagnosticar"), "solver_diagnosticar não existe"
        src = inspect.getsource(solver_graph.run_solver)
        assert "solver_diagnosticar" in src, "run_solver não chama solver_diagnosticar"
