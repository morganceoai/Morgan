"""PlannerAtlas — Gerador multilingua: DE / ES / PT — 6 produtos × 3 linguas = 18 PDFs"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from lang import LANGS

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

GREEN=HexColor("#1B4332"); GOLD=HexColor("#C9A84C"); CREAM=HexColor("#FAFAF5")
LGRID=HexColor("#D4E8DC"); MINT=HexColor("#F0FAF4"); WCREAM=HexColor("#FFF9EE")
ALTROW=HexColor("#EEF6F1"); WHITE=HexColor("#FFFFFF"); GRAYTEXT=HexColor("#6B7280")
DARKTEXT=HexColor("#1B4332")
W,H=A4; M=18*mm

# ── helpers ──────────────────────────────────────────────────────────────────
def footer(c,label=""):
    c.setFont("Helvetica",6.5); c.setFillColor(GRAYTEXT)
    c.drawString(M,10*mm,"planneratlas.etsy.com")
    if label: c.drawRightString(W-M,10*mm,label)

def hdr(c,title):
    bar_h=11*mm; y=H-14*mm
    c.setFillColor(GREEN); c.rect(0,y-bar_h,W,bar_h,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",9)
    c.drawString(M,y-bar_h+3.5*mm,title)
    return y-bar_h

def hline(c,y,x1=None,x2=None):
    if x1 is None: x1=M
    if x2 is None: x2=W-M
    c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.line(x1,y,x2,y)

def cover_base(c,line1,line2,L):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,10*mm,H,fill=1,stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8)
    c.line(M+2*mm,H-30*mm,W-M,H-30*mm)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",11)
    c.drawString(M+2*mm,H-22*mm,"PA")
    c.setFont("Helvetica-Bold",38)
    c.drawString(M+2*mm,H*0.55,line1)
    c.drawString(M+2*mm,H*0.55-44,line2)
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm,H*0.55-60,L["premium"])
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm,H*0.55-72,L["undated"])

def yearly_mini(c,months_list,days_mini):
    """Mini-calendário 4×3 partilhado por weekly e monthly."""
    y=hdr(c,LANGS_CUR["YEARLY_OVERVIEW"])
    cell_w=(W-2*M)/4; grid_top=y-16*mm; cell_h=(grid_top-24*mm)/3
    row_h_inner=cell_h-16*mm
    for i,month in enumerate(months_list):
        col=i%4; row=i//4
        x0=M+col*cell_w; y0=grid_top-(row+1)*cell_h+4*mm
        name_h=6*mm; days_h=5*mm; total_h=name_h+days_h+row_h_inner
        box_x=x0+1*mm; box_w=cell_w-4*mm
        c.setFillColor(WHITE); c.rect(box_x,y0,box_w,total_h,fill=1,stroke=0)
        c.setFillColor(GREEN); c.rect(box_x,y0+days_h+row_h_inner,box_w,name_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawString(box_x+2*mm,y0+days_h+row_h_inner+1.5*mm,month.upper())
        day_col_w=box_w/7
        c.setFillColor(GREEN); c.rect(box_x,y0+row_h_inner,box_w,days_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",5.5)
        for d,lbl in enumerate(days_mini):
            c.drawCentredString(box_x+d*day_col_w+day_col_w/2,y0+row_h_inner+1.5*mm,lbl)
        week_row_h=row_h_inner/6
        for week in range(6):
            wy=y0+week*week_row_h; c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(box_x,wy,box_x+box_w,wy)
        for d in range(1,7):
            c.line(box_x+d*day_col_w,y0,box_x+d*day_col_w,y0+row_h_inner)
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.rect(box_x,y0,box_w,total_h,fill=0,stroke=1)
    footer(c,LANGS_CUR["YEARLY_OVERVIEW"]); c.showPage()

def monthly_grid_page(c,month_name,L):
    """Página mensal para Monthly Planner."""
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,month_name.upper())
    label_y=y-10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,label_y,L["YEAR"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+15*mm,label_y+1,M+60*mm,label_y+1)
    grid_top=y-22*mm; grid_h=grid_top-65*mm
    col_w=(W-2*M)/7; row_h=grid_h/6
    day_colors=[GREEN]*5+[GOLD]*2
    for d,(day,col) in enumerate(zip(L["days"],day_colors)):
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
    grid_bottom=grid_top-grid_h
    goals_y=grid_bottom-6*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
    c.drawString(M,goals_y,L["MONTHLY_GOALS"])
    half=(W-2*M)/2
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    for i in range(3):
        ly=goals_y-8*mm-i*8*mm
        if ly>30*mm: c.line(M,ly,M+half-4*mm,ly)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
    c.drawString(M+half+4*mm,goals_y,L["NOTES"])
    for i in range(3):
        ly=goals_y-8*mm-i*8*mm
        if ly>30*mm: c.line(M+half+4*mm,ly,W-M,ly)
    footer(c,month_name); c.showPage()

def goals_page(c,L,sections):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["GOALS_INTENTIONS"])
    box_h=(y-30*mm)/len(sections)
    for idx,(title,prompt) in enumerate(sections):
        by=y-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",7.5)
        c.drawString(M+3*mm,by+box_h-6*mm,title)
        c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
        c.drawString(M+3*mm,by+box_h-11*mm,prompt)
        lines=max(1,int((box_h-14*mm)/7))
        for li in range(lines):
            ly=by+box_h-15*mm-li*7*mm
            if ly>by+2*mm:
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.line(M+3*mm,ly,W-M-3*mm,ly)
    footer(c,L["GOALS_INTENTIONS"]); c.showPage()

def notes_page(c,L,num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["NOTES"])
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,y-10*mm,L["NOTES_TITLE"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm,y-10*mm+1,W-M,y-10*mm+1)
    ls=y-18*mm; sp=10*mm; nl=int((ls-22*mm)/sp)
    for i in range(nl):
        ly=ls-i*sp; bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ly-sp+1,W-2*M,sp-1,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.line(M,ly,W-M,ly)
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    c.line(M,ls-nl*sp,W-M,ls-nl*sp)
    footer(c,f"{L['NOTES']} {num}"); c.showPage()

def monthly_overview_grid(c,L):
    """Página 'monthly overview' partilhada por weekly e daily planner."""
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["MONTHLY_OVERVIEW"])
    grid_top=y-22*mm
    label_y=grid_top+12*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,label_y,L["MONTHLY_OVERVIEW_LABEL"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm,label_y+1,W-M,label_y+1)
    grid_h=grid_top-72*mm; col_w=(W-2*M)/7; row_h=grid_h/6
    day_colors=[GREEN]*5+[GOLD]*2
    for d,(day,col) in enumerate(zip(L["days"],day_colors)):
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
    c.drawString(M,notes_y,L["NOTES_GOALS_MONTH"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    for i in range(4):
        ly=notes_y-10*mm-i*10*mm
        if ly>30*mm: c.line(M,ly,W-M,ly)
    footer(c,L["MONTHLY_OVERVIEW"]); c.showPage()

def habit_tracker_grid(c,L,habits,weeks,label_habit,label_w=45*mm):
    """Grelha de habit tracker reutilizável (weekly e daily planner)."""
    row_h=11*mm; week_col_w=(W-2*M-label_w)/len(weeks); header_y=L["_hy"]
    c.setFillColor(GREEN); c.rect(M,header_y-8*mm,label_w,8*mm,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(M+2*mm,header_y-5.5*mm,label_habit)
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
        for wi in range(len(weeks)):
            wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
            for di in range(7):
                dx=wx+di*day_w; fill=WCREAM if di>=5 else bg
                c.setFillColor(fill); c.rect(dx,ry,day_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(dx,ry,day_w,row_h,fill=0,stroke=1)
    blank_start=header_y-8*mm-len(habits)*row_h; blank_count=0
    while blank_start-(blank_count+1)*row_h>22*mm: blank_count+=1
    for idx in range(blank_count):
        ry=blank_start-(idx+1)*row_h; bg=ALTROW if (len(habits)+idx)%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3)
        c.line(M+2*mm,ry+row_h/2,M+label_w-2*mm,ry+row_h/2)
        for wi in range(len(weeks)):
            wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
            for di in range(7):
                dx=wx+di*day_w; fill=WCREAM if di>=5 else bg
                c.setFillColor(fill); c.rect(dx,ry,day_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(dx,ry,day_w,row_h,fill=0,stroke=1)
    legend_y=header_y-8*mm-(len(habits)+blank_count+0.3)*row_h
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6.5)
    for wi in range(len(weeks)):
        wx=M+label_w+wi*week_col_w; day_w=week_col_w/7
        for di,da in enumerate(L["day_legend"]):
            c.drawCentredString(wx+di*day_w+day_w/2,legend_y,da)

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 1: WEEKLY PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def gen_weekly(lang_code, L, out_dir):
    out=f"{out_dir}/weekly_planner_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Weekly Planner — {L['premium']}"); c.setAuthor("PlannerAtlas")

    # Cover
    cover_base(c,L["weekly_title"][0],L["weekly_title"][1],L)
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["weekly_items"]: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

    # Yearly
    global LANGS_CUR; LANGS_CUR=L
    yearly_mini(c,L["months"],L["days_mini"])

    # Monthly Overview
    monthly_overview_grid(c,L)

    # 4 semanas
    for w in range(1,5):
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['WEEKLY_PLANNER']} — {L['week_x'](w)}")
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
        c.drawString(M,y-9*mm,L["WEEK_OF"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.line(M+24*mm,y-9*mm+1,M+70*mm,y-9*mm+1)
        c.setFont("Helvetica-Bold",8.5)
        c.drawString(M+80*mm,y-9*mm,L["WEEKLY_INTENTION"])
        c.line(M+116*mm,y-9*mm+1,W-M,y-9*mm+1)
        grid_top=y-20*mm; grid_h=grid_top-55*mm
        sidebar_w=18*mm; day_col_w=(W-2*M-sidebar_w)/7
        slots=["6:00","7:00","8:00","9:00","10:00","11:00","12:00","13:00",
               "14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00","22:00"]
        row_h=grid_h/len(slots)
        day_bg=[GREEN]*5+[GOLD]*2
        for d in range(7):
            x=M+sidebar_w+d*day_col_w
            c.setFillColor(day_bg[d]); c.rect(x,grid_top,day_col_w,9*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
            c.drawCentredString(x+day_col_w/2,grid_top+2.8*mm,L["days"][d])
        for i,slot in enumerate(slots):
            yy=grid_top-(i+1)*row_h
            c.setFillColor(ALTROW if i%2==0 else CREAM)
            c.rect(M,yy,sidebar_w,row_h,fill=1,stroke=0)
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6.5)
            c.drawString(M+1.5*mm,yy+row_h/2-2,slot)
            for d in range(7):
                x=M+sidebar_w+d*day_col_w
                fill=WCREAM if d>=5 else (ALTROW if i%2==0 else MINT)
                c.setFillColor(fill); c.rect(x,yy,day_col_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(x,yy,day_col_w,row_h,fill=0,stroke=1)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,grid_top-len(slots)*row_h,sidebar_w,len(slots)*row_h,fill=0,stroke=1)
        bottom_y=grid_top-len(slots)*row_h-5*mm; half=(W-2*M)/2
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M,bottom_y,L["TOP_PRIORITIES"])
        c.drawString(M+half+4*mm,bottom_y,L["NOTES"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        for i in range(3):
            ly=bottom_y-9*mm-i*9*mm
            if ly>30*mm:
                c.line(M,ly,M+half-4*mm,ly)
                c.line(M+half+4*mm,ly,W-M,ly)
        footer(c,L["week_x"](w)); c.showPage()

    # Habit Tracker
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["HABIT_TRACKER"])
    hy=y-10*mm; L["_hy"]=hy
    habit_tracker_grid(c,L,L["habits"],L["weeks"],L["HABIT"])
    footer(c,L["HABIT_TRACKER"]); c.showPage()

    # Mood Tracker
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["MOOD_TRACKER"])
    metrics=L["mood_metrics"]
    label_w=45*mm; mood_weeks=L["weeks"]+[L["weeks"][-1].replace("4","5")]
    week_col_w=(W-2*M-label_w)/5; row_h=10*mm; header_y=y-10*mm
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M,header_y+2*mm,"Rate each metric 1–10 daily.")
    c.setFillColor(GREEN); c.rect(M,header_y-8*mm,label_w,8*mm,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(M+2*mm,header_y-5.5*mm,L["METRIC"])
    for i,wk in enumerate(mood_weeks):
        x=M+label_w+i*week_col_w
        c.setFillColor(GREEN); c.rect(x,header_y-8*mm,week_col_w,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
        c.drawCentredString(x+week_col_w/2,header_y-5.5*mm,wk)
    for idx,metric in enumerate(metrics):
        ry=header_y-8*mm-(idx+1)*row_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",8)
        c.drawString(M+2*mm,ry+row_h/2-2,metric)
        for wi in range(5):
            wx=M+label_w+wi*week_col_w
            c.setFillColor(bg); c.rect(wx,ry,week_col_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(wx,ry,week_col_w,row_h,fill=0,stroke=1)
    blank_start=header_y-8*mm-len(metrics)*row_h; blank_count=0
    while blank_start-(blank_count+1)*row_h>60*mm: blank_count+=1
    for idx in range(blank_count):
        ry=blank_start-(idx+1)*row_h; bg=ALTROW if (len(metrics)+idx)%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3)
        c.line(M+2*mm,ry+row_h/2,M+label_w-2*mm,ry+row_h/2)
        for wi in range(5):
            wx=M+label_w+wi*week_col_w
            c.setFillColor(bg); c.rect(wx,ry,week_col_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(wx,ry,week_col_w,row_h,fill=0,stroke=1)
    notes_y=header_y-8*mm-(len(metrics)+blank_count+0.5)*row_h
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,notes_y,L["NOTES_REFLECTIONS"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    for i in range(5): c.line(M,notes_y-9*mm-i*9*mm,W-M,notes_y-9*mm-i*9*mm)
    footer(c,L["MOOD_TRACKER"]); c.showPage()

    # Goals
    goals_page(c,L,L["goal_sections"])
    # Notes
    notes_page(c,L,1); notes_page(c,L,2)

    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 2: MONTHLY PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def gen_monthly(lang_code,L,out_dir):
    out=f"{out_dir}/monthly_planner_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Monthly Planner — {L['premium']}"); c.setAuthor("PlannerAtlas")

    cover_base(c,L["monthly_title"][0],L["monthly_title"][1],L)
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["monthly_items"]: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

    global LANGS_CUR; LANGS_CUR=L
    yearly_mini(c,L["months"],L["days_mini"])

    for month in L["months"]: monthly_grid_page(c,month,L)

    goals_page(c,L,L["goal_sections"])
    notes_page(c,L,1); notes_page(c,L,2)
    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 3: DAILY PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def gen_daily(lang_code,L,out_dir):
    out=f"{out_dir}/daily_planner_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Daily Planner — {L['premium']}"); c.setAuthor("PlannerAtlas")

    cover_base(c,L["daily_title"][0],L["daily_title"][1],L)
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["daily_items"]: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

    monthly_overview_grid(c,L)

    for day_num in range(1,11):
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['HABIT_TRACKER'].split()[0].upper()} — {L['day_x'](day_num)}")
        # hack: use daily planner header text
        y=hdr(c,f"{L['NOTES'].split()[0][0]}... — {L['day_x'](day_num)}")
        # proper header
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['daily_title'][0].rstrip()} {L['daily_title'][1]} — {L['day_x'](day_num)}")

        row1_y=y-9*mm
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M,row1_y,L["DATE"])
        hline(c,row1_y+1,M+14*mm,M+55*mm)
        c.drawString(M+60*mm,row1_y,L["DAY"])
        hline(c,row1_y+1,M+73*mm,W-M)

        morning_y=y-18*mm
        c.setFillColor(GREEN); c.rect(M,morning_y-8*mm,W-2*M,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,morning_y-5.5*mm,L["MORNING_ROUTINE"])

        fields=[(L["GRATEFUL"],28*mm),(L["AFFIRMATION"],28*mm),(L["INTENTION"],20*mm)]
        fy=morning_y-10*mm
        for label,width in fields:
            fy-=8*mm
            c.setFillColor(GREEN); c.setFont("Helvetica",7.5)
            c.drawString(M+3*mm,fy,label)
            hline(c,fy+1,M+3*mm+width,W-M-3*mm)

        prio_y=fy-10*mm
        half=(W-2*M)/2
        c.setFillColor(GREEN); c.rect(M,prio_y-8*mm,half-4*mm,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,prio_y-5.5*mm,L["TOP3_PRIORITIES"])

        for i in range(3):
            py=prio_y-12*mm-i*11*mm
            if py>30*mm:
                c.setFillColor(GOLD); c.setFont("Helvetica-Bold",11)
                c.drawString(M+2*mm,py,str(i+1)+".")
                hline(c,py-1,M+12*mm,M+half-4*mm)
        blank_start=prio_y-12*mm-3*11*mm-4*mm; blank_count=0
        while blank_start-(blank_count+1)*11*mm>80*mm+16*mm: blank_count+=1
        for i in range(blank_count):
            py=blank_start-i*11*mm
            if py>80*mm+16*mm: hline(c,py-1,M+12*mm,M+half-4*mm)

        sched_x=M+half+4*mm
        c.setFillColor(GREEN); c.rect(sched_x,prio_y-8*mm,half-4*mm,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(sched_x+3*mm,prio_y-5.5*mm,L["SCHEDULE"])
        slots=["6:00","7:00","8:00","9:00","10:00","11:00","12:00","13:00",
               "14:00","15:00","16:00","17:00","18:00","19:00","20:00","21:00","22:00"]
        sched_top=prio_y-10*mm; sched_h=sched_top-30*mm; row_h=sched_h/len(slots)
        for i,slot in enumerate(slots):
            sy=sched_top-(i+1)*row_h; bg=ALTROW if i%2==0 else CREAM
            c.setFillColor(bg); c.rect(sched_x,sy,half-4*mm,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.rect(sched_x,sy,half-4*mm,row_h,fill=0,stroke=1)
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6.5)
            c.drawString(sched_x+1.5*mm,sy+row_h/2-2,slot)

        evn_y=prio_y-12*mm-3*11*mm-4*mm-10*mm
        if evn_y>80*mm:
            c.setFillColor(GREEN); c.rect(M,evn_y-8*mm,half-4*mm,8*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
            c.drawString(M+3*mm,evn_y-5.5*mm,L["EVENING_REFLECTION"])
            for i,lbl in enumerate([L["BEST_MOMENT"],L["LEARNED"],L["TOMORROW_FOCUS"]]):
                ly=evn_y-14*mm-i*10*mm
                if ly>30*mm:
                    c.setFillColor(GREEN); c.setFont("Helvetica",7.5)
                    c.drawString(M+3*mm,ly+3*mm,lbl)
                    hline(c,ly,M+3*mm+38*mm,M+half-4*mm)

        footer(c,L["day_x"](day_num)); c.showPage()

    # Habit tracker (simplified — same as weekly)
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["HABIT_TRACKER"])
    L["_hy"]=y-10*mm
    habit_tracker_grid(c,L,L["habits"],L["weeks"],L["HABIT"])
    footer(c,L["HABIT_TRACKER"]); c.showPage()

    notes_page(c,L,1); notes_page(c,L,2)
    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 4: HABIT TRACKER
# ══════════════════════════════════════════════════════════════════════════════
def gen_habit(lang_code,L,out_dir):
    out=f"{out_dir}/habit_tracker_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Habit Tracker — {L['premium']}"); c.setAuthor("PlannerAtlas")

    cover_base(c,L["habit_title"][0],L["habit_title"][1],L)
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["habit_items"]: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

    # How to use
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["HOW_TO_USE"])
    sy=y-14*mm; box_h=(sy-30*mm)/len(L["how_to_steps"])
    for idx,(title,text) in enumerate(L["how_to_steps"]):
        by=sy-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.rect(M,by,12*mm,box_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",16)
        c.drawCentredString(M+6*mm,by+box_h/2-5,str(idx+1))
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
        c.drawString(M+15*mm,by+box_h-7*mm,title)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
        words=text.split(); line=""; lines_out=[]; max_w=W-2*M-18*mm-6*mm
        for w in words:
            test=line+" "+w if line else w
            if c.stringWidth(test,"Helvetica",7.5)<max_w: line=test
            else: lines_out.append(line); line=w
        if line: lines_out.append(line)
        for li,ln in enumerate(lines_out[:3]):
            c.drawString(M+15*mm,by+box_h-14*mm-li*9,ln)
    footer(c,L["HOW_TO_USE"]); c.showPage()

    # Monthly trackers
    habits=L["habits"]
    for month in L["months"]:
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['HABIT_TRACKER']} — {month.upper()}")
        label_w=42*mm; days_in_month=31
        day_col_w=(W-2*M-label_w)/days_in_month
        row_h=10*mm; header_y=y-10*mm
        c.setFillColor(GREEN); c.rect(M,header_y-8*mm,label_w,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
        c.drawString(M+2*mm,header_y-5.5*mm,L["HABIT"])
        for d in range(days_in_month):
            x=M+label_w+d*day_col_w
            c.setFillColor(GREEN); c.rect(x,header_y-8*mm,day_col_w,8*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",5)
            c.drawCentredString(x+day_col_w/2,header_y-5.5*mm,str(d+1))
        for idx,habit in enumerate(habits):
            ry=header_y-8*mm-(idx+1)*row_h; bg=ALTROW if idx%2==0 else CREAM
            c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
            c.setFillColor(DARKTEXT); c.setFont("Helvetica",7)
            c.drawString(M+2*mm,ry+row_h/2-2,habit)
            for d in range(days_in_month):
                x=M+label_w+d*day_col_w
                c.setFillColor(bg); c.rect(x,ry,day_col_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(x,ry,day_col_w,row_h,fill=0,stroke=1)
        blank_start=header_y-8*mm-len(habits)*row_h; blank_count=0
        while blank_start-(blank_count+1)*row_h>22*mm: blank_count+=1
        for idx in range(blank_count):
            ry=blank_start-(idx+1)*row_h; bg=ALTROW if (len(habits)+idx)%2==0 else CREAM
            c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(M+2*mm,ry+row_h/2,M+label_w-2*mm,ry+row_h/2)
            for d in range(days_in_month):
                x=M+label_w+d*day_col_w
                c.setFillColor(bg); c.rect(x,ry,day_col_w,row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.rect(x,ry,day_col_w,row_h,fill=0,stroke=1)
        footer(c,month); c.showPage()

    # Habit reviews
    for num in range(1,3):
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['HABIT_REVIEW']} — Q{num*2-1}/Q{num*2}")
        box_h=(y-30*mm)/len(L["habit_review_sections"])
        for idx,(title,prompt) in enumerate(L["habit_review_sections"]):
            by=y-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
            c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
            c.setFillColor(GREEN); c.setFont("Helvetica-Bold",7.5)
            c.drawString(M+3*mm,by+box_h-6*mm,title)
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
            c.drawString(M+3*mm,by+box_h-11*mm,prompt)
            lines=max(1,int((box_h-14*mm)/7))
            for li in range(lines):
                ly=by+box_h-15*mm-li*7*mm
                if ly>by+2*mm:
                    c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                    c.line(M+3*mm,ly,W-M-3*mm,ly)
        footer(c,f"{L['HABIT_REVIEW']} Q{num*2-1}/Q{num*2}"); c.showPage()

    notes_page(c,L,1); notes_page(c,L,2)
    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 5: BUDGET PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def gen_budget(lang_code,L,out_dir):
    out=f"{out_dir}/budget_planner_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Budget Planner — {L['premium']}"); c.setAuthor("PlannerAtlas")

    cover_base(c,L["budget_title"][0],L["budget_title"][1],L)
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["budget_items"]: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

    def mini_hdr(c,title,x,y,w,h=8*mm):
        c.setFillColor(GREEN); c.rect(x,y-h,w,h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawString(x+2*mm,y-h+2.5*mm,title)

    # Annual overview
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["ANNUAL_OVERVIEW"])
    year_y=y-10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,year_y,L["YEAR"])
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+16*mm,year_y+1,M+55*mm,year_y+1)
    cols=L["annual_cols"]; col_w=[(W-2*M)*0.22,(W-2*M)*0.20,(W-2*M)*0.20,(W-2*M)*0.19,(W-2*M)*0.19]
    tbl_top=y-20*mm; row_h=10*mm; x=M
    for col,cw in zip(cols,col_w):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col); x+=cw
    for mi,month in enumerate(L["months"]):
        ry=tbl_top-8*mm-(mi+1)*row_h; bg=ALTROW if mi%2==0 else CREAM; x=M
        for i,(col,cw) in enumerate(zip(cols,col_w)):
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(x,ry,cw,row_h,fill=0,stroke=1)
            if i==0:
                c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
                c.drawString(x+2*mm,ry+row_h/2-2,month)
            x+=cw
    tot_y=tbl_top-8*mm-12*row_h; x=M
    for i,(col,cw) in enumerate(zip(cols,col_w)):
        c.setFillColor(MINT); c.rect(x,tot_y-row_h,cw,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.5); c.rect(x,tot_y-row_h,cw,row_h,fill=0,stroke=1)
        if i==0:
            c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
            c.drawString(x+2*mm,tot_y-row_h+row_h/2-2,L["TOTAL"])
        x+=cw
    footer(c,L["ANNUAL_OVERVIEW"]); c.showPage()

    # Monthly budgets
    EXPENSE_CATS=L["expense_cats"]
    for month in L["months"]:
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['BUDGET_LABEL']} — {month.upper()}")
        my=y-10*mm; c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
        c.drawString(M,my,L["MONTH_YEAR"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.line(M+32*mm,my+1,W-M,my+1)
        half=(W-2*M)/2; col_right=M+half+4*mm
        inc_y=y-20*mm
        mini_hdr(c,L["INCOME"],M,inc_y,half-4*mm)
        ir_h=8*mm
        for i,item in enumerate(L["income_items"]):
            ry=inc_y-8*mm-(i+1)*ir_h; bg=ALTROW if i%2==0 else CREAM
            c.setFillColor(bg); c.rect(M,ry,half-4*mm,ir_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(M,ry,half-4*mm,ir_h,fill=0,stroke=1)
            c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
            c.drawString(M+2*mm,ry+ir_h/2-2,item)
            c.setStrokeColor(LGRID); c.line(M+half-4*mm-18*mm,ry+ir_h/2,M+half-4*mm-2*mm,ry+ir_h/2)
        ti_y=inc_y-8*mm-(len(L["income_items"])+1)*ir_h
        c.setFillColor(MINT); c.rect(M,ti_y,half-4*mm,ir_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ti_y,half-4*mm,ir_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M+2*mm,ti_y+ir_h/2-2,L["TOTAL_INCOME"])
        c.setStrokeColor(LGRID); c.line(M+half-4*mm-18*mm,ti_y+ir_h/2,M+half-4*mm-2*mm,ti_y+ir_h/2)
        sum_y=y-20*mm
        mini_hdr(c,L["MONTHLY_SUMMARY"],col_right,sum_y,half-4*mm)
        sum_items=[(L["TOTAL_INCOME"],""),(L["TOTAL_EXPENSES"],""),(L["SAVINGS"],""),(L["BALANCE"],"")]
        sr_h=10*mm
        for i,(lbl,_) in enumerate(sum_items):
            ry=sum_y-8*mm-(i+1)*sr_h; bg=ALTROW if i%2==0 else CREAM
            c.setFillColor(bg); c.rect(col_right,ry,half-4*mm,sr_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(col_right,ry,half-4*mm,sr_h,fill=0,stroke=1)
            c.setFillColor(DARKTEXT); c.setFont("Helvetica",8)
            c.drawString(col_right+2*mm,ry+sr_h/2-2,lbl)
            c.setStrokeColor(LGRID); c.line(col_right+half-4*mm-22*mm,ry+sr_h/2,col_right+half-4*mm-2*mm,ry+sr_h/2)
        exp_y=ti_y-6*mm
        exp_table_h=exp_y-30*mm
        mini_hdr(c,L["EXPENSES"],M,exp_y,W-2*M)
        n=len(EXPENSE_CATS); half_n=(n+1)//2
        er_h=min(exp_table_h/half_n,8.5*mm)
        for i,cat in enumerate(EXPENSE_CATS):
            col_idx=i//half_n; row_idx=i%half_n
            cw=(W-2*M)/2; cx=M+col_idx*cw
            ry=exp_y-8*mm-(row_idx+1)*er_h; bg=ALTROW if i%2==0 else CREAM
            c.setFillColor(bg); c.rect(cx,ry,cw,er_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(cx,ry,cw,er_h,fill=0,stroke=1)
            c.setFillColor(DARKTEXT); c.setFont("Helvetica",7)
            c.drawString(cx+2*mm,ry+er_h/2-2,cat)
            c.setStrokeColor(LGRID); c.line(cx+cw-18*mm,ry+er_h/2,cx+cw-2*mm,ry+er_h/2)
        last_row_bottom=exp_y-8*mm-half_n*er_h; blank_count=0
        while last_row_bottom-(blank_count+1)*er_h>30*mm: blank_count+=1
        for bi in range(blank_count):
            for col_idx in range(2):
                cw=(W-2*M)/2; cx=M+col_idx*cw
                row_idx=half_n+bi
                ry=exp_y-8*mm-(row_idx+1)*er_h; bg=ALTROW if (len(EXPENSE_CATS)+bi*2+col_idx)%2==0 else CREAM
                if ry>30*mm:
                    c.setFillColor(bg); c.rect(cx,ry,cw,er_h,fill=1,stroke=0)
                    c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(cx,ry,cw,er_h,fill=0,stroke=1)
                    c.setStrokeColor(LGRID); c.line(cx+cw-18*mm,ry+er_h/2,cx+cw-2*mm,ry+er_h/2)
        footer(c,month); c.showPage()

    # Debt tracker
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["DEBT_TRACKER"])
    cols=L["debt_cols"]; col_w=[(W-2*M)*0.25,(W-2*M)*0.15,(W-2*M)*0.14,(W-2*M)*0.14,(W-2*M)*0.15,(W-2*M)*0.17]
    tbl_top=y-12*mm; row_h=11*mm; x=M
    for col,cw in zip(cols,col_w):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",6.5)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col); x+=cw
    rows=int((tbl_top-8*mm-30*mm)/row_h)
    for ri in range(rows):
        ry=tbl_top-8*mm-(ri+1)*row_h; bg=ALTROW if ri%2==0 else CREAM; x=M
        for cw in col_w:
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(x,ry,cw,row_h,fill=0,stroke=1); x+=cw
    footer(c,L["DEBT_TRACKER"]); c.showPage()

    # Savings goals
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["SAVINGS_GOALS"])
    goals=[f"{L['SAVINGS_GOALS'].split()[0]} {i+1}" for i in range(6)]
    box_h=(y-30*mm)/len(goals)
    for idx,goal in enumerate(goals):
        by=y-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,by+box_h-6*mm,goal)
        fields=[("Goal/Ziel/Meta:",""),("Target:","€"),("Deadline:",""),("Saved:","€"),("Left:","€")]
        fw=(W-2*M-6*mm)/len(fields)
        for fi,(lbl,unit) in enumerate(fields):
            fx=M+3*mm+fi*fw
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
            c.drawString(fx,by+box_h-12*mm,lbl)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(fx,by+box_h-19*mm,fx+fw-3*mm,by+box_h-19*mm)
        bar_y=by+4*mm; bar_h_px=5*mm; bar_w=W-2*M-6*mm
        c.setFillColor(LGRID); c.rect(M+3*mm,bar_y,bar_w,bar_h_px,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(M+3*mm,bar_y,bar_w,bar_h_px,fill=0,stroke=1)
        c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6)
        c.drawString(M+3*mm,bar_y-4*mm,"0%")
        c.drawRightString(M+3*mm+bar_w,bar_y-4*mm,"100%")
    footer(c,L["SAVINGS_GOALS"]); c.showPage()

    notes_page(c,L,1); notes_page(c,L,2)
    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# PRODUTO 6: MEAL PLANNER
# ══════════════════════════════════════════════════════════════════════════════
def gen_meal(lang_code,L,out_dir):
    out=f"{out_dir}/meal_planner_{lang_code}.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle(f"Meal Planner — {L['premium']}"); c.setAuthor("PlannerAtlas")

    cover_base(c,L["meal_title"][0],L["meal_title"][1],L)
    y_pos=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in L["meal_items"]: c.drawString(M+2*mm,y_pos,item); y_pos-=14
    footer(c); c.showPage()

    MEALS=L["meals"]
    for w in range(1,5):
        # Weekly meal
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['WEEKLY_MEAL']} — {L['week_x'](w)}")
        row_y=y-10*mm
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M,row_y,L["WEEK_OF_MEAL"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.line(M+22*mm,row_y+1,M+70*mm,row_y+1)
        c.setFillColor(GREEN)
        c.drawString(M+80*mm,row_y,L["CALORIE_GOAL"])
        c.line(M+120*mm,row_y+1,W-M,row_y+1)
        grid_top=y-22*mm; grid_h=grid_top-30*mm
        day_col_w=(W-2*M)/7; meal_row_h=grid_h/len(MEALS)
        day_colors=[GREEN]*5+[GOLD]*2
        for d,(day,col) in enumerate(zip(L["days"],day_colors)):
            x=M+d*day_col_w
            c.setFillColor(col); c.rect(x,grid_top,day_col_w,9*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
            c.drawCentredString(x+day_col_w/2,grid_top+2.8*mm,day)
        for mi,meal in enumerate(MEALS):
            for d in range(7):
                x=M+d*day_col_w; yy=grid_top-(mi+1)*meal_row_h
                fill=WCREAM if d>=5 else (ALTROW if mi%2==0 else MINT)
                c.setFillColor(fill); c.rect(x,yy,day_col_w,meal_row_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.4)
                c.rect(x,yy,day_col_w,meal_row_h,fill=0,stroke=1)
                if d==0:
                    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",6.5)
                    c.drawString(x+1.5*mm,yy+meal_row_h-4.5*mm,meal)
        notes_y=grid_top-len(MEALS)*meal_row_h-6*mm
        half=(W-2*M)/2
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M,notes_y,L["NOTES_GOALS"])
        c.drawString(M+half+4*mm,notes_y,L["WATER_INTAKE"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        for i in range(3):
            ly=notes_y-8*mm-i*8*mm
            if ly>30*mm:
                c.line(M,ly,M+half-4*mm,ly)
                c.line(M+half+4*mm,ly,W-M,ly)
        footer(c,L["week_x"](w)); c.showPage()

        # Grocery list
        c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
        y=hdr(c,f"{L['GROCERY']} — {L['week_x'](w)}")
        row_y=y-10*mm
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M,row_y,L["WEEK_OF_MEAL"])
        c.setStrokeColor(LGRID); c.setLineWidth(0.5)
        c.line(M+22*mm,row_y+1,M+70*mm,row_y+1)
        c.setFillColor(GREEN)
        c.drawString(M+80*mm,row_y,L["BUDGET_FIELD"])
        c.line(M+98*mm,row_y+1,W-M,row_y+1)
        cats=L["grocery_cats"]; half=(W-2*M)/2; cat_h=(y-22*mm-30*mm)/4
        for ci,cat in enumerate(cats):
            col_idx=ci//4; row_idx=ci%4
            cx=M+col_idx*half; cy=y-20*mm-(row_idx+1)*cat_h
            c.setFillColor(GREEN); c.rect(cx,cy+cat_h-8*mm,half-3*mm,8*mm,fill=1,stroke=0)
            c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
            c.drawString(cx+2*mm,cy+cat_h-5.5*mm,cat.upper())
            item_h=(cat_h-10*mm)/5
            for ii in range(5):
                iy=cy+cat_h-8*mm-(ii+1)*item_h; bg=ALTROW if ii%2==0 else CREAM
                c.setFillColor(bg); c.rect(cx,iy,half-3*mm,item_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(cx,iy,half-3*mm,item_h,fill=0,stroke=1)
                c.setStrokeColor(GREEN); c.setLineWidth(0.5)
                c.rect(cx+2*mm,iy+item_h/2-2,4*mm,4*mm,fill=0,stroke=1)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.line(cx+8*mm,iy+item_h/2,cx+half-5*mm,iy+item_h/2)
        footer(c,f"{L['GROCERY']} {L['week_x'](w)}"); c.showPage()

    # Pantry
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["PANTRY"])
    cols=L["pantry_cols"]; col_w=[(W-2*M)*0.40,(W-2*M)*0.20,(W-2*M)*0.22,(W-2*M)*0.18]
    tbl_top=y-12*mm; row_h=9*mm; x=M
    for col,cw in zip(cols,col_w):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col); x+=cw
    rows=int((tbl_top-8*mm-30*mm)/row_h)
    for ri in range(rows):
        ry=tbl_top-8*mm-(ri+1)*row_h; bg=ALTROW if ri%2==0 else CREAM; x=M
        for cw in col_w:
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(x,ry,cw,row_h,fill=0,stroke=1); x+=cw
    footer(c,L["PANTRY"]); c.showPage()

    # Recipes
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,L["RECIPES"])
    recipe_h=(y-30*mm)/2
    for ri in range(2):
        ry=y-(ri+1)*recipe_h; bg=ALTROW if ri%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,W-2*M,recipe_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,W-2*M,recipe_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,ry+recipe_h-6*mm,L["RECIPE_N"](ri+1))
        fields=[(L["SERVINGS"],""),(L["PREP_TIME"],""),(L["COOK_TIME"],"")]
        fw=(W-2*M-6*mm)/4
        for fi,(lbl,_) in enumerate(fields):
            fx=M+3*mm+fi*fw
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
            c.drawString(fx,ry+recipe_h-12*mm,lbl)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(fx+20*mm,ry+recipe_h-12*mm+1,fx+fw-3*mm,ry+recipe_h-12*mm+1)
        half=(W-2*M-6*mm)/2
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",7)
        c.drawString(M+3*mm,ry+recipe_h-20*mm,L["INGREDIENTS"])
        c.drawString(M+3*mm+half+3*mm,ry+recipe_h-20*mm,L["INSTRUCTIONS"])
        line_h=7*mm; n_lines=int((recipe_h-24*mm)/line_h)
        for li in range(n_lines):
            ly=ry+recipe_h-24*mm-li*line_h
            if ly>ry+4*mm:
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.line(M+3*mm,ly,M+3*mm+half,ly)
                c.line(M+3*mm+half+3*mm,ly,W-M-3*mm,ly)
    footer(c,L["RECIPES"]); c.showPage()

    notes_page(c,L,1); notes_page(c,L,2)
    c.save(); print(f"✅ {out}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
LANGS_CUR={}

def main():
    out_dir="scripts"
    for lang_code,L in LANGS.items():
        print(f"\n── {lang_code} ──")
        gen_weekly(lang_code,L,out_dir)
        gen_monthly(lang_code,L,out_dir)
        gen_daily(lang_code,L,out_dir)
        gen_habit(lang_code,L,out_dir)
        gen_budget(lang_code,L,out_dir)
        gen_meal(lang_code,L,out_dir)
    print("\n✅ 18 PDFs gerados.")

if __name__=="__main__": main()
