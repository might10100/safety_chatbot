"""
pdf_utils.py — 일일 안전일지 PDF (업로드 양식 그대로)
"""
import os, platform, subprocess
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _reg():
    for path, ir, ib in [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0, 3),
        ("/Library/Fonts/NanumGothic.ttf", None, None),
        ("/Library/Fonts/AppleGothic.ttf", None, None),
        ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", None, None),
        ("C:/Windows/Fonts/malgun.ttf", None, None),
    ]:
        if not os.path.exists(path): continue
        try:
            if path.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont("F",  path, subfontIndex=ir))
                pdfmetrics.registerFont(TTFont("FB", path, subfontIndex=ib))
            else:
                pdfmetrics.registerFont(TTFont("F",  path))
                bp = path.replace(".ttf","Bold.ttf")
                pdfmetrics.registerFont(TTFont("FB", bp if os.path.exists(bp) else path))
            return "F","FB"
        except: continue
    return "Helvetica","Helvetica-Bold"

FN, FNB = _reg()
W = A4[0] - 30*mm

def _p(text, size=9, bold=False, align="LEFT", color=colors.black, leading=None):
    fn = FNB if bold else FN
    al = {"LEFT":0,"CENTER":1,"RIGHT":2}.get(align,0)
    return Paragraph(str(text or ""), ParagraphStyle("s",
        fontName=fn, fontSize=size, leading=leading or size*1.5,
        alignment=al, textColor=color, wordWrap='CJK'))

def _ts(*extra):
    base = [
        ("FONTNAME",    (0,0),(-1,-1), FN),
        ("FONTSIZE",    (0,0),(-1,-1), 9),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("GRID",        (0,0),(-1,-1), 0.5, colors.black),
        ("TOPPADDING",  (0,0),(-1,-1), 3),
        ("BOTTOMPADDING",(0,0),(-1,-1), 3),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
    ]
    return TableStyle(base + list(extra))

def _open(path):
    try:
        if platform.system()=="Darwin":   subprocess.run(["open",path])
        elif platform.system()=="Windows": os.startfile(path)
        else:                              subprocess.run(["xdg-open",path])
    except: pass

def _out(fn, save_dir):
    if save_dir and os.path.isdir(save_dir): return os.path.join(save_dir, fn)
    d = os.path.join(os.path.expanduser("~"),"Desktop")
    return os.path.join(d if os.path.isdir(d) else os.path.expanduser("~"), fn)

def _doc(path):
    return SimpleDocTemplate(path, pagesize=A4,
        topMargin=12*mm, bottomMargin=12*mm, leftMargin=15*mm, rightMargin=15*mm)


# ══════════════════════════════════════════════════════════════
# 일일 안전일지 PDF — 업로드 양식과 동일한 선 형식
# ══════════════════════════════════════════════════════════════
def save_daily_log_pdf(daily: dict, report_text: str,
                        project: str = "", save_dir: str = "") -> str:
    date_c  = daily.get("date_c", datetime.today().strftime("%Y%m%d"))
    manager = daily.get("manager","")
    path    = _out(f"{date_c}_일일안전일지_{manager}.pdf", save_dir)
    doc     = _doc(path)
    story   = []

    HDR  = colors.HexColor("#1a1a2e")
    GRAY = colors.HexColor("#f0f0f0")

    # ── 제목 ──
    title_data = [[_p("일  일  안  전  일  지", 15, bold=True, align="CENTER")]]
    t = Table(title_data, colWidths=[W])
    t.setStyle(_ts(("BOX",(0,0),(-1,-1),1.5,HDR),
                   ("BACKGROUND",(0,0),(-1,-1),HDR),
                   ("TEXTCOLOR",(0,0),(-1,-1),colors.white),
                   ("FONTNAME",(0,0),(-1,-1),FNB),
                   ("TOPPADDING",(0,0),(-1,-1),7),
                   ("BOTTOMPADDING",(0,0),(-1,-1),7)))
    story.append(t)

    # ── 작성일자 / 관리자 ──
    d = daily.get("date","")
    dp = d.split("-") if "-" in d else ["","",""]
    date_str = f"{dp[0]}년  {dp[1]}월  {dp[2]}일" if len(dp)==3 else d
    info_data = [[
        _p("작성일자", 9, bold=True, align="CENTER"),
        _p(date_str, 9, align="CENTER"),
        _p("관리자", 9, bold=True, align="CENTER"),
        _p(manager, 9, align="CENTER"),
    ]]
    t2 = Table(info_data, colWidths=[W*0.15, W*0.45, W*0.15, W*0.25], rowHeights=[8*mm])
    t2.setStyle(_ts(("BACKGROUND",(0,0),(0,0),GRAY),
                    ("BACKGROUND",(2,0),(2,0),GRAY),
                    ("FONTNAME",(0,0),(0,0),FNB),
                    ("FONTNAME",(2,0),(2,0),FNB)))
    story.append(t2)
    story.append(Spacer(1,2*mm))

    # ── 1. 당일 작업 현황 ──
    sec1 = [[_p("1. 당일 작업 현황", 10, bold=True)]]
    t3 = Table(sec1, colWidths=[W])
    t3.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY),
                    ("FONTNAME",(0,0),(-1,-1),FNB),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                    ("BOTTOMPADDING",(0,0),(-1,-1),4)))
    story.append(t3)

    w = daily.get("weather",{})
    ws = (f"최고풍속 {w.get('wind_max','-')} ({w.get('peak_time','-')} 도달) / "
          f"평균기온 {w.get('temp_avg','-')}" if w else "-")

    rows1 = [
        [_p("투입 인원", 9, bold=True, align="CENTER"),
         _p(daily.get("workers",""), 9),
         _p("장비 현황", 9, bold=True, align="CENTER"),
         _p(daily.get("equipment",""), 9)],
        [_p("주요 작업 내용", 9, bold=True, align="CENTER"),
         _p(daily.get("work_process",""), 9, leading=13),
         "", ""],
        [_p("작업 위치", 9, bold=True, align="CENTER"),
         _p(daily.get("location",""), 9),
         _p("공종 시간", 9, bold=True, align="CENTER"),
         _p(daily.get("work_time",""), 9, align="CENTER")],
        [_p("현장 특이사항", 9, bold=True, align="CENTER"),
         _p(ws, 9), "", ""],
    ]
    cw1 = [W*0.14, W*0.36, W*0.14, W*0.36]
    t4 = Table(rows1, colWidths=cw1, rowHeights=[8*mm, 12*mm, 8*mm, 10*mm])
    t4.setStyle(_ts(
        ("BACKGROUND",(0,0),(0,-1),GRAY),
        ("BACKGROUND",(2,0),(2,-1),GRAY),
        ("FONTNAME",(0,0),(0,-1),FNB),
        ("FONTNAME",(2,0),(2,-1),FNB),
        ("SPAN",(1,1),(3,1)),
        ("SPAN",(1,3),(3,3)),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ))
    story.append(t4)
    story.append(Spacer(1,2*mm))

    # ── 2. 위험 요인 및 안전 조치 ──
    sec2 = [[_p("2. 위험 요인 및 안전 조치 (법규 기반)", 10, bold=True)]]
    t5 = Table(sec2, colWidths=[W])
    t5.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY),
                    ("FONTNAME",(0,0),(-1,-1),FNB),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                    ("BOTTOMPADDING",(0,0),(-1,-1),4)))
    story.append(t5)

    # 위험요인 파싱
    risk_sets = []
    lines = report_text.split("\n")
    risk=law=action=""
    for line in lines:
        s = line.strip()
        if s.startswith("[위험요인]"):
            if risk: risk_sets.append((risk,law,action))
            risk=s.replace("[위험요인]","").strip(); law=""; action=""
        elif s.startswith("[법적 근거]"): law=s.replace("[법적 근거]","").strip()
        elif s.startswith("[안전 조치]"): action=s.replace("[안전 조치]","").strip()
    if risk: risk_sets.append((risk,law,action))

    if not risk_sets:
        risk_sets = [("(위험 요인 정보 없음)","","")]

    for risk, law_txt, action in risk_sets:
        rows2 = [
            [_p("위험 요인", 9, bold=True, align="CENTER"),
             _p(risk, 9)],
            [_p("법적 근거", 9, bold=True, align="CENTER"),
             _p(law_txt, 9)],
            [_p("안전 조치 사항", 9, bold=True, align="CENTER"),
             _p(action, 9)],
        ]
        t6 = Table(rows2, colWidths=[W*0.18, W*0.82], rowHeights=[9*mm,8*mm,9*mm])
        t6.setStyle(_ts(
            ("BACKGROUND",(0,0),(0,-1),GRAY),
            ("FONTNAME",(0,0),(0,-1),FNB),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ))
        story.append(t6)
    story.append(Spacer(1,2*mm))

    # ── 3. 근로자 TBM 메시지 ──
    sec3 = [[_p("3. 근로자 TBM 메시지", 10, bold=True)]]
    t7 = Table(sec3, colWidths=[W])
    t7.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY),
                    ("FONTNAME",(0,0),(-1,-1),FNB),
                    ("TOPPADDING",(0,0),(-1,-1),4),
                    ("BOTTOMPADDING",(0,0),(-1,-1),4)))
    story.append(t7)

    tbm = ""
    in_tbm = False
    for line in lines:
        if "TBM 메시지" in line: in_tbm=True; continue
        if in_tbm and line.strip() and not line.strip().startswith("["):
            tbm += line.strip()+" "
    tbm = tbm.strip() or "(TBM 메시지 없음)"

    tbm_data = [[_p(tbm, 9)]]
    t8 = Table(tbm_data, colWidths=[W], rowHeights=[28*mm])
    t8.setStyle(_ts(("VALIGN",(0,0),(-1,-1),"TOP")))
    story.append(t8)
    story.append(Spacer(1,4*mm))

    # ── 확인자 ──
    sig_data = [[_p(f"확인자 (관리자):  {manager}                    (인)", 9, align="CENTER")]]
    t9 = Table(sig_data, colWidths=[W], rowHeights=[8*mm])
    t9.setStyle(_ts(("BOX",(0,0),(-1,-1),0.5,colors.black)))
    story.append(t9)

    doc.build(story)
    _open(path)
    return path


# ══════════════════════════════════════════════════════════════
# 체크리스트 PDF
# ══════════════════════════════════════════════════════════════
def save_checklist_pdf(content: str, date: str,
                        project: str = "", save_dir: str = "") -> str:
    path = _out(f"{date}_안전점검체크리스트.pdf", save_dir)
    doc  = _doc(path)
    story = []
    HDR  = colors.HexColor("#1a1a2e")
    GRAY = colors.HexColor("#f0f0f0")

    title_data = [[_p("현장 안전 점검 체크리스트", 14, bold=True, align="CENTER")]]
    t = Table(title_data, colWidths=[W])
    t.setStyle(_ts(("BOX",(0,0),(-1,-1),1.5,HDR),
                   ("BACKGROUND",(0,0),(-1,-1),HDR),
                   ("TEXTCOLOR",(0,0),(-1,-1),colors.white),
                   ("FONTNAME",(0,0),(-1,-1),FNB),
                   ("TOPPADDING",(0,0),(-1,-1),6),
                   ("BOTTOMPADDING",(0,0),(-1,-1),6)))
    story.append(t)

    if project or date:
        info = [[_p(f"현장명: {project}  |  점검일: {date}", 8, align="CENTER")]]
        ti = Table(info, colWidths=[W], rowHeights=[6*mm])
        ti.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY)))
        story.append(ti)

    story.append(Spacer(1,2*mm))

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            story.append(Spacer(1,1.5*mm))
        elif s.startswith(("I.","II.","Ⅰ.","Ⅱ.")):
            story.append(Spacer(1,3*mm))
            data = [[_p(s, 10, bold=True)]]
            tb = Table(data, colWidths=[W])
            tb.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY),
                            ("FONTNAME",(0,0),(-1,-1),FNB),
                            ("TOPPADDING",(0,0),(-1,-1),3),
                            ("BOTTOMPADDING",(0,0),(-1,-1),3)))
            story.append(tb)
        elif s[:2] in ("1.","2.","3.","4.","5.","6.","7.","8.","9.") and len(s)<25:
            story.append(Spacer(1,1*mm))
            story.append(_p(s, 9, bold=True))
        elif "[주의]" in s or "[!]" in s:
            data = [[_p(s, 9, color=colors.red)]]
            tb = Table(data, colWidths=[W], rowHeights=[7*mm])
            tb.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#fff0f0")),
                            ("BOX",(0,0),(-1,-1),0.5,colors.red)))
            story.append(tb)
        elif s.startswith("□"):
            data = [[_p(s, 9)]]
            tb = Table(data, colWidths=[W], rowHeights=[7*mm])
            tb.setStyle(_ts(("BOX",(0,0),(-1,-1),0.3,colors.HexColor("#cccccc"))))
            story.append(tb)
        elif any(x in s for x in ["안전관리자","현장소장","작업반장","점검 확인"]):
            story.append(Spacer(1,2*mm))
            data = [[_p(s, 9, bold=True if "점검 확인" in s else False, align="CENTER")]]
            tb = Table(data, colWidths=[W], rowHeights=[8*mm])
            tb.setStyle(_ts(("BOX",(0,0),(-1,-1),0.5,colors.black),
                            ("BACKGROUND",(0,0),(-1,-1),GRAY)))
            story.append(tb)
        else:
            story.append(_p(s, 9))

    doc.build(story)
    _open(path)
    return path


# ══════════════════════════════════════════════════════════════
# 사고 보고서 PDF (accident_form.py의 save_accident_form_pdf 사용)
# ══════════════════════════════════════════════════════════════
def save_accident_report_pdf(content: str, date: str,
                              project: str = "", save_dir: str = "") -> str:
    path = _out(f"{date}_사고보고서.pdf", save_dir)
    doc  = _doc(path)
    story = []
    HDR  = colors.HexColor("#1a1a2e")
    GRAY = colors.HexColor("#f0f0f0")

    if "[중대재해 주의]" in content:
        story.append(_p("⚠ 중대재해 주의", 13, bold=True, color=colors.red))
        story.append(Spacer(1,2*mm))

    title_data = [[_p("사  고  현  장  보  고  서", 14, bold=True, align="CENTER")]]
    t = Table(title_data, colWidths=[W])
    t.setStyle(_ts(("BOX",(0,0),(-1,-1),1.5,HDR),
                   ("BACKGROUND",(0,0),(-1,-1),HDR),
                   ("TEXTCOLOR",(0,0),(-1,-1),colors.white),
                   ("FONTNAME",(0,0),(-1,-1),FNB),
                   ("TOPPADDING",(0,0),(-1,-1),6),
                   ("BOTTOMPADDING",(0,0),(-1,-1),6)))
    story.append(t)
    story.append(Spacer(1,2*mm))

    for line in content.split("\n"):
        s = line.strip()
        if not s:
            story.append(Spacer(1,1.5*mm))
        elif s.startswith("[") and s.endswith("]") and "수정됨" not in s and "중대재해" not in s:
            story.append(Spacer(1,3*mm))
            data = [[_p(s, 10, bold=True)]]
            tb = Table(data, colWidths=[W])
            tb.setStyle(_ts(("BACKGROUND",(0,0),(-1,-1),GRAY),
                            ("FONTNAME",(0,0),(-1,-1),FNB),
                            ("TOPPADDING",(0,0),(-1,-1),3),
                            ("BOTTOMPADDING",(0,0),(-1,-1),3)))
            story.append(tb)
        elif s.startswith("-"):
            data = [[_p(s, 9)]]
            tb = Table(data, colWidths=[W], rowHeights=[7*mm])
            tb.setStyle(_ts(("BOX",(0,0),(-1,-1),0.3,colors.HexColor("#cccccc"))))
            story.append(tb)
        elif "담당(서명)" in s or "과장(서명)" in s:
            story.append(Spacer(1,4*mm))
            story.append(_p(s, 9, bold=True, align="CENTER"))
        else:
            story.append(_p(s, 9))

    doc.build(story)
    _open(path)
    return path