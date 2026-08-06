"""PlannerAtlas — Daily Planner EN (Premium) — 14 páginas"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

GREEN   = HexColor("#1B4332"); GOLD  = HexColor("#C9A84C"); CREAM = HexColor("#FAFAF5")
LGRID   = HexColor("#D4E8DC"); MINT  = HexColor("#F0FAF4"); WCREAM= HexColor("#FFF9EE")
ALTROW  = HexColor("#EEF6F1"); WHITE = HexColor("#FFFFFF"); GRAYTEXT = HexColor("#6B7280")
DARKTEXT= HexColor("#1B4332")
W, H = A4; M = 18 * mm

def footer(c, label=""):
    c.setFont("Helvetica",6.5); c.setFillColor(GRAYTEXT)
    c.drawString(M,10*mm,"planneratlas.etsy.com")
    if label: c.drawRightString(W-M,10*mm,label)

def header(c, title):
    bar_h=11*mm; y=H-14*mm
    c.setFillColor(GREEN); c.rect(0,y-bar_h,W,bar_h,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",9)
    c.drawString(M, y-bar_h+3.5*mm, title)
    return y-bar_h

def hline(c, y, x1=None, x2=None):
    if x1 is None: x1=M
    if x2 is None: x2=W-M
    c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.line(x1,y,x2,y)

def page_cover(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,10*mm,H,fill=1,stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8)
    c.line(M+2*mm,H-30*mm,W-M,H-30*mm)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",11)
    c.drawString(M+2*mm,H-22*mm,"PA")
    c.setFont("Helvetica-Bold",42)
    c.drawString(M+2*mm,H*0.55,"DAILY")
    c.drawString(M+2*mm,H*0.55-48,"PLANNER")
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm,H*0.55-64,"PREMIUM COLLECTION")
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm,H*0.55-76,"UNDATED  ·  A4")
    items=["Monthly Overview","Daily Pages × 10","Habit Tracker","Notes × 2"]
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in items: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

def page_monthly_overview(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c,"MONTHLY OVERVIEW")
    grid_top = y-22*mm
    label_y = grid_top+12*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M, label_y, "Month / Year:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm, label_y+1, W-M, label_y+1)
    grid_h = grid_top-72*mm; col_w=(W-2*M)/7; row_h=grid_h/6
    days=["MON","TUE","WED","THU","FRI","SAT","SUN"]
    day_colors=[GREEN]*5+[GOLD]*2
    for d,(day,col) in enumerate(zip(days,day_colors)):
        x=M+d*col_w
        c.setFillColor(col); c.rect(x,grid_top,col_w,9*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawCentredString(x+col_w/2,grid_top+2.8*mm,day)
    for row in range(6):
        for col in range(7):
            x=M+col*col_w; yy=grid_top-(row+1)*row_h
            fill=WCREAM if col>=5 else MINT
            c.setFillColor(fill); c.rect(x,yy,col_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(x,yy,col_w,row_h,fill=0,stroke=1)
    notes_y=grid_top-6*row_h-8*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,notes_y,"Notes & Goals of the Month")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    for i in range(4):
        ly=notes_y-10*mm-i*10*mm
        if ly>30*mm: c.line(M,ly,W-M,ly)
    footer(c,"Monthly Overview"); c.showPage()

def page_daily(c, day_num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c, f"DAILY PLANNER — DAY {day_num}")

    # Data e intenção
    row1_y = y - 9*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
    c.drawString(M, row1_y, "Date:")
    hline(c, row1_y+1, M+14*mm, M+55*mm)
    c.drawString(M+60*mm, row1_y, "Day:")
    hline(c, row1_y+1, M+73*mm, W-M)

    # Secção manhã
    morning_y = y - 18*mm
    c.setFillColor(GREEN); c.rect(M, morning_y-8*mm, W-2*M, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(M+3*mm, morning_y-5.5*mm, "MORNING ROUTINE")

    fields = [("Today I'm grateful for:", 28*mm), ("Daily affirmation:", 28*mm), ("Today's intention:", 20*mm)]
    fy = morning_y - 10*mm
    for label, width in fields:
        fy -= 8*mm
        c.setFillColor(GREEN); c.setFont("Helvetica",7.5)
        c.drawString(M+3*mm, fy, label)
        hline(c, fy+1, M+3*mm+width, W-M-3*mm)

    # Top 3 Priorities
    prio_y = fy - 10*mm
    c.setFillColor(GREEN); c.rect(M, prio_y-8*mm, (W-2*M)/2-4*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(M+3*mm, prio_y-5.5*mm, "TOP 3 PRIORITIES")
    half = (W-2*M)/2
    for i in range(3):
        py = prio_y - 12*mm - i*11*mm
        if py > 30*mm:
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold",11)
            c.drawString(M+2*mm, py, str(i+1)+".")
            hline(c, py-1, M+12*mm, M+half-4*mm)
    # blank rows
    blank_start = prio_y - 12*mm - 3*11*mm - 4*mm
    blank_count = 0
    while blank_start - (blank_count+1)*11*mm > 80*mm + 16*mm: blank_count += 1
    for i in range(blank_count):
        py = blank_start - i*11*mm
        if py > 80*mm + 16*mm:
            hline(c, py-1, M+12*mm, M+half-4*mm)

    # Schedule
    sched_x = M + half + 4*mm
    c.setFillColor(GREEN); c.rect(sched_x, prio_y-8*mm, half-4*mm, 8*mm, fill=1, stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(sched_x+3*mm, prio_y-5.5*mm, "SCHEDULE")

    slots = ["6:00","7:00","8:00","9:00","10:00","11:00","12:00","13:00",
             "14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00","22:00"]
    sched_top = prio_y - 10*mm
    sched_h = sched_top - 30*mm
    row_h = sched_h / len(slots)
    for i, slot in enumerate(slots):
        sy = sched_top - (i+1)*row_h
        bg = ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(sched_x, sy, half-4*mm, row_h, fill=1, stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3)
        c.rect(sched_x, sy, half-4*mm, row_h, fill=0, stroke=1)
        c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6.5)
        c.drawString(sched_x+1.5*mm, sy+row_h/2-2, slot)

    # Evening Reflection
    evn_y = prio_y - 12*mm - 3*11*mm - 4*mm - 10*mm
    if evn_y > 80*mm:
        c.setFillColor(GREEN); c.rect(M, evn_y-8*mm, half-4*mm, 8*mm, fill=1, stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm, evn_y-5.5*mm, "EVENING REFLECTION")
        evn_labels = ["Best moment today:", "What I learned:", "Tomorrow's focus:"]
        for i, lbl in enumerate(evn_labels):
            ly = evn_y - 14*mm - i*10*mm
            if ly > 30*mm:
                c.setFillColor(GREEN); c.setFont("Helvetica",7.5)
                c.drawString(M+3*mm, ly+3*mm, lbl)
                hline(c, ly, M+3*mm+38*mm, M+half-4*mm)

    footer(c, f"Day {day_num}"); c.showPage()

def page_habit(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y = header(c,"HABIT TRACKER")
    habits=["Exercise","Meditation","Reading","Hydration (2L)","Sleep 8h",
            "Journaling","Gratitude","No Sugar","Walk 10k steps","Vitamins"]
    label_w=45*mm; weeks=["Week 1","Week 2","Week 3","Week 4"]
    week_col_w=(W-2*M-label_w)/4; row_h=11*mm; header_y=y-10*mm
    c.setFillColor(GREEN); c.rect(M,header_y-8*mm,label_w,8*mm,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(M+2*mm,header_y-5.5*mm,"HABIT")
    for i,wk in enumerate(weeks):
        x=M+label_w+i*week_col_w
        c.setFillColor(GREEN); c.rect(x,header_y-8*mm,week_col_w,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
        c.drawCentredString(x+week_col_w/2,header_y-5.5*mm,wk)
    for idx,habit in enumerate(habits):
        ry=header_y-8*mm-(idx+1)*row_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",8)
        c.drawString(M+2*mm,ry+row_h/2-2,habit)
        for wi in range(4):
            wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
            for di in range(7):
                dx=wx+di*day_w; fill=WCREAM if di>=5 else bg
                c.setFillColor(fill); c.rect(dx,ry,day_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(dx,ry,day_w,row_h,fill=0,stroke=1)
    # blank rows
    blank_start=header_y-8*mm-len(habits)*row_h; blank_count=0
    while blank_start-(blank_count+1)*row_h > 22*mm: blank_count+=1
    for idx in range(blank_count):
        ry=blank_start-(idx+1)*row_h; bg=ALTROW if (len(habits)+idx)%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3)
        c.line(M+2*mm,ry+row_h/2,M+label_w-2*mm,ry+row_h/2)
        for wi in range(4):
            wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
            for di in range(7):
                dx=wx+di*day_w; fill=WCREAM if di>=5 else bg
                c.setFillColor(fill); c.rect(dx,ry,day_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(dx,ry,day_w,row_h,fill=0,stroke=1)
    legend_y=header_y-8*mm-(len(habits)+blank_count+0.3)*row_h
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6.5)
    for wi in range(4):
        wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
        for di,da in enumerate(["M","T","W","T","F","S","S"]):
            c.drawCentredString(wx+di*day_w+day_w/2,legend_y,da)
    footer(c,"Habit Tracker"); c.showPage()

def page_notes(c, num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=header(c,"NOTES")
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,y-10*mm,"Title / Topic:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm,y-10*mm+1,W-M,y-10*mm+1)
    line_start=y-18*mm; line_spacing=10*mm
    num_lines=int((line_start-22*mm)/line_spacing)
    for i in range(num_lines):
        ly=line_start-i*line_spacing; bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ly-line_spacing+1,W-2*M,line_spacing-1,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.line(M,ly,W-M,ly)
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    c.line(M,line_start-num_lines*line_spacing,W-M,line_start-num_lines*line_spacing)
    footer(c,f"Notes {num}"); c.showPage()

def generate():
    out="scripts/daily_planner_EN.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle("Daily Planner — Premium Collection"); c.setAuthor("PlannerAtlas")
    page_cover(c); page_monthly_overview(c)
    for d in range(1,11): page_daily(c,d)
    page_habit(c); page_notes(c,1); page_notes(c,2)
    c.save(); print(f"✅ {out}")

if __name__=="__main__": generate()
