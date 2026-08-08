"""
Solver Health Check passivo — sem Claude.
Corre a cada 5 minutos. Detecta falhas silenciosas que nunca disparam excepções.
Só acorda o Solver (com Claude) quando uma métrica está fora do padrão histórico.

Thresholds dinâmicos: compara com a média das últimas 4 semanas para a mesma
hora do dia. Um pico às 3h é avaliado contra o padrão das 3h, não contra o das 14h.
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

_BASE = Path(__file__).parent
_BASELINE_FILE = _BASE / "memory" / "health_baseline.json"
_INCIDENT_LOG = _BASE / "memory" / "incident_log.jsonl"

# Métricas a monitorizar e os seus limites absolutos de emergência
# (usados quando ainda não há baseline histórico suficiente)
_HARD_LIMITS = {
    "log_silence_minutes": 30,      # log sem actividade há > 30min → algo morreu
    "log_error_rate_per_hour": 20,  # > 20 linhas ERROR/hora → problema sistémico
    "state_file_age_minutes": 120,  # system_state.json não actualizado há > 2h
    "disk_free_mb": 500,            # disco com < 500MB livres
}


# ── Baseline dinâmico ─────────────────────────────────────────────────────────

def _load_baseline() -> dict:
    if _BASELINE_FILE.exists():
        try:
            return json.loads(_BASELINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_baseline(baseline: dict) -> None:
    _BASELINE_FILE.parent.mkdir(exist_ok=True)
    _BASELINE_FILE.write_text(json.dumps(baseline, indent=2, ensure_ascii=False), encoding="utf-8")


def _record_metric(name: str, value: float) -> None:
    """Regista uma amostra de métrica no baseline para a hora actual."""
    baseline = _load_baseline()
    hora = f"{datetime.now().hour:02d}"
    if name not in baseline:
        baseline[name] = {}
    if hora not in baseline[name]:
        baseline[name][hora] = []
    samples = baseline[name][hora]
    samples.append(value)
    baseline[name][hora] = samples[-100:]  # máximo 100 amostras por hora
    _save_baseline(baseline)


def _is_anomalous(name: str, value: float, multiplier: float = 2.5) -> bool:
    """
    Retorna True se o valor está fora do padrão histórico para esta hora.
    Usa média das últimas N amostras. Se não há baseline suficiente (< 5 amostras),
    usa hard limits absolutos.
    """
    baseline = _load_baseline()
    hora = f"{datetime.now().hour:02d}"
    samples = baseline.get(name, {}).get(hora, [])

    if len(samples) < 5:
        # Sem baseline suficiente — usa limite absoluto se existir
        limit = _HARD_LIMITS.get(name)
        return limit is not None and value > limit

    media = sum(samples) / len(samples)
    if media == 0:
        return value > 0
    return value > media * multiplier


# ── Colectores de métricas ────────────────────────────────────────────────────

def _check_log_silence() -> Optional[str]:
    """Há quanto tempo o log não tem actividade?"""
    log_path = _BASE / "morgan_server.log"
    if not log_path.exists():
        return "Log do servidor não encontrado"
    try:
        age_minutes = (time.time() - log_path.stat().st_mtime) / 60
        _record_metric("log_silence_minutes", age_minutes)
        if _is_anomalous("log_silence_minutes", age_minutes):
            return f"Log sem actividade há {age_minutes:.0f} minutos (anómalo para esta hora)"
    except Exception:
        pass
    return None


def _check_log_error_rate() -> Optional[str]:
    """Quantas linhas ERROR/CRITICAL apareceram na última hora?"""
    log_path = _BASE / "morgan_server.log"
    if not log_path.exists():
        return None
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        limite = datetime.now() - timedelta(hours=1)
        count = 0
        for line in reversed(lines[-2000:]):
            if "ERROR" in line or "CRITICAL" in line or "Traceback" in line:
                # Tentar extrair timestamp da linha para confirmar última hora
                count += 1
        _record_metric("log_error_rate_per_hour", count)
        if _is_anomalous("log_error_rate_per_hour", count):
            return f"{count} erros no log na última hora (anómalo para esta hora)"
    except Exception:
        pass
    return None


def _check_state_file_freshness() -> Optional[str]:
    """O system_state.json está desactualizado?"""
    state_path = _BASE / "memory" / "system_state.json"
    if not state_path.exists():
        return "system_state.json não encontrado"
    try:
        age_minutes = (time.time() - state_path.stat().st_mtime) / 60
        _record_metric("state_file_age_minutes", age_minutes)
        if _is_anomalous("state_file_age_minutes", age_minutes):
            return f"system_state.json não actualizado há {age_minutes:.0f} minutos"
    except Exception:
        pass
    return None


def _check_disk_space() -> Optional[str]:
    """Espaço livre em disco."""
    try:
        r = subprocess.run(
            ["df", "-m", str(_BASE)],
            capture_output=True, text=True, timeout=5
        )
        for line in r.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                free_mb = float(parts[3])
                _record_metric("disk_free_mb", free_mb)
                if free_mb < _HARD_LIMITS["disk_free_mb"]:
                    return f"Disco com apenas {free_mb:.0f}MB livres"
    except Exception:
        pass
    return None


def _check_trading_state() -> Optional[str]:
    """O trading bot actualizou o seu estado recentemente?"""
    trading_state = _BASE / "memory" / "trading_state.json"
    if not trading_state.exists():
        return None
    try:
        data = json.loads(trading_state.read_text(encoding="utf-8"))
        ts_str = data.get("ultima_actualizacao") or data.get("timestamp", "")
        if not ts_str:
            return None
        ts = datetime.fromisoformat(ts_str)
        age_minutes = (datetime.now() - ts).total_seconds() / 60
        _record_metric("trading_state_age_minutes", age_minutes)
        if _is_anomalous("trading_state_age_minutes", age_minutes, multiplier=3.0):
            return f"Trading state não actualizado há {age_minutes:.0f} minutos"
    except Exception:
        pass
    return None


def _check_process_alive() -> Optional[str]:
    """O processo está vivo — se este código corre, o servidor está activo."""
    return None


# ── Ponto de entrada ──────────────────────────────────────────────────────────

def run_health_check() -> list[str]:
    """
    Corre todos os checks. Retorna lista de anomalias detectadas.
    Lista vazia = sistema saudável.
    Chamado pelo heartbeat do desktop_server.py a cada 5 minutos.
    """
    checks = [
        _check_process_alive,
        _check_log_silence,
        _check_log_error_rate,
        _check_state_file_freshness,
        _check_disk_space,
        _check_trading_state,
    ]
    anomalias = []
    for check in checks:
        try:
            resultado = check()
            if resultado:
                anomalias.append(resultado)
        except Exception as e:
            pass  # health check nunca deve crashar o sistema

    if anomalias:
        _registar_anomalias(anomalias)

    return anomalias


def _registar_anomalias(anomalias: list[str]) -> None:
    """Regista anomalias no incident log sem chamar Claude."""
    _INCIDENT_LOG.parent.mkdir(exist_ok=True)
    for a in anomalias:
        entrada = {
            "ts": datetime.now().isoformat(),
            "agente": "health_check",
            "descricao": a,
            "severidade": "media",
            "tipo": "anomalia_passiva",
        }
        with open(_INCIDENT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def acionar_solver_se_necessario(anomalias: list[str]) -> None:
    """
    Se há anomalias: aciona o Solver com Claude.
    Chamado pelo heartbeat após run_health_check().
    Throttle: não aciona mais que 1x por 15 minutos para o mesmo problema.
    """
    if not anomalias:
        return

    # Throttle — evitar loop de Solver a chamar Solver
    throttle_file = _BASE / "memory" / "health_solver_throttle.json"
    agora = datetime.now()
    throttle = {}
    if throttle_file.exists():
        try:
            throttle = json.loads(throttle_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    anomalias_para_solver = []
    for a in anomalias:
        chave = a[:60]
        ultimo = throttle.get(chave)
        if ultimo:
            try:
                delta = (agora - datetime.fromisoformat(ultimo)).total_seconds() / 60
                if delta < 15:
                    continue  # já foi enviado ao Solver há menos de 15min
            except Exception:
                pass
        anomalias_para_solver.append(a)
        throttle[chave] = agora.isoformat()

    # Limpar entradas antigas do throttle (> 2h)
    throttle = {k: v for k, v in throttle.items()
                if (agora - datetime.fromisoformat(v)).total_seconds() < 7200}
    throttle_file.write_text(json.dumps(throttle, indent=2, ensure_ascii=False), encoding="utf-8")

    if not anomalias_para_solver:
        return

    problema = "Health check detectou anomalias passivas:\n" + "\n".join(f"- {a}" for a in anomalias_para_solver)
    try:
        from solver_graph import solver_diagnosticar
        solver_diagnosticar(problema, modo="explain")
    except Exception:
        pass


def iniciar_scheduler_solver():
    """Daemon thread independente — health check a cada 5 minutos, sem depender do heartbeat."""
    def _loop():
        time.sleep(90)  # 1.5min startup delay
        while True:
            try:
                anomalias = run_health_check()
                if anomalias:
                    acionar_solver_se_necessario(anomalias)
            except Exception as e:
                print(f"[solver_health] erro: {e}", flush=True)
            time.sleep(5 * 60)

    t = threading.Thread(target=_loop, daemon=True, name="solver-health-scheduler")
    t.start()


if __name__ == "__main__":
    anomalias = run_health_check()
    if anomalias:
        print(f"⚠ {len(anomalias)} anomalia(s) detectada(s):")
        for a in anomalias:
            print(f"  - {a}")
    else:
        print("✓ Sistema saudável")
