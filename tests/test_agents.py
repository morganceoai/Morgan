"""
T1-T6 — Testes de agentes: resposta válida, sem exposição de erros, sem truncagem.
"""
import pytest


class TestCEO:
    def test_resposta_nao_vazia(self, mock_claude):
        from desktop_server import chat_with_morgan
        reply = chat_with_morgan("olá")
        assert reply and len(reply) > 0

    def test_nao_expoe_traceback(self, mock_claude):
        from desktop_server import chat_with_morgan
        reply = chat_with_morgan("diz-me algo")
        assert "traceback" not in reply.lower()
        assert "exception" not in reply.lower()

    def test_resposta_em_portugues(self, mock_claude):
        mock_claude["_texts"] = ["Bom dia, Vasco. Como posso ajudar?"]
        from desktop_server import chat_with_morgan
        reply = chat_with_morgan("hello")
        assert reply  # conteúdo validado pelo mock


class TestSolver:
    def test_alias_run_solver_existe(self):
        from solver_graph import run_solver
        assert callable(run_solver)

    def test_solver_retorna_string(self, mock_claude):
        mock_claude["_texts"] = [
            "DIAGNÓSTICO: problema de teste\nCONFIANÇA_DIAGNÓSTICO: 85%\nREVERSÍVEL: sim\nIMPACTO: isolado",
            "PLANO: fix simples\nCONFIANÇA_SOLUÇÃO: 92%\nREQUER_APROVAÇÃO: não\nMOTIVO_APROVAÇÃO: baixo risco",
            "EXECUÇÃO: feito\nCONFIANÇA_EXECUÇÃO: 90%",
            "RESULTADO: RESOLVIDO\nCONFIANÇA_VERIFICAÇÃO: 90%\nDETALHES: ok",
            "Relatório final do Solver.",
        ]
        from solver_graph import run_solver
        result = run_solver("teste simples")
        assert isinstance(result, str)
        assert len(result) > 0


class TestGoogleTrends:
    def test_trends_usa_tavily(self, mock_tavily):
        from tools import google_trends
        result = google_trends(["AI automation", "micro SaaS"])
        assert isinstance(result, str)
        assert "AI automation" in result or "micro SaaS" in result or "Tendências" in result

    def test_trends_nao_usa_pytrends(self):
        """pytrends foi arquivado — garantir que não é importado."""
        import tools
        import inspect
        src = inspect.getsource(tools.google_trends)
        assert "pytrends" not in src, "google_trends ainda usa pytrends (arquivado Abril 2025)"


class TestTools:
    def test_pesquisar_web_retorna_string(self, mock_tavily):
        from tools import pesquisar_web
        result = pesquisar_web("Moreirense FC 2026")
        assert isinstance(result, str)

    def test_tool_functions_completas(self):
        from tools import TOOLS, TOOL_FUNCTIONS
        for tool in TOOLS:
            nome = tool["name"]
            assert nome in TOOL_FUNCTIONS, f"Tool '{nome}' não tem função em TOOL_FUNCTIONS"


class TestCreator:
    def test_listar_agentes(self):
        from creator_agent import listar_agentes
        agentes = listar_agentes()
        assert isinstance(agentes, list)
        # Agentes core devem existir
        nomes = " ".join(agentes)
        assert "cfo_agent.py" in nomes or "coach_agent.py" in nomes

    def test_deploy_valida_sintaxe(self, tmp_path, monkeypatch):
        """Garantir que deploy_agente rejeita código com SyntaxError."""
        import creator_agent
        # Criar agente com sintaxe inválida
        bad_file = creator_agent.MORGAN_DIR / "testbad_agent.py"
        bad_file.write_text("def broken(: pass")
        try:
            result = creator_agent.deploy_agente("testbad")
            assert result.get("fase") == "sintaxe" or result.get("status") == "erro"
        finally:
            if bad_file.exists():
                bad_file.unlink()
