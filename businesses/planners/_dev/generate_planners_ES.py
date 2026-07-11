from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Helvetica Neue — macOS built-in, embedding permitido para uso pessoal/comercial
HN = '/System/Library/Fonts/HelveticaNeue.ttc'
pdfmetrics.registerFont(TTFont("HN",     HN, subfontIndex=0))
pdfmetrics.registerFont(TTFont("HN-B",   HN, subfontIndex=1))
pdfmetrics.registerFont(TTFont("HN-M",   HN, subfontIndex=10))
pdfmetrics.registerFont(TTFont("HN-L",   HN, subfontIndex=7))

W, H = A4
mm = 2.8346456692913385
MB = 13*mm  # margin bottom

THEMES = {
    "indigo": {
        "P":  colors.HexColor("#3d52d5"),  # primary
        "Pd": colors.HexColor("#2b3aaa"),  # primary dark
        "Pl": colors.HexColor("#eef0fc"),  # primary light
        "A":  colors.HexColor("#7c3aed"),  # accent
        "R":  colors.HexColor("#d4d9f5"),  # rule lines
        "BG": colors.HexColor("#f6f8ff"),  # page bg
        "TX": colors.HexColor("#1a1d3b"),  # text
        "MU": colors.HexColor("#8891c4"),  # muted
        "WE": colors.HexColor("#ede9fb"),  # weekend bg
        "WA": colors.HexColor("#7c3aed"),  # weekend accent
    },
    "sage": {
        "P":  colors.HexColor("#2e7d5a"),
        "Pd": colors.HexColor("#1f5e42"),
        "Pl": colors.HexColor("#e8f5ee"),
        "A":  colors.HexColor("#c97b4b"),
        "R":  colors.HexColor("#bee0d0"),
        "BG": colors.HexColor("#f4fbf7"),
        "TX": colors.HexColor("#162a1e"),
        "MU": colors.HexColor("#6aa48a"),
        "WE": colors.HexColor("#fdf0e8"),
        "WA": colors.HexColor("#c97b4b"),
    },
    "terracotta": {
        "P":  colors.HexColor("#b84e28"),
        "Pd": colors.HexColor("#923c1a"),
        "Pl": colors.HexColor("#fceee6"),
        "A":  colors.HexColor("#e8a22e"),
        "R":  colors.HexColor("#f0c8b4"),
        "BG": colors.HexColor("#fdf7f3"),
        "TX": colors.HexColor("#2c1606"),
        "MU": colors.HexColor("#c28570"),
        "WE": colors.HexColor("#fffbee"),
        "WA": colors.HexColor("#e8a22e"),
    },
}

DAYS = [("Lu","Lunes"),("Ma","Martes"),("Mi","Miercoles"),
        ("Ju","Jueves"),("Vi","Viernes"),("Sa","Sabado"),("Do","Domingo")]
MONTHS = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
          "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

def bg(cv, t):
    cv.setFillColor(t["BG"]); cv.rect(0,0,W,H,fill=1,stroke=0)

def hdr(cv, t, title, sub=""):
    hh = 27*mm
    # Base
    cv.setFillColor(t["P"]); cv.rect(0, H-hh, W, hh, fill=1, stroke=0)
    # Accent stripe
    cv.setFillColor(t["A"]); cv.rect(0, H-hh, 5*mm, hh, fill=1, stroke=0)
    # Decorative circle right
    cv.setFillColor(t["Pd"]); cv.circle(W-18*mm, H-hh/2, 15*mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]);  cv.circle(W-18*mm, H-hh/2,  7*mm, fill=1, stroke=0)
    cv.setFillColor(colors.white)
    # Title
    cv.setFont("HN-B", 21); cv.drawString(14*mm, H-11*mm, title)
    if sub:
        cv.setFont("HN-L", 9); cv.setFillColor(colors.HexColor("#ffffffaa"))
        cv.drawString(14*mm, H-20*mm, sub)

def ftr(cv, t, label):
    fh = MB-2*mm
    cv.setFillColor(t["P"]); cv.rect(0,0,W,fh,fill=1,stroke=0)
    cv.setFillColor(t["A"]); cv.rect(0,0,5*mm,fh,fill=1,stroke=0)
    cv.setFillColor(colors.HexColor("#ffffffaa")); cv.setFont("HN",7.5)
    cv.drawString(14*mm, 4*mm, f"PlannerAtlas  ·  {label}  ·  planneratlas.etsy.com")
    cv.setFillColor(colors.white); cv.setFont("HN-B",7.5)
    cv.drawRightString(W-12*mm, 4*mm, "planneratlas.etsy.com")

# ─── COVER ───────────────────────────────────────────────────
def cover(cv, t, tname):
    bg(cv, t)
    split = H * 0.40
    cv.setFillColor(t["P"]); cv.rect(0, split, W, H-split, fill=1, stroke=0)
    cv.setFillColor(t["Pd"]); cv.circle(W*0.9, split + (H-split)*0.7, 58*mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]);  cv.circle(W*0.9, split + (H-split)*0.7, 30*mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]);  cv.circle(-8*mm, H-10*mm, 32*mm, fill=1, stroke=0)
    cv.setFillColor(t["A"]);  cv.rect(0, split, 5*mm, H-split, fill=1, stroke=0)

    cv.setFillColor(colors.white)
    cv.setFont("HN-B", 40); cv.drawString(18*mm, split+88*mm, "Planificador")
    cv.setFont("HN-L", 17); cv.setFillColor(colors.HexColor("#ffffffcc"))
    cv.drawString(18*mm, split+75*mm, "Sin fecha  ·  Para cada ano")
    cv.setStrokeColor(t["A"]); cv.setLineWidth(2.5)
    cv.line(18*mm, split+70*mm, 82*mm, split+70*mm)

    # Contents list
    cv.setFillColor(t["TX"]); cv.setFont("HN-B", 11.5)
    cv.drawString(18*mm, split-16*mm, "Contenido:")
    items = ["  ●  Vista anual",
             "  ●  Vista mensual (sin fecha)",
             "  ●  Planificador semanal (sin fecha)",
             "  ●  Habit Tracker",
             "  ●  Paginas de notas"]
    cv.setFont("HN", 11); cv.setFillColor(t["MU"])
    for i,item in enumerate(items):
        cv.drawString(20*mm, split-28*mm - i*8.5*mm, item)

    # Tip box
    cv.setFillColor(t["Pl"])
    cv.roundRect(18*mm, MB+14*mm, W-36*mm, 18*mm, 5, fill=1, stroke=0)
    cv.setFillColor(t["P"]); cv.setFont("HN-M", 9)
    cv.drawString(23*mm, MB+21*mm,
        "Consejo: Imprime la pagina del planificador todas las veces que necesites - para cada semana.")

    cv.setFillColor(t["MU"]); cv.setFont("HN",8)
    cv.drawCentredString(W/2, MB+5*mm,
        f"PlannerAtlas  ·  {tname.capitalize()} Edition  ·  planneratlas.etsy.com")
    cv.showPage()

# ─── JAHRESÜBERSICHT ─────────────────────────────────────────
def jahres(cv, t):
    bg(cv, t); hdr(cv, t, "Vista Anual", "______")
    gx = 14*mm; gy = H-38*mm
    cw = (W-28*mm)/3; rh = (gy-MB-6*mm)/4
    dl = ["Mo","Di","Mi","Do","Fr","Sa","So"]
    for idx,month in enumerate(MONTHS):
        col=idx%3; row=idx//3
        mx=gx+col*cw; my=gy-row*rh
        cv.setFillColor(colors.white)
        cv.roundRect(mx+1.5*mm, my-rh+2*mm, cw-3*mm, rh-3*mm, 6, fill=1, stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.6)
        cv.roundRect(mx+1.5*mm, my-rh+2*mm, cw-3*mm, rh-3*mm, 6, fill=0, stroke=1)
        # Month name bar
        cv.setFillColor(t["P"])
        cv.roundRect(mx+1.5*mm, my-9*mm, cw-3*mm, 8*mm, 6, fill=1, stroke=0)
        cv.rect(mx+1.5*mm, my-9*mm, cw-3*mm, 4*mm, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 9)
        cv.drawString(mx+4*mm, my-6.5*mm, month)
        # Day headers
        cw2 = (cw-5*mm)/7
        for d,dl2 in enumerate(dl):
            dx=mx+2.5*mm+d*cw2
            cv.setFillColor(t["WA"] if d>=5 else t["MU"]); cv.setFont("HN-M",6.5)
            cv.drawCentredString(dx+cw2/2, my-13.5*mm, dl2)
        # Day cells
        for r in range(6):
            for d in range(7):
                dx=mx+2.5*mm+d*cw2; dy=my-18*mm-r*5.2*mm
                cv.setFillColor(t["WE"] if d>=5 else t["Pl"])
                cv.roundRect(dx+0.3, dy, cw2-0.6, 4.5*mm, 1.5, fill=1, stroke=0)
                cv.setFillColor(t["R"]); cv.circle(dx+cw2/2, dy+2.2*mm, 0.7*mm, fill=1, stroke=0)
    ftr(cv, t, "Vista Anual"); cv.showPage()

# ─── MONATSÜBERSICHT ─────────────────────────────────────────
def monats(cv, t):
    bg(cv, t); hdr(cv, t, "Vista Mensual", "_____________ · ______")
    lx=14*mm; rx=W-14*mm; gw=rx-lx; yt=H-39*mm
    dlw=13*mm; wcw=(gw-dlw)/4; rh=10.5*mm
    dl=["Mo","Di","Mi","Do","Fr","Sa","So"]
    for wk in range(4):
        wx=lx+dlw+wk*wcw
        cv.setFillColor(t["P"]); cv.roundRect(wx+1*mm, yt-7.5*mm, wcw-2*mm, 6.5*mm, 3, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B", 8)
        cv.drawCentredString(wx+wcw/2, yt-5*mm, f"Semana {wk+1}")
        for d,day in enumerate(dl):
            dy2=yt-11*mm-d*rh; iw=d>=5
            if wk==0:
                cv.setFillColor(t["Pl"]); cv.rect(lx, dy2-rh+0.5*mm, dlw, rh-1*mm, fill=1, stroke=0)
                cv.setFillColor(t["P"]); cv.setFont("HN-B",8.5)
                cv.drawCentredString(lx+dlw/2, dy2-rh/2-1.5*mm, day)
            cv.setFillColor(t["WE"] if iw else colors.white)
            cv.rect(wx+0.5*mm, dy2-rh+0.5*mm, wcw-1*mm, rh-1*mm, fill=1, stroke=0)
            cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
            cv.rect(wx+0.5*mm, dy2-rh+0.5*mm, wcw-1*mm, rh-1*mm, fill=0, stroke=1)
            cv.setFillColor(t["Pl"]); cv.roundRect(wx+1.5*mm, dy2-3.5*mm, 5.5*mm, 4*mm, 2, fill=1, stroke=0)
            cv.setFillColor(t["MU"]); cv.setFont("HN",7.5)
            cv.drawCentredString(wx+4.25*mm, dy2-1.5*mm, "__")
    cv.setStrokeColor(t["P"]); cv.setLineWidth(0.8)
    cv.rect(lx, yt-11*mm-7*rh, gw, 7*rh+8*mm, fill=0, stroke=1)
    ny=yt-11*mm-7*rh-8*mm
    cv.setFillColor(t["P"]); cv.setFont("HN-B",9.5)
    cv.drawString(lx, ny-4*mm, "Notas y Objetivos del Mes")
    cv.setStrokeColor(t["A"]); cv.setLineWidth(2)
    cv.line(lx, ny-6.5*mm, lx+58*mm, ny-6.5*mm)
    ly=ny-14*mm
    while ly>MB+8*mm:
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4); cv.line(lx, ly, rx, ly); ly-=7.5*mm
    ftr(cv, t, "Vista Mensual"); cv.showPage()

# ─── WOCHENPLANER ────────────────────────────────────────────
def woche(cv, t):
    bg(cv, t); hdr(cv, t, "Planificador", "Semana ____  ·  Del ____. al ____. de _____________")
    yt=H-39*mm; yb=MB+12*mm; ch=yt-yb
    lx=14*mm; rx=W-14*mm; tw=rx-lx
    dw=tw*0.67; gap=4*mm; sw=tw-dw-gap; sx=lx+dw+gap
    dh=ch/7; lpd=5; lg=(dh-10.5*mm)/lpd

    for i,(ab,full) in enumerate(DAYS):
        yt2=yt-i*dh; yb2=yt2-dh; iw=i>=5
        tc=t["WA"] if iw else t["P"]
        # Row bg
        cv.setFillColor(t["WE"] if iw else t["Pl"])
        cv.rect(lx, yb2, dw, dh, fill=1, stroke=0)
        # Day tab
        cv.setFillColor(tc); cv.rect(lx, yb2, 11*mm, dh, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B",10.5)
        cv.drawCentredString(lx+5.5*mm, yb2+dh/2-2*mm, ab)
        # Day name
        cv.setFillColor(t["TX"]); cv.setFont("HN-B",9)
        cv.drawString(lx+14*mm, yt2-6*mm, full)
        # Date placeholder
        cv.setFillColor(t["MU"]); cv.setFont("HN",8)
        cv.drawString(lx+44*mm, yt2-6*mm, "__.__")
        # Priority chip
        cv.setFillColor(tc)
        cv.roundRect(lx+dw-23*mm, yt2-7.5*mm, 21*mm, 5.5*mm, 2.5, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN",6.5)
        cv.drawCentredString(lx+dw-12.5*mm, yt2-5*mm, "Prioridad del Dia")
        # Write lines
        for l in range(lpd):
            ly2=yt2-11*mm-l*lg
            if ly2>yb2+2*mm:
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
                cv.line(lx+14*mm, ly2, lx+dw-2*mm, ly2)
        if i<6:
            cv.setStrokeColor(colors.HexColor("#bbc2e0") if not iw else colors.HexColor("#c8c0de"))
            cv.setLineWidth(0.7); cv.line(lx, yb2, lx+dw, yb2)

    cv.setStrokeColor(t["P"]); cv.setLineWidth(1)
    cv.rect(lx, yb, dw, ch, fill=0, stroke=1)

    # Sidebar
    secs=[("Esta Semana",3),("Objetivos de la Semana",4),("Notas",7),("Reflexion",3)]
    sy=yt; lh=8*mm; lhs=6.2*mm; sg=3.5*mm
    for label,n in secs:
        sh=lh+n*lhs; secy=sy-sh
        cv.setFillColor(colors.white); cv.roundRect(sx,secy,sw,sh,6,fill=1,stroke=0)
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.5)
        cv.roundRect(sx,secy,sw,sh,6,fill=0,stroke=1)
        cv.setFillColor(t["P"]); cv.roundRect(sx,secy+sh-lh,sw,lh,6,fill=1,stroke=0)
        cv.rect(sx,secy+sh-lh,sw,lh/2,fill=1,stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B",9)
        cv.drawString(sx+3.5*mm, secy+sh-lh+2.5*mm, label)
        for l in range(n):
            ly2=secy+sh-lh-(l+1)*lhs+1.5*mm
            if ly2>secy+1.5*mm:
                cv.setStrokeColor(t["R"]); cv.setLineWidth(0.35)
                cv.line(sx+2.5*mm,ly2,sx+sw-2.5*mm,ly2)
        sy=secy-sg

    ftr(cv, t, "Planificador Semanal Sin Fecha"); cv.showPage()

# ─── HABIT TRACKER ───────────────────────────────────────────
def habit(cv, t):
    bg(cv, t); hdr(cv, t, "Habit Tracker", "_____________ · ______")
    lx=14*mm; rx=W-14*mm; yt=H-39*mm
    nh=10; nd=31; hlw=40*mm; cw=(rx-lx-hlw)/nd
    rh=(yt-MB-20*mm)/(nh+1)
    habits=["Ejercicio / Deporte","Agua (2 litros)","Comer saludable",
            "Leer (30 min.)","Meditacion","Levantarse temprano",
            "Sin redes sociales","Journaling","Gratitud",
            "Mi objetivo: ___________"]
    # Day number header
    for d in range(nd):
        dx=lx+hlw+d*cw; iw=d%7>=5
        cv.setFillColor(t["WA"] if iw else t["P"])
        cv.roundRect(dx+0.3*mm, yt-rh+0.5*mm, cw-0.6*mm, rh-1*mm, 2, fill=1, stroke=0)
        cv.setFillColor(colors.white); cv.setFont("HN-B",6.5)
        cv.drawCentredString(dx+cw/2, yt-rh/2-2*mm, str(d+1))
    # Habit rows
    for h,hab in enumerate(habits):
        hy=yt-(h+1)*rh; bg2=t["Pl"] if h%2==0 else colors.white
        cv.setFillColor(bg2); cv.rect(lx, hy-rh+0.5*mm, hlw, rh-1*mm, fill=1, stroke=0)
        cv.setFillColor(t["TX"] if h<9 else t["MU"])
        cv.setFont("HN-M" if h<9 else "HN", 8)
        cv.drawString(lx+2.5*mm, hy-rh/2-2*mm, hab)
        for d in range(nd):
            dx=lx+hlw+d*cw
            cv.setFillColor(bg2); cv.rect(dx+0.3*mm, hy-rh+0.5*mm, cw-0.6*mm, rh-1*mm, fill=1, stroke=0)
            r=min(cw,rh)*0.29
            cv.setStrokeColor(t["R"]); cv.setFillColor(colors.white); cv.setLineWidth(0.5)
            cv.circle(dx+cw/2, hy-rh/2, r, fill=1, stroke=1)
    cv.setStrokeColor(t["P"]); cv.setLineWidth(0.9)
    cv.rect(lx, yt-rh*(nh+1), rx-lx, rh*(nh+1), fill=0, stroke=1)
    # Quote / goal box
    qy=yt-rh*(nh+1)-5*mm
    cv.setFillColor(t["Pl"])
    cv.roundRect(lx, MB+8*mm, rx-lx, qy-MB-8*mm, 6, fill=1, stroke=0)
    cv.setStrokeColor(t["A"]); cv.setLineWidth(4)
    cv.line(lx, MB+8*mm, lx, qy)
    cv.setFillColor(t["P"]); cv.setFont("HN-B", 9.5)
    cv.drawString(lx+5*mm, qy-9*mm, "\"Kleine Schritte jeden Tag fuhren zu grossen Veranderungen.\"")
    cv.setFillColor(t["MU"]); cv.setFont("HN", 8.5)
    cv.drawString(lx+5*mm, qy-18*mm, "Mi objetivo del mes:  ___________________________________________")
    ftr(cv, t, "Habit Tracker"); cv.showPage()

# ─── NOTIZEN ─────────────────────────────────────────────────
def notizen(cv, t):
    bg(cv, t); hdr(cv, t, "Notas", "")
    lx=14*mm; rx=W-14*mm; y=H-43*mm
    while y>MB+10*mm:
        cv.setStrokeColor(t["R"]); cv.setLineWidth(0.4); cv.line(lx, y, rx, y); y-=9*mm
    ftr(cv, t, "Notas"); cv.showPage()

# ─── GENERATE ────────────────────────────────────────────────
OUT = "/Users/vascobotelhodacosta/Morgan/businesses/planners"
os.makedirs(OUT, exist_ok=True)

for tname, tp in THEMES.items():
    out = f"{OUT}/planificador_ES_{tname}.pdf"
    cv = canvas.Canvas(out, pagesize=A4)
    cover(cv, tp, tname)
    jahres(cv, tp)
    monats(cv, tp)
    woche(cv, tp)
    habit(cv, tp)
    notizen(cv, tp)
    cv.save()
    print(f"OK  {tname:12} -> {out}")

print("\nProntos.")
