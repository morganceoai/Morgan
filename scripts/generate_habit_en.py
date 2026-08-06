"""PlannerAtlas — Habit Tracker EN (Premium) — 18 páginas"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
import calendar

GREEN=HexColor("#1B4332"); GOLD=HexColor("#C9A84C"); CREAM=HexColor("#FAFAF5")
LGRID=HexColor("#D4E8DC"); MINT=HexColor("#F0FAF4"); WCREAM=HexColor("#FFF9EE")
ALTROW=HexColor("#EEF6F1"); WHITE=HexColor("#FFFFFF"); GRAYTEXT=HexColor("#6B7280")
DARKTEXT=HexColor("#1B4332")
W,H=A4; M=18*mm
MONTHS=["January","February","March","April","May","June",
        "July","August","September","October","November","December"]
HABITS_DEFAULT=["Exercise","Meditation","Reading","Hydration (2L)","Sleep 8h",
                "No Sugar","Journaling","Gratitude","Walk 10k steps","Vitamins",
                "Cold Shower","Stretching"]

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

def page_cover(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,10*mm,H,fill=1,stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8)
    c.line(M+2*mm,H-30*mm,W-M,H-30*mm)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",11)
    c.drawString(M+2*mm,H-22*mm,"PA")
    c.setFont("Helvetica-Bold",42)
    c.drawString(M+2*mm,H*0.55,"HABIT")
    c.drawString(M+2*mm,H*0.55-48,"TRACKER")
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm,H*0.55-64,"PREMIUM COLLECTION")
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm,H*0.55-76,"UNDATED  ·  A4")
    items=["How to Use","Monthly Habit Tracker × 12","Habit Review × 2","Notes × 2"]
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in items: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

def page_how_to_use(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"HOW TO USE")
    steps=[
        ("1. Set Your Habits","Choose up to 12 habits you want to track. Write them in the rows on each monthly page. Start with habits you already do consistently, then add new ones gradually."),
        ("2. Track Daily","Each day, mark the corresponding cell: ✓ for completed, ✗ for missed, or use your own symbols. Consistency is key — even partial completion counts!"),
        ("3. Review Weekly","At the end of each week, count your completed days. Aim to improve by at least one day each week. Small progress adds up."),
        ("4. Monthly Reflection","At month-end, use the Habit Review page to analyse your patterns. Which habits thrived? Which need adjusting? Be honest and compassionate."),
        ("5. Adapt & Grow","It's OK to change a habit if it's not working. The goal is sustainable progress, not perfection. Celebrate every win, no matter how small."),
    ]
    sy=y-14*mm; box_h=(sy-30*mm)/len(steps)
    for idx,(title,text) in enumerate(steps):
        by=sy-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        # número
        c.setFillColor(GREEN); c.rect(M,by,12*mm,box_h,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",16)
        c.drawCentredString(M+6*mm,by+box_h/2-5,str(idx+1))
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8.5)
        c.drawString(M+15*mm,by+box_h-7*mm,title)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
        # wrap text simples
        words=text.split(); line=""; lines_out=[]; max_w=W-2*M-18*mm-6*mm
        for w in words:
            test=line+" "+w if line else w
            if c.stringWidth(test,"Helvetica",7.5)<max_w: line=test
            else: lines_out.append(line); line=w
        if line: lines_out.append(line)
        for li,ln in enumerate(lines_out[:3]):
            c.drawString(M+15*mm,by+box_h-14*mm-li*9,ln)
    footer(c,"How to Use"); c.showPage()

def page_monthly_tracker(c, month_name):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,f"HABIT TRACKER — {month_name.upper()}")

    label_w=42*mm; days_in_month=31
    day_col_w=(W-2*M-label_w)/days_in_month
    row_h=10*mm; header_y=y-10*mm

    # Cabeçalho "HABIT"
    c.setFillColor(GREEN); c.rect(M,header_y-8*mm,label_w,8*mm,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
    c.drawString(M+2*mm,header_y-5.5*mm,"HABIT")

    # Dias 1-31
    for d in range(days_in_month):
        x=M+label_w+d*day_col_w
        c.setFillColor(GREEN); c.rect(x,header_y-8*mm,day_col_w,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",5)
        c.drawCentredString(x+day_col_w/2,header_y-5.5*mm,str(d+1))

    # Hábitos
    for idx,habit in enumerate(HABITS_DEFAULT):
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

    # Linhas em branco extra
    blank_start=header_y-8*mm-len(HABITS_DEFAULT)*row_h; blank_count=0
    while blank_start-(blank_count+1)*row_h>22*mm: blank_count+=1
    for idx in range(blank_count):
        ry=blank_start-(idx+1)*row_h; bg=ALTROW if (len(HABITS_DEFAULT)+idx)%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,label_w,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,label_w,row_h,fill=0,stroke=1)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3)
        c.line(M+2*mm,ry+row_h/2,M+label_w-2*mm,ry+row_h/2)
        for d in range(days_in_month):
            x=M+label_w+d*day_col_w
            c.setFillColor(bg); c.rect(x,ry,day_col_w,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.rect(x,ry,day_col_w,row_h,fill=0,stroke=1)

    footer(c,month_name); c.showPage()

def page_habit_review(c, num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,f"HABIT REVIEW — Q{num*2-1} / Q{num*2}")
    sections=[
        ("HABITS THAT THRIVED","Which habits did you complete most consistently?"),
        ("HABITS TO IMPROVE","Which habits need more focus next quarter?"),
        ("BIGGEST WIN","What are you most proud of?"),
        ("KEY LESSON","What did you learn about yourself?"),
        ("NEXT QUARTER FOCUS","What will you prioritise?"),
        ("NOTES","Any other reflections"),
    ]
    box_h=(y-30*mm)/len(sections)
    for idx,(title,prompt) in enumerate(sections):
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
    footer(c,f"Habit Review Q{num*2-1}/Q{num*2}"); c.showPage()

def page_notes(c,num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"NOTES")
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,y-10*mm,"Title / Topic:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm,y-10*mm+1,W-M,y-10*mm+1)
    ls=y-18*mm; sp=10*mm; nl=int((ls-22*mm)/sp)
    for i in range(nl):
        ly=ls-i*sp; bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ly-sp+1,W-2*M,sp-1,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.line(M,ly,W-M,ly)
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    c.line(M,ls-nl*sp,W-M,ls-nl*sp)
    footer(c,f"Notes {num}"); c.showPage()

def generate():
    out="scripts/habit_tracker_EN.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle("Habit Tracker — Premium Collection"); c.setAuthor("PlannerAtlas")
    page_cover(c); page_how_to_use(c)
    for m in MONTHS: page_monthly_tracker(c,m)
    page_habit_review(c,1); page_habit_review(c,2)
    page_notes(c,1); page_notes(c,2)
    c.save(); print(f"✅ {out}")

if __name__=="__main__": generate()
