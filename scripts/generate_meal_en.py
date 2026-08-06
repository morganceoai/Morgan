"""PlannerAtlas — Meal Planner EN (Premium) — 14 páginas"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

GREEN=HexColor("#1B4332"); GOLD=HexColor("#C9A84C"); CREAM=HexColor("#FAFAF5")
LGRID=HexColor("#D4E8DC"); MINT=HexColor("#F0FAF4"); WCREAM=HexColor("#FFF9EE")
ALTROW=HexColor("#EEF6F1"); WHITE=HexColor("#FFFFFF"); GRAYTEXT=HexColor("#6B7280")
DARKTEXT=HexColor("#1B4332")
W,H=A4; M=18*mm
DAYS=["MON","TUE","WED","THU","FRI","SAT","SUN"]
MEALS=["Breakfast","Lunch","Dinner","Snacks"]

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
    c.drawString(M+2*mm,H*0.55,"MEAL")
    c.drawString(M+2*mm,H*0.55-48,"PLANNER")
    c.setFillColor(GOLD); c.setFont("Helvetica",8)
    c.drawString(M+2*mm,H*0.55-64,"PREMIUM COLLECTION")
    c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7.5)
    c.drawString(M+2*mm,H*0.55-76,"UNDATED  ·  A4")
    items=["Weekly Meal Planner × 4","Grocery List × 4","Pantry Inventory","Favourite Recipes","Notes × 2"]
    y=H*0.35; c.setFillColor(GREEN); c.setFont("Helvetica",8.5)
    for item in items: c.drawString(M+2*mm,y,item); y-=14
    footer(c); c.showPage()

def page_weekly_meal(c, week_num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,f"WEEKLY MEAL PLANNER — WEEK {week_num}")

    # Linha week of + calories goal
    row_y=y-10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
    c.drawString(M,row_y,"Week of:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+22*mm,row_y+1,M+70*mm,row_y+1)
    c.setFillColor(GREEN)
    c.drawString(M+80*mm,row_y,"Daily Calorie Goal:")
    c.line(M+120*mm,row_y+1,W-M,row_y+1)

    grid_top=y-22*mm
    grid_h=grid_top-30*mm
    day_col_w=(W-2*M)/7
    meal_row_h=grid_h/len(MEALS)

    # Cabeçalho dias — verde/dourado
    day_colors=[GREEN]*5+[GOLD]*2
    for d,(day,col) in enumerate(zip(DAYS,day_colors)):
        x=M+d*day_col_w
        c.setFillColor(col); c.rect(x,grid_top,day_col_w,9*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",8)
        c.drawCentredString(x+day_col_w/2,grid_top+2.8*mm,day)

    # Linhas de refeições
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

    # Notas + Water intake
    notes_y=grid_top-len(MEALS)*meal_row_h-6*mm
    half=(W-2*M)/2
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
    c.drawString(M,notes_y,"Notes & Goals")
    c.drawString(M+half+4*mm,notes_y,"Water Intake (glasses/day)")
    c.setStrokeColor(LGRID); c.setLineWidth(0.4)
    for i in range(3):
        ly=notes_y-8*mm-i*8*mm
        if ly>30*mm:
            c.line(M,ly,M+half-4*mm,ly)
            c.line(M+half+4*mm,ly,W-M,ly)
    footer(c,f"Week {week_num}"); c.showPage()

def page_grocery(c, week_num):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,f"GROCERY LIST — WEEK {week_num}")

    # Cabeçalho
    row_y=y-10*mm
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
    c.drawString(M,row_y,"Week of:")
    c.setStrokeColor(LGRID); c.setLineWidth(0.5)
    c.line(M+22*mm,row_y+1,M+70*mm,row_y+1)
    c.setFillColor(GREEN)
    c.drawString(M+80*mm,row_y,"Budget:")
    c.line(M+98*mm,row_y+1,W-M,row_y+1)

    categories=["Produce","Meat & Fish","Dairy & Eggs","Bakery","Frozen","Pantry","Beverages","Other"]
    half=(W-2*M)/2; cat_h=(y-22*mm-30*mm)/4

    for ci,cat in enumerate(categories):
        col_idx=ci//4; row_idx=ci%4
        cx=M+col_idx*half; cy=y-20*mm-(row_idx+1)*cat_h

        c.setFillColor(GREEN); c.rect(cx,cy+cat_h-8*mm,half-3*mm,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7.5)
        c.drawString(cx+2*mm,cy+cat_h-5.5*mm,cat.upper())

        # linhas de itens
        item_h=(cat_h-10*mm)/5
        for ii in range(5):
            iy=cy+cat_h-8*mm-(ii+1)*item_h
            bg=ALTROW if ii%2==0 else CREAM
            c.setFillColor(bg); c.rect(cx,iy,half-3*mm,item_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3); c.rect(cx,iy,half-3*mm,item_h,fill=0,stroke=1)
            # checkbox
            c.setStrokeColor(GREEN); c.setLineWidth(0.5)
            c.rect(cx+2*mm,iy+item_h/2-2,4*mm,4*mm,fill=0,stroke=1)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(cx+8*mm,iy+item_h/2,cx+half-5*mm,iy+item_h/2)

    footer(c,f"Grocery List Week {week_num}"); c.showPage()

def page_pantry(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"PANTRY INVENTORY")
    cols=["ITEM","QUANTITY","EXPIRY DATE","RESTOCK?"]
    col_w=[(W-2*M)*0.40,(W-2*M)*0.20,(W-2*M)*0.22,(W-2*M)*0.18]
    tbl_top=y-12*mm; row_h=9*mm
    x=M
    for col,cw in zip(cols,col_w):
        c.setFillColor(GREEN); c.rect(x,tbl_top-8*mm,cw,8*mm,fill=1,stroke=0)
        c.setFillColor(WHITE); c.setFont("Helvetica-Bold",7)
        c.drawCentredString(x+cw/2,tbl_top-5.5*mm,col); x+=cw
    rows=int((tbl_top-8*mm-30*mm)/row_h)
    for ri in range(rows):
        ry=tbl_top-8*mm-(ri+1)*row_h; bg=ALTROW if ri%2==0 else CREAM; x=M
        for cw in col_w:
            c.setFillColor(bg); c.rect(x,ry,cw,row_h,fill=1,stroke=0)
            c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(x,ry,cw,row_h,fill=0,stroke=1)
            x+=cw
    footer(c,"Pantry Inventory"); c.showPage()

def page_recipes(c):
    c.setFillColor(CREAM); c.rect(0,0,W,H,fill=1,stroke=0)
    y=hdr(c,"FAVOURITE RECIPES")
    sections=[("RECIPE NAME",""),("INGREDIENTS",""),("INSTRUCTIONS",""),
              ("PREP TIME",""),("NOTES","")]
    # 2 recipes per page, split vertically
    recipe_h=(y-30*mm)/2
    for ri in range(2):
        ry=y-(ri+1)*recipe_h; bg=ALTROW if ri%2==0 else CREAM
        c.setFillColor(bg); c.rect(M,ry,W-2*M,recipe_h,fill=1,stroke=0)
        c.setStrokeColor(LGRID); c.setLineWidth(0.4); c.rect(M,ry,W-2*M,recipe_h,fill=0,stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",8)
        c.drawString(M+3*mm,ry+recipe_h-6*mm,f"Recipe {ri+1}")
        # campos
        fields=[("Name:",""),("Servings:",""),("Prep Time:",""),("Cook Time:","")]
        fw=(W-2*M-6*mm)/len(fields)
        for fi,(lbl,_) in enumerate(fields):
            fx=M+3*mm+fi*fw
            c.setFillColor(GRAYTEXT); c.setFont("Helvetica",7)
            c.drawString(fx,ry+recipe_h-12*mm,lbl)
            c.setStrokeColor(LGRID); c.setLineWidth(0.3)
            c.line(fx+20*mm,ry+recipe_h-12*mm+1,fx+fw-3*mm,ry+recipe_h-12*mm+1)
        # Ingredients + Instructions
        half=(W-2*M-6*mm)/2
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold",7)
        c.drawString(M+3*mm,ry+recipe_h-20*mm,"Ingredients")
        c.drawString(M+3*mm+half+3*mm,ry+recipe_h-20*mm,"Instructions")
        line_h=7*mm; n_lines=int((recipe_h-24*mm)/line_h)
        for li in range(n_lines):
            ly=ry+recipe_h-24*mm-li*line_h
            if ly>ry+4*mm:
                c.setStrokeColor(LGRID); c.setLineWidth(0.3)
                c.line(M+3*mm,ly,M+3*mm+half,ly)
                c.line(M+3*mm+half+3*mm,ly,W-M-3*mm,ly)
    footer(c,"Favourite Recipes"); c.showPage()

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
    out="scripts/meal_planner_EN.pdf"
    c=canvas.Canvas(out,pagesize=A4)
    c.setTitle("Meal Planner — Premium Collection"); c.setAuthor("PlannerAtlas")
    page_cover(c)
    for w in range(1,5): page_weekly_meal(c,w); page_grocery(c,w)
    page_pantry(c); page_recipes(c)
    page_notes(c,1); page_notes(c,2)
    c.save(); print(f"✅ {out}")

if __name__=="__main__": generate()
