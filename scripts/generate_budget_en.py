"""PlannerAtlas — Budget Planner EN (Premium) — 18 páginas"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

GREEN=HexColor("#1B4332"); GOLD=HexColor("#C9A84C"); CREAM=HexColor("#FAFAF5")
LGRID=HexColor("#D4E8DC"); MINT=HexColor("#F0FAF4"); WCREAM=HexColor("#FFF9EE")
ALTROW=HexColor("#EEF6F1"); WHITE=HexColor("#FFFFFF"); GRAYTEXT=HexColor("#6B7280")
DARKTEXT=HexColor("#1B4332")
W,H=A4; M=18*mm
MONTHS=["January","February","March","April","May","June",
        "July","August","September","October","November","December"]
EXPENSE_CATS=["Housing / Rent","Utilities","Groceries","Transport","Health",
              "Insurance","Subscriptions","Entertainment","Clothing","Dining Out",
              "Personal Care","Education","Gifts","Savings","Other"]

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

def mini_header(c,title,x,y,w,h):
    c.setFillColor(GREEN); c.rect(x,y-h,w,h,fill=1,stroke=0)
    c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
    c.drawString(x+2*mm,y-h+2.5*mm,title)

def page_cover(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    c.setFillColor(GREEN); c.rect(0,0,10*mm,H,fill=1,stroke=0)
    c.setStrokeColor(GOLD); c.setLineWidth(0.8)
    c.line(M+2*mm,H-30*mm,W-M,H-30*mm)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",11)
    c.drawString(M+2*mm,H-22*mm,"PA")
    c.setFont("Helvetica-Bold",42)
    c.drawString(M+2*mm,H*0.55,"BUDGET")
    c.drawString(M+2*mm,H*0.55-48,"PLANNER")
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm,H*0.55-64,"PREMIUM COLLECTION")
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm,H*0.55-76,"UNDATED  ·  A4")
    items=["Annual Overview","Monthly Budget × 12","Debt Tracker","Savings Goals","Notes × 2"]
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in items: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

def page_annual(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"ANNUAL FINANCIAL OVERVIEW")
    year_y=y-10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,year_y,"Year:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+16*mm,year_y+1,M+55*mm,year_y+1)

    # Tabela anual: meses × (income, expenses, savings, balance)
    cols=["MONTH","INCOME","EXPENSES","SAVINGS","BALANCE"]
    col_w=[(W-2*M)*0.22,(W-2*M)*0.20,(W-2*M)*0.20,(W-2*M)*0.19,(W-2*M)*0.19]
    tbl_top=y-20*mm; row_h=10*mm
    # cabeçalho tabela
    x=M
    for i,(col,cw) in enumerate(zip(cols,col_w)):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col)
        x+=cw
    for mi,month in enumerate(MONTHS):
        ry=tbl_top-8*mm-(mi+1)*row_h; bg=ALTROW if mi%2==0 else CREAM
        x=M
        for i,(col,cw) in enumerate(zip(cols,col_w)):
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4)
            c.rect(x,ry,cw,row_h,fill=0,stroke=1)
            if i==0:
                c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
                c.drawString(x+2*mm,ry+row_h/2-2,month)
            x+=cw
    # Total row
    tot_y=tbl_top-8*mm-12*row_h; x=M
    for i,(col,cw) in enumerate(zip(cols,col_w)):
        c.setFillColor(MINT); c.rect(x,tot_y-row_h,cw,row_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.5); c.rect(x,tot_y-row_h,cw,row_h,fill=0,stroke=1)
        if i==0:
            c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
            c.drawString(x+2*mm,tot_y-row_h+row_h/2-2,"TOTAL")
        x+=cw
    footer(c,"Annual Overview"); c.showPage()

def page_monthly_budget(c,month_name):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,f"BUDGET — {month_name.upper()}")

    # Linha month/year
    my=y-10*mm; c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
    c.drawString(M,my,"Month / Year:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+32*mm,my+1,W-M,my+1)

    half=(W-2*M)/2; col_right=M+half+4*mm

    # ── LEFT: INCOME ──
    inc_y=y-20*mm
    mini_header(c,"INCOME",M,inc_y,half-4*mm,8*mm)
    inc_items=["Salary / Wages","Freelance","Investments","Side Income","Other Income"]
    ir_h=8*mm
    for i,item in enumerate(inc_items):
        ry=inc_y-8*mm-(i+1)*ir_h; bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,half-4*mm,ir_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(M,ry,half-4*mm,ir_h,fill=0,stroke=1)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",7.5)
        c.drawString(M+2*mm,ry+ir_h/2-2,item)
        c.setStrokeColor(LGRID); c.line(M+half-4*mm-18*mm,ry+ir_h/2,M+half-4*mm-2*mm,ry+ir_h/2)
    # Total income
    ti_y=inc_y-8*mm-(len(inc_items)+1)*ir_h
    c.setFillColor(MINT); c.rect(M,ti_y,half-4*mm,ir_h,fill=1,stroke=0)
    c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ti_y,half-4*mm,ir_h,fill=0,stroke=1)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
    c.drawString(M+2*mm,ti_y+ir_h/2-2,"TOTAL INCOME")
    c.setStrokeColor(LGRID); c.line(M+half-4*mm-18*mm,ti_y+ir_h/2,M+half-4*mm-2*mm,ti_y+ir_h/2)

    # ── RIGHT: SUMMARY BOX ──
    sum_y=y-20*mm
    mini_header(c,"MONTHLY SUMMARY",col_right,sum_y,half-4*mm,8*mm)
    sum_items=[("Total Income",""),("Total Expenses",""),("Savings",""),("Balance","")]
    sr_h=10*mm
    for i,(lbl,_) in enumerate(sum_items):
        ry=sum_y-8*mm-(i+1)*sr_h; bg=ALTROW if i%2==0 else CREAM
        c.setFillColor(bg); c.rect(col_right,ry,half-4*mm,sr_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(col_right,ry,half-4*mm,sr_h,fill=0,stroke=1)
        c.setFillColor(DARKTEXT); c.setFont("Helvetica",8)
        c.drawString(col_right+2*mm,ry+sr_h/2-2,lbl)
        c.setStrokeColor(LGRID); c.line(col_right+half-4*mm-22*mm,ry+sr_h/2,col_right+half-4*mm-2*mm,ry+sr_h/2)

    # ── EXPENSES table ──
    exp_y=ti_y-6*mm
    exp_table_h=exp_y-30*mm
    mini_header(c,"EXPENSES",M,exp_y,W-2*M,8*mm)
    # 2 colunas de categorias
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

    # blank rows para o utilizador acrescentar despesas
    last_row_bottom = exp_y-8*mm-half_n*er_h
    blank_count=0
    while last_row_bottom-(blank_count+1)*er_h > 30*mm: blank_count+=1
    for bi in range(blank_count):
        for col_idx in range(2):
            cw=(W-2*M)/2; cx=M+col_idx*cw
            row_idx=half_n+bi
            ry=exp_y-8*mm-(row_idx+1)*er_h; bg=ALTROW if (len(EXPENSE_CATS)+bi*2+col_idx)%2==0 else CREAM
            if ry > 30*mm:
                c.setFillColor(bg); c.rect(cx,ry,cw,er_h,fill=1,stroke=0)
                c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(cx,ry,cw,er_h,fill=0,stroke=1)
                c.setStrokeColor(LGRID); c.line(cx+cw-18*mm,ry+er_h/2,cx+cw-2*mm,ry+er_h/2)

    footer(c,month_name); c.showPage()

def page_debt(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"DEBT TRACKER")
    cols=["DEBT / LOAN","TOTAL AMOUNT","INTEREST RATE","MIN. PAYMENT","PAID SO FAR","REMAINING"]
    col_w=[(W-2*M)*0.25,(W-2*M)*0.15,(W-2*M)*0.14,(W-2*M)*0.14,(W-2*M)*0.15,(W-2*M)*0.17]
    tbl_top=y-12*mm; row_h=11*mm
    x=M
    for col,cw in zip(cols,col_w):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",6.5)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col); x+=cw
    rows=int((tbl_top-8*mm-30*mm)/row_h)
    for ri in range(rows):
        ry=tbl_top-8*mm-(ri+1)*row_h; bg=ALTROW if ri%2==0 else CREAM
        x=M
        for cw in col_w:
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(x,ry,cw,row_h,fill=0,stroke=1)
            x+=cw
    # Notes
    ny=tbl_top-8*mm-(rows+1)*row_h-5*mm
    if ny>30*mm:
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",9)
        c.drawString(M,ny,"Notes")
        c.setStrokeColor(LGRID); c.setLineWidth(0.4)
        i=0
        while ny-10*mm-i*10*mm>30*mm:
            c.line(M,ny-10*mm-i*10*mm,W-M,ny-10*mm-i*10*mm); i+=1
    footer(c,"Debt Tracker"); c.showPage()

def page_savings(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"SAVINGS GOALS")
    goals=[f"Goal {i+1}" for i in range(6)]
    box_h=(y-30*mm)/len(goals)
    for idx,goal in enumerate(goals):
        by=y-(idx+1)*box_h; bg=ALTROW if idx%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,by,W-2*M,box_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,by,W-2*M,box_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,by+box_h-6*mm,goal)
        # campos: Goal, Target, Deadline, Saved, Remaining
        fields=[("Goal:",""),("Target Amount:","€"),("Deadline:",""),("Saved:","€"),("Remaining:","€")]
        fw=(W-2*M-6*mm)/len(fields)
        for fi,(lbl,unit) in enumerate(fields):
            fx=M+3*mm+fi*fw
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
            c.drawString(fx,by+box_h-12*mm,lbl)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(fx,by+box_h-19*mm,fx+fw-3*mm,by+box_h-19*mm)
        # barra de progresso
        bar_y=by+4*mm; bar_h_px=5*mm; bar_w=W-2*M-6*mm
        c.setFillColor(LGRID); c.rect(M+3*mm,bar_y,bar_w,bar_h_px,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(M+3*mm,bar_y,bar_w,bar_h_px,fill=0,stroke=1)
        c.setFillColor(GRAYTEXT); c.setFont("Helvetica",6)
        c.drawString(M+3*mm,bar_y-4*mm,"0%")
        c.drawRightString(M+3*mm+bar_w,bar_y-4*mm,"100%")
    footer(c,"Savings Goals"); c.showPage()

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
    out="scripts/budget_planner_EN.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle("Budget Planner — Premium Collection"); c.setAuthor("PlannerAtlas")
    page_cover(c); page_annual(c)
    for m in MONTHS: page_monthly_budget(c,m)
    page_debt(c); page_savings(c)
    page_notes(c,1); page_notes(c,2)
    c.save(); print(f"✅ {out}")

if __name__=="__main__": generate()
