"""
automation_service.py — browser automation e acesso a email Zoho.

Usa Playwright para criar contas em plataformas web.
Usa IMAP para verificar emails de confirmação Zoho.
2FA é sempre manual — nunca automatizado.

Variáveis de ambiente necessárias:
  ZOHO_EMAIL      — conta principal Zoho (ex: morganceoai@zohomail.eu)
  ZOHO_PASSWORD   — password da conta Zoho
"""
import os
import imaplib
import email as email_lib
import re
import time
from datetime import datetime, timedelta
from typing import Optional


# ── Zoho IMAP ─────────────────────────────────────────────────────────────────

ZOHO_EMAIL    = os.getenv("ZOHO_EMAIL", "")
ZOHO_PASSWORD = os.getenv("ZOHO_PASSWORD", "")
ZOHO_IMAP     = "imap.zoho.eu"  # ou imap.zoho.com dependendo da conta


def _imap_connect() -> imaplib.IMAP4_SSL:
    conn = imaplib.IMAP4_SSL(ZOHO_IMAP, 993)
    conn.login(ZOHO_EMAIL, ZOHO_PASSWORD)
    return conn


def verificar_email_confirmacao(remetente_keywords: list[str], assunto_keywords: list[str] = None, minutos: int = 10) -> Optional[str]:
    """
    Procura o email de confirmação mais recente que chegou nos últimos `minutos`.
    Retorna o URL de confirmação encontrado ou None.

    remetente_keywords: lista de strings para filtrar remetente (ex: ["etsy", "noreply"])
    assunto_keywords:   lista de strings para filtrar assunto (ex: ["confirm", "verify", "activate"])
    """
    if not ZOHO_EMAIL or not ZOHO_PASSWORD:
        return None

    try:
        conn = _imap_connect()
        conn.select("INBOX")

        # Pesquisar emails dos últimos N minutos
        since = (datetime.now() - timedelta(minutes=minutos)).strftime("%d-%b-%Y")
        _, data = conn.search(None, f'(SINCE "{since}" UNSEEN)')
        ids = data[0].split() if data[0] else []

        for mid in reversed(ids[-20:]):  # últimos 20, mais recentes primeiro
            _, msg_data = conn.fetch(mid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            from_addr = str(msg.get("From", "")).lower()
            subject   = str(msg.get("Subject", "")).lower()

            # Filtrar por remetente
            if remetente_keywords and not any(k.lower() in from_addr for k in remetente_keywords):
                continue
            # Filtrar por assunto
            if assunto_keywords and not any(k.lower() in subject for k in assunto_keywords):
                continue

            # Extrair URL de confirmação do corpo
            body = _get_email_body(msg)
            urls = re.findall(r'https?://[^\s"<>]+confirm[^\s"<>]*|https?://[^\s"<>]+verif[^\s"<>]*|https?://[^\s"<>]+activ[^\s"<>]*', body, re.IGNORECASE)
            if urls:
                conn.store(mid, "+FLAGS", "\\Seen")
                conn.logout()
                return urls[0]

        conn.logout()
        return None

    except Exception as e:
        print(f"[zoho-imap] erro: {e}", flush=True)
        return None


def _get_email_body(msg) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct in ("text/plain", "text/html"):
                try:
                    body += part.get_payload(decode=True).decode("utf-8", errors="ignore")
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
        except Exception:
            pass
    return body


def listar_emails_recentes(n: int = 10) -> str:
    """Lista os N emails mais recentes — usado pelo CEO para dar contexto ao Vasco."""
    if not ZOHO_EMAIL or not ZOHO_PASSWORD:
        return "Zoho IMAP não configurado (ZOHO_EMAIL / ZOHO_PASSWORD em falta)."
    try:
        conn = _imap_connect()
        conn.select("INBOX")
        _, data = conn.search(None, "ALL")
        ids = data[0].split()[-n:]
        resultado = []
        for mid in reversed(ids):
            _, msg_data = conn.fetch(mid, "(RFC822.HEADER)")
            msg = email_lib.message_from_bytes(msg_data[0][1])
            resultado.append(f"De: {msg.get('From','')} | Assunto: {msg.get('Subject','')} | Data: {msg.get('Date','')}")
        conn.logout()
        return "\n".join(resultado) if resultado else "Sem emails."
    except Exception as e:
        return f"Erro IMAP: {e}"


# ── Playwright browser automation ─────────────────────────────────────────────

def _playwright_disponivel() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def criar_conta_plataforma(plataforma: str, url_registo: str, email: str, password: str, dados_extra: dict = None) -> str:
    """
    Abre a página de registo e preenche o formulário.
    Requer playwright instalado: pip install playwright && playwright install chromium

    dados_extra: dict com campos adicionais (ex: {"nome": "Morgan CEO", "empresa": "BC Industries"})
    Não automatiza 2FA — avisa o Vasco se for necessário.
    """
    if not _playwright_disponivel():
        return (
            "Playwright não instalado. Para activar browser automation:\n"
            "pip install playwright && playwright install chromium"
        )

    dados_extra = dados_extra or {}

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(url_registo, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            # Preencher email
            for sel in ['input[type="email"]', 'input[name*="email"]', 'input[id*="email"]', 'input[placeholder*="email" i]']:
                try:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.fill(email)
                        break
                except Exception:
                    pass

            # Preencher password
            for sel in ['input[type="password"]', 'input[name*="password"]', 'input[name*="pass"]']:
                try:
                    els = page.locator(sel).all()
                    for el in els:
                        el.fill(password)
                except Exception:
                    pass

            # Preencher campos extra (nome, empresa, etc.)
            for campo, valor in dados_extra.items():
                for sel in [
                    f'input[name="{campo}"]',
                    f'input[id="{campo}"]',
                    f'input[placeholder*="{campo}" i]',
                ]:
                    try:
                        if page.locator(sel).count() > 0:
                            page.locator(sel).first.fill(str(valor))
                            break
                    except Exception:
                        pass

            # Submeter formulário
            for sel in ['button[type="submit"]', 'input[type="submit"]', 'button:has-text("Sign up")', 'button:has-text("Register")', 'button:has-text("Create")']:
                try:
                    if page.locator(sel).count() > 0:
                        page.locator(sel).first.click()
                        page.wait_for_load_state("networkidle", timeout=8000)
                        break
                except Exception:
                    pass

            title = page.title()
            browser.close()

        # Registar conta no sistema
        from sistema_service import registar_conta_zoho
        if "zoho" in email.lower() or "morganceoai" in email.lower():
            registar_conta_zoho(email)

        return (
            f"Formulário de registo submetido em {plataforma}.\n"
            f"Título da página: {title}\n"
            f"Verifica o email {email} para confirmação (usar verificar_email_confirmacao).\n"
            f"NOTA: Se houver 2FA, o Vasco tem de completar manualmente."
        )

    except Exception as e:
        return f"Erro na automation de {plataforma}: {e}"


def visitar_url_confirmacao(url: str) -> str:
    """Visita um URL de confirmação de conta."""
    if not _playwright_disponivel():
        return "Playwright não instalado."
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=15000)
            page.wait_for_load_state("networkidle", timeout=8000)
            title = page.title()
            browser.close()
        return f"URL visitado. Título: {title}"
    except Exception as e:
        return f"Erro: {e}"


def instalar_playwright() -> str:
    """Instala playwright se não estiver disponível."""
    import subprocess
    try:
        subprocess.run(["pip", "install", "playwright"], check=True, capture_output=True)
        subprocess.run(["playwright", "install", "chromium"], check=True, capture_output=True)
        return "Playwright instalado com sucesso."
    except Exception as e:
        return f"Erro na instalação: {e}"
