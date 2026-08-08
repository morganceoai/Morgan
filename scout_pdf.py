"""
Geração de PDFs para relatórios Scout.
Chamado pelo scout_agent após cada missão e pelo endpoint /api/scout/pdf.
"""
import re
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

MEMORY_DIR = Path(__file__).parent / "memory"
SCOUT_REPORTS_DIR = MEMORY_DIR / "scout_reports"
SCOUT_PDF_DIR = MEMORY_DIR / "scout_pdfs"
SCOUT_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Paleta BCVertex
C_BG      = colors.HexColor("#0a0a0a")
C_CYAN    = colors.HexColor("#00d4ff")
C_GREEN   = colors.HexColor("#00ff88")
C_YELLOW  = colors.HexColor("#ffcc00")
C_RED     = colors.HexColor("#ff3333")
C_GRAY    = colors.HexColor("#888888")
C_WHITE   = colors.HexColor("#e8e8e8")
C_DARK    = colors.HexColor("#1a1a2e")
C_PANEL   = colors.HexColor("#111122")


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "SCTitle",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=C_CYAN,
            spaceAfter=4,
            alignment=TA_LEFT,
            leading=26,
        ),
        "subtitle": ParagraphStyle(
            "SCSubtitle",
            fontName="Helvetica",
            fontSize=10,
            textColor=C_GRAY,
            spaceAfter=16,
            alignment=TA_LEFT,
        ),
        "section": ParagraphStyle(
            "SCSection",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=C_GREEN,
            spaceBefore=14,
            spaceAfter=4,
            leading=16,
        ),
        "body": ParagraphStyle(
            "SCBody",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_WHITE,
            spaceAfter=6,
            leading=14,
            leftIndent=0,
        ),
        "bullet": ParagraphStyle(
            "SCBullet",
            fontName="Helvetica",
            fontSize=9,
            textColor=C_WHITE,
            spaceAfter=3,
            leading=13,
            leftIndent=12,
            bulletIndent=0,
        ),
        "label": ParagraphStyle(
            "SCLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=C_YELLOW,
            spaceAfter=2,
            leading=11,
            letterSpacing=1,
        ),
        "meta": ParagraphStyle(
            "SCMeta",
            fontName="Helvetica-Oblique",
            fontSize=8,
            textColor=C_GRAY,
            spaceAfter=2,
            leading=11,
        ),
    }


def _clean(text: str) -> str:
    """Remove markdown pesado e converte para texto limpo."""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"^[-•]\s+", "• ", text, flags=re.MULTILINE)
    text = text.replace("&", "&amp;").replace("<b>&amp;", "<b>&").replace("&amp;</b>", "&</b>")
    # Só escapar & soltos (fora de tags)
    return text


def _parse_sections(raw: str) -> list[tuple[str, str]]:
    """Divide o texto em secções por headings markdown."""
    sections = []
    parts = re.split(r"\n(?=#{1,3} )", raw.strip())
    for part in parts:
        lines = part.strip().split("\n")
        heading_line = lines[0]
        heading = re.sub(r"^#{1,3}\s*", "", heading_line).strip()
        body = "\n".join(lines[1:]).strip()
        sections.append((heading, body))
    return sections


def _categoria_from_filename(filename: str) -> str:
    fname = filename.replace(".txt", "").replace(".md", "")
    if "missao_a" in fname:
        return "Oportunidades de Negócio"
    if "missao_b_solver" in fname:
        return "Melhorias ao Sistema"
    if "missao_b" in fname:
        return "Melhorias ao Ecossistema"
    if "missao_c" in fname:
        return "Saúde dos Negócios"
    if "missao_d" in fname:
        return "Trading & Estratégia"
    if "analise" in fname or "investigacao" in fname:
        return "Análise Autónoma"
    return "Scout"


def _titulo_from_filename(filename: str) -> str:
    fname = filename.replace(".txt", "").replace(".md", "")
    # Extrair partes úteis
    fname = re.sub(r"^missao_[abcd]_?", "", fname)
    fname = re.sub(r"_\d{4}-\d{2}-\d{2}$", "", fname)
    fname = re.sub(r"_\d{2}ago\d{4}$", "", fname)
    fname = fname.replace("_", " ").strip().title()
    return fname or "Relatório Scout"


def gerar_pdf(txt_path: Path, pdf_path: Path | None = None) -> Path:
    """
    Converte um relatório .txt/.md do Scout num PDF formatado BCVertex.
    Devolve o caminho do PDF gerado.
    """
    raw = txt_path.read_text(encoding="utf-8")
    stem = txt_path.stem

    if pdf_path is None:
        pdf_path = SCOUT_PDF_DIR / f"{stem}.pdf"

    styles = _build_styles()
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.2*cm,
        bottomMargin=2*cm,
        title=_titulo_from_filename(txt_path.name),
        author="Morgan — BCVertex",
    )

    story = []
    categoria = _categoria_from_filename(txt_path.name)
    titulo = _titulo_from_filename(txt_path.name)
    data_str = datetime.now().strftime("%d/%m/%Y")

    # Header
    story.append(Paragraph(f"BCVERTEX · SCOUT", styles["label"]))
    story.append(Spacer(1, 0.1*cm))
    story.append(Paragraph(titulo, styles["title"]))
    story.append(Paragraph(f"{categoria}  ·  {data_str}", styles["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=1, color=C_CYAN, spaceAfter=14))

    # Conteúdo
    sections = _parse_sections(raw)

    if len(sections) <= 1:
        # Sem headings — tratar como corpo corrido
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 0.3*cm))
            elif line.startswith("•") or line.startswith("-"):
                story.append(Paragraph(_clean(line), styles["bullet"]))
            else:
                story.append(Paragraph(_clean(line), styles["body"]))
    else:
        for heading, body in sections:
            if heading:
                story.append(Paragraph(_clean(heading), styles["section"]))
                story.append(HRFlowable(width="40%", thickness=0.5, color=C_CYAN, spaceAfter=6))
            for line in body.split("\n"):
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 0.2*cm))
                elif line.startswith("•") or line.startswith("- ") or line.startswith("* "):
                    story.append(Paragraph("• " + _clean(line.lstrip("-•* ")), styles["bullet"]))
                else:
                    story.append(Paragraph(_clean(line), styles["body"]))

    # Footer
    story.append(Spacer(1, 0.8*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=C_GRAY, spaceAfter=6))
    story.append(Paragraph(
        f"Gerado por Morgan CEO · BCVertex · {data_str}",
        styles["meta"]
    ))

    # Background escuro via canvas callback
    def _bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    return pdf_path


def gerar_todos_pdfs() -> list[Path]:
    """Converte todos os .txt/.md de scout_reports que ainda não têm PDF."""
    gerados = []
    for f in sorted(SCOUT_REPORTS_DIR.iterdir()):
        if f.suffix not in (".txt", ".md"):
            continue
        pdf = SCOUT_PDF_DIR / f"{f.stem}.pdf"
        if not pdf.exists():
            try:
                gerar_pdf(f, pdf)
                gerados.append(pdf)
            except Exception as e:
                print(f"[scout_pdf] erro ao gerar {f.name}: {e}")
    return gerados


def listar_relatorios() -> list[dict]:
    """
    Devolve lista de relatórios para o endpoint da API.
    Cada item: {titulo, categoria, data, pdf_url, tamanho_kb}
    """
    out = []
    for f in sorted(SCOUT_REPORTS_DIR.iterdir(), reverse=True):
        if f.suffix not in (".txt", ".md"):
            continue
        pdf = SCOUT_PDF_DIR / f"{f.stem}.pdf"
        if not pdf.exists():
            try:
                gerar_pdf(f, pdf)
            except Exception:
                continue

        stat = f.stat()
        out.append({
            "id": f.stem,
            "titulo": _titulo_from_filename(f.name),
            "categoria": _categoria_from_filename(f.name),
            "data": datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y"),
            "pdf_url": f"/api/scout/pdf/{f.stem}",
            "tamanho_kb": round(pdf.stat().st_size / 1024, 1),
        })
    return out
