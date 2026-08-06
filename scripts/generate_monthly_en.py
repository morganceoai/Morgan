"""PlannerAtlas — Monthly Planner EN (Premium) — 16 páginas"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

GREEN   = HexColor("#1B4332"); GOLD  = HexColor("#C9A84C"); CREAM = HexColor("#FAFAF5")
LGRID   = HexColor("#D4E8DC"); MINT  = HexColor("#F0FAF4"); WCREAM= HexColor("#FFF9EE")
ALTROW  = HexColor("#EEF6F1"); WHITE = HexColor("#FFFFFF"); GRAYTEXT = HexColor("#6B7280")
DARKTEXT= HexColor("#1B4332")
W, H = A4; M = 18 * mm
DAYS   = ["MON","TUE","WED","THU","FRI","SAT","SUN"]
MONTHS = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def footer(c, label=""):
    c.setFont("Helvetica", 6.5); c.setFillColor(GRAYTEXT)
    c.drawString(M, 10*mm, "planneratlas.etsy.com")
    if label: c.drawRightString(W-M, 10*mm, label)

def header(c, title, y=None):
    if y is None: y = H - 14*mm
    bar_h = 11*mm
    c.setFillColor(GREEN); c.rect(0, y-bar_h, W, bar_h, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold", 9)
    c.drawString(M, y-bar_h+3.5*mm, title)
    return y - bar_h

def page_cover(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,10*mm,H,fill=1,stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8)
    c.line(M+2*mm, H-30*mm, W-M, H-30*mm)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",11)
    c.drawString(M+2*mm, H-22*mm, "PA")
    c.setFont("Helvetica-Bold",42)
    c.drawString(M+2*mm, H*0.55, "MONTHLY")
    c.drawString(M+2*mm, H*0.55-48, "PLANNER")
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm, H*0.55-64, "PREMIUM COLLECTION")
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm, H*0.55-76, "UNDATED  ·  A4")
    items = ["Yearly Overview","January – December (12 pages)","Goals & Intentions","Notes × 2"]
    y = H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in items: c.drawString(M+2*mm, y, item); y -= 14
    footer(c); c.showPage()

def page_yearly(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c, "YEARLY OVERVIEW")
    cell_w = (W-2*M)/4; grid_top = y-16*mm; cell_h = (grid_top-24*mm)/3
    row_h_inner = cell_h - 16*mm
    for i, month in enumerate(MONTHS):
        col = i%4; row = i//4
        x0 = M+col*cell_w; y0 = grid_top-(row+1)*cell_h+4*mm
        name_h=6*mm; days_h=5*mm; total_h=name_h+days_h+row_h_inner
        box_x=x0+1*mm; box_w=cell_w-4*mm
        c.setFillColor(WHITE); c.rect(box_x,y0,box_w,total_h,fill=1,stroke=0)
        # nome mês — fundo verde, letra branca
        c.setFillColor(GREEN); c.rect(box_x,y0+days_h+row_h_inner,box_w,name_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawString(box_x+2*mm, y0+days_h+row_h_inner+1.5*mm, month.upper())
        day_labels=["Mo","Tu","We","Th","Fr","Sa","Su"]; day_col_w=box_w/7
        c.setFillColor(GREEN); c.rect(box_x,y0+row_h_inner,box_w,days_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",5.5)
        for d,lbl in enumerate(day_labels):
            c.drawCentredString(box_x+d*day_col_w+day_col_w/2, y0+row_h_inner+1.5*mm, lbl)
        week_row_h=row_h_inner/6
        for week in range(6):
            wy=y0+week*week_row_h; c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(box_x,wy,box_x+box_w,wy)
        for d in range(1,7):
            c.line(box_x+d*day_col_w,y0,box_x+d*day_col_w,y0+row_h_inner)
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.rect(box_x,y0,box_w,total_h,fill=0,stroke=1)
    footer(c,"Yearly Overview"); c.showPage()

def page_month(c, month_name):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c, month_name.upper())

    # Linha Year
    label_y = y - 10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M, label_y, "Year:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+15*mm, label_y+1, M+60*mm, label_y+1)

    grid_top = y - 22*mm
    # reservar 65mm no fundo para goals + notes
    grid_h = grid_top - 65*mm
    col_w = (W-2*M)/7; row_h = grid_h/6

    # Cabeçalho dias
    day_colors = [GREEN]*5 + [GOLD]*2
    for d,(day,col) in enumerate(zip(DAYS, day_colors)):
        x = M+d*col_w
        c.setFillColor(col); c.rect(x,grid_top,col_w,9*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawCentredString(x+col_w/2, grid_top+2.8*mm, day)

    # Grelha 6×7
    for row in range(6):
        for col in range(7):
            x=M+col*col_w; yy=grid_top-(row+1)*row_h
            fill=WCREAM if col>=5 else MINT
            c.setFillColor(fill); c.rect(x,yy,col_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(x,yy,col_w,row_h,fill=0,stroke=1)
            # número dia (canto sup. esq.)
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6)
            c.drawString(x+1.5*mm, yy+row_h-4*mm, "")

    grid_bottom = grid_top - grid_h  # = 65mm from bottom

    # Goals do mês
    goals_y = grid_bottom - 6*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
    c.drawString(M, goals_y, "Monthly Goals")
    half = (W-2*M)/2
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    for i in range(3):
        ly = goals_y - 8*mm - i*8*mm
        if ly > 30*mm:
            c.line(M, ly, M+half-4*mm, ly)

    # Notes
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
    c.drawString(M+half+4*mm, goals_y, "Notes")
    for i in range(3):
        ly = goals_y - 8*mm - i*8*mm
        if ly > 30*mm:
            c.line(M+half+4*mm, ly, W-M, ly)

    footer(c, month_name); c.showPage()

def page_goals(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c,"GOALS & INTENTIONS")
    sections = [
        ("ANNUAL GOAL","What is your main goal this year?"),
        ("WHY IT MATTERS","Your deeper reason and motivation"),
        ("ACTION STEPS","Break it down into monthly actions"),
        ("POTENTIAL OBSTACLES","What might get in the way?"),
        ("HOW I'LL OVERCOME THEM","Your strategy"),
        ("REWARD","How will you celebrate success?"),
    ]
    box_h = (y-30*mm)/len(sections)
    for idx,(title,prompt) in enumerate(sections):
        by = y-(idx+1)*box_h
        bg = ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",7.5)
        c.drawString(M+3*mm, by+box_h-6*mm, title)
        c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
        c.drawString(M+3*mm, by+box_h-11*mm, prompt)
        lines = max(1,int((box_h-14*mm)/7))
        for li in range(lines):
            ly = by+box_h-15*mm-li*7*mm
            if ly > by+2*mm:
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.line(M+3*mm, ly, W-M-3*mm, ly)
    footer(c,"Goals & Intentions"); c.showPage()

def page_notes(c, num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c,"NOTES")
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M, y-10*mm, "Title / Topic:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm, y-10*mm+1, W-M, y-10*mm+1)
    line_start=y-18*mm; line_spacing=10*mm
    num_lines=int((line_start-22*mm)/line_spacing)
    for i in range(num_lines):
        ly=line_start-i*line_spacing
        bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ly-line_spacing+1,W-2*M,line_spacing-1,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.line(M,ly,W-M,ly)
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    c.line(M,line_start-num_lines*line_spacing,W-M,line_start-num_lines*line_spacing)
    footer(c,f"Notes {num}"); c.showPage()

def generate():
    out = "scripts/monthly_planner_EN.pdf"
    c = canvas.Canvas(out, pagesize=A4)
    c.setTitle("Monthly Planner — Premium Collection")
    c.setAuthor("PlannerAtlas")
    page_cover(c)
    page_yearly(c)
    for month in MONTHS:
        page_month(c, month)
    page_goals(c)
    page_notes(c,1); page_notes(c,2)
    c.save(); print(f"✅ {out}")

if __name__ == "__main__":
    generate()
