"""
Morgan — logging estruturado + Sentry.
Importar no início de qualquer módulo que precise de logging.

Uso:
    from morgan_logging import get_logger
    logger = get_logger(__name__)
    logger.info("evento", agente="CEO", latency_ms=120)
"""
import logging
import os
import sys


def configure(level: str = "INFO"):
    """Configura structlog + Sentry. Chamado uma vez no startup do servidor."""
    try:
        import structlog

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.dev.ConsoleRenderer() if sys.stderr.isatty()
                else structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(level)
            ),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )
    except ImportError:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    # Sentry (opcional — só activo se SENTRY_DSN estiver definido)
    dsn = os.getenv("SENTRY_DSN", "")
    if dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.logging import LoggingIntegration

            sentry_sdk.init(
                dsn=dsn,
                integrations=[
                    FastApiIntegration(),
                    LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
                ],
                traces_sample_rate=0.05,
            )
        except ImportError:
            pass


def get_logger(name: str):
    """Retorna logger structlog (ou stdlib como fallback)."""
    try:
        import structlog
        return structlog.get_logger(name)
    except ImportError:
        return logging.getLogger(name)


def bind_agent(agent: str):
    """Bind do nome do agente ao contexto de logging para todas as chamadas seguintes."""
    try:
        import structlog
        structlog.contextvars.bind_contextvars(agent=agent)
    except ImportError:
        pass


def log_llm_call(agent: str, input_tokens: int, output_tokens: int, latency_ms: int):
    """Regista uma chamada ao Claude com métricas de custo e latência."""
    logger = get_logger("llm")
    custo = round(input_tokens * 0.000003 + output_tokens * 0.000015, 6)
    logger.info(
        "llm_call",
        agent=agent,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        custo_usd=custo,
    )
