"""
accident_form.py
사고현장 보고서 — 공식 양식 PDF 생성
"""
import os, platform, subprocess
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle


# ── 폰트 등록 ──────────────────────────────────────────────
def _reg():
    candidates = [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0, 3),
        ("/Library/Fonts/NanumGothic.ttf", None, None),
        ("/Library/Fonts/AppleGothic.ttf", None, None),
        ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", None, None),
        ("C:/Windows/Fonts/malgun.ttf", None, None),
    ]
    for path, ir, ib in candidates:
        if not os.path.exists(path): continue
        try:
            if path.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont("F",  path, subfontIndex=ir))
                pdfmetrics.registerFont(TTFont("FB", path, subfontIndex=ib))
            else:
                pdfmetrics.registerFont(TTFont("F",  path))
                bp = path.replace(".ttf","Bold.ttf")
                pdfmetrics.registerFont(TTFont("FB", bp if os.path.exists(bp) else path))
            return ("F","FB")
        except: continue
    return ("Helvetica","Helvetica-Bold")

FN, FNB = _reg()

W = A4[0] - 30*mm   # 표 전체 너비


def _p(text, size=8, bold=False, align="LEFT", color=colors.black):
    fn = FNB if bold else FN
    al = {"LEFT":0,"CENTER":1,"RIGHT":2}.get(align,0)
    style = ParagraphStyle("s", fontName=fn, fontSize=size,
                            leading=size*1.4, alignment=al,
                            textColor=color, wordWrap='CJK')
    return Paragraph(str(text) if text else "", style)


def _ts(*cmds):
    base = [
        ("FONTNAME",   (0,0),(-1,-1), FN),
        ("FONTSIZE",   (0,0),(-1,-1), 8),
        ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",      (0,0),(-1,-1), "CENTER"),
        ("GRID",       (0,0),(-1,-1), 0.5, colors.black),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING",(0,0),(-1,-1), 2),
        ("LEFTPADDING",(0,0),(-1,-1), 2),
        ("RIGHTPADDING",(0,0),(-1,-1), 2),
    ]
    return TableStyle(base + list(cmds))


def _open(path):
    try:
        if platform.system()=="Darwin": subprocess.run(["open",path])
        elif platform.system()=="Windows": os.startfile(path)
        else: subprocess.run(["xdg-open",path])
    except: pass


def _out(filename, save_dir):
    if save_dir and os.path.isdir(save_dir):
        return os.path.join(save_dir, filename)
    desktop = os.path.join(os.path.expanduser("~"),"Desktop")
    base = desktop if os.path.isdir(desktop) else os.path.expanduser("~")
    return os.path.join(base, filename)


def save_accident_form_pdf(acc: dict, ai_content: str = "",
                            save_dir: str = "") -> str:
    """
    사고현장 보고서를 공식 양식 PDF로 저장합니다.
    acc: 사고 입력 딕셔너리
    ai_content: AI 생성 텍스트 (개요/원인/과정 파싱용)
    """
    date_c   = acc.get("write_date","").replace("-","")
    filename = f"{date_c}_사고보고서_양식.pdf"
    path     = _out(filename, save_dir)

    doc = SimpleDocTemplate(path, pagesize=A4,
                             topMargin=10*mm, bottomMargin=10*mm,
                             leftMargin=15*mm, rightMargin=15*mm)
    story = []

    # AI 생성 내용에서 섹션 파싱
    def extract(content, start_markers, end_markers=None):
        lines = content.split("\n")
        capturing = False
        result = []
        for line in lines:
            line = line.strip()
            if any(m in line for m in start_markers):
                capturing = True
                continue
            if capturing:
                if end_markers and any(m in line for m in end_markers):
                    break
                if line and not line.startswith("[") or not end_markers:
                    if line.startswith("→"): line = line[1:].strip()
                    if line.startswith("•"): line = line[1:].strip()
                    if line: result.append(line)
        return "\n".join(result[:8])

    overview     = extract(ai_content, ["재해 발생 개요","[재해 발생 개요]"],
                           ["사고 직접원인","[사고 직접 원인]"]) or acc.get("overview","")
    direct_cause = extract(ai_content, ["사고 직접원인","[사고 직접 원인]"],
                           ["작업내용","[작업 내용"]) or acc.get("direct_cause","")
    work_proc    = extract(ai_content, ["작업내용","[작업 내용"],
                           ["발생 형태","─────"]) or acc.get("work_process","")
    law_review   = extract(ai_content, ["관련 법규 검토","[관련 법규"],
                           ["담당","─────"])

    # ── 제목 ────────────────────────────────────────────────
    title_data = [[_p("사  고  현  장  보  고  서", 14, bold=True, align="CENTER")]]
    title_t = Table(title_data, colWidths=[W])
    title_t.setStyle(_ts(("BOX",(0,0),(-1,-1),1,colors.black),
                         ("TOPPADDING",(0,0),(-1,-1),6),
                         ("BOTTOMPADDING",(0,0),(-1,-1),6)))
    story.append(title_t)

    # ── 결재란 ───────────────────────────────────────────────
    kw = W * 0.35
    ap_data = [
        [_p("결  재", bold=True, align="CENTER"),
         _p("담  당", align="CENTER"),
         _p("과  장", align="CENTER"),
         _p("소  장", align="CENTER")],
        ["", "", "", ""],
        ["", "", "", ""],
    ]
    ap_col = [kw, (W-kw)/3, (W-kw)/3, (W-kw)/3]
    ap_t = Table(ap_data, colWidths=ap_col, rowHeights=[6*mm, 10*mm, 4*mm])
    ap_t.setStyle(_ts(
        ("SPAN",(0,0),(0,2)),
        ("GRID",(0,0),(-1,-1),0.5,colors.black),
    ))
    story.append(ap_t)

    # ── 작성일자 ─────────────────────────────────────────────
    wd = acc.get("write_date","")
    date_parts = wd.split("-") if "-" in wd else ["20  ","  ","  "]
    date_str = f"20{date_parts[0][2:] if len(date_parts)>0 else '  '} 년   {date_parts[1] if len(date_parts)>1 else '  '} 월   {date_parts[2] if len(date_parts)>2 else '  '} 일"
    d_data = [[_p(f"작성일자:  {date_str}", align="LEFT")]]
    d_t = Table(d_data, colWidths=[W])
    d_t.setStyle(_ts(("BOX",(0,0),(-1,-1),0.5,colors.black),
                     ("ALIGN",(0,0),(-1,-1),"LEFT")))
    story.append(d_t)

    # ── 현장명 / 작성자 ──────────────────────────────────────
    site_data = [
        [_p("현  장  명", bold=True, align="CENTER"),
         _p(acc.get("project_name",""), align="LEFT"),
         _p("작성자", bold=True, align="CENTER"),
         _p("직위", bold=True, align="CENTER"),
         _p(acc.get("writer_position",""), align="CENTER"),
         _p("성  명", bold=True, align="CENTER"),
         _p(acc.get("writer_name",""), align="CENTER"),
         _p("(인)", align="CENTER")],
    ]
    sc = [W*0.13, W*0.22, W*0.07, W*0.07, W*0.1, W*0.09, W*0.17, W*0.07]
    s_t = Table(site_data, colWidths=sc, rowHeights=[8*mm])
    s_t.setStyle(_ts(("ALIGN",(1,0),(1,0),"LEFT")))
    story.append(s_t)

    # ── 안전관리책임자 + 재해자 ──────────────────────────────
    ra_w  = W * 0.07   # 안전관리책임자 열
    ra_w2 = W * 0.08
    ra_w3 = W * 0.12
    rb_w  = W * 0.13
    rb_w2 = W * 0.28

    mgr_data = [
        # row 0
        [_p("안\n전\n관\n리\n책\n임\n자", bold=True, align="CENTER"),
         _p("구  분", bold=True, align="CENTER"),
         _p("직  위", bold=True, align="CENTER"),
         _p("성  명", bold=True, align="CENTER"),
         _p("재\n해\n자", bold=True, align="CENTER"),
         _p("협력업체명", bold=True, align="CENTER"),
         _p(acc.get("subcontractor",""), align="LEFT")],
        # row 1
        ["",
         _p("현장소장", align="CENTER"),
         _p(acc.get("site_manager",""), align="CENTER"),
         "", "",
         _p("공사종류", bold=True, align="CENTER"),
         _p(acc.get("work_type",""), align="LEFT")],
        # row 2
        ["",
         _p("공사과장", align="CENTER"),
         _p(acc.get("const_manager",""), align="CENTER"),
         "", "",
         _p("성    명", bold=True, align="CENTER"),
         _p(acc.get("victim_name",""), align="CENTER")],
        # row 3
        ["",
         _p("담당기사", align="CENTER"),
         _p(acc.get("engineer",""), align="CENTER"),
         "", "",
         _p("주민등록번호", bold=True, align="CENTER"),
         _p("", align="CENTER")],
    ]
    mc = [ra_w, ra_w*1.5, ra_w2, ra_w3, ra_w, rb_w, rb_w2]
    # 나머지 합산
    mc[-1] = W - sum(mc[:-1])
    m_t = Table(mgr_data, colWidths=mc, rowHeights=[9*mm]*4)
    m_t.setStyle(_ts(
        ("SPAN",(0,0),(0,3)),   # 안전관리책임자 세로 합치기
        ("SPAN",(4,0),(4,3)),   # 재해자 세로 합치기
        ("SPAN",(3,0),(3,3)),   # 성명열 합치기 (빈칸)
        ("VALIGN",(0,0),(0,3),"MIDDLE"),
        ("VALIGN",(4,0),(4,3),"MIDDLE"),
    ))
    story.append(m_t)

    # 직종 / 채용일 행 추가
    extra_data = [[
        _p("", align="CENTER"),
        _p("", align="CENTER"), "", "",
        _p("", align="CENTER"),
        _p("직  종 / 채용일", bold=True, align="CENTER"),
        _p(f"{acc.get('victim_job','')}  /  {acc.get('hire_date','')}", align="CENTER"),
    ]]
    e_t = Table(extra_data, colWidths=mc, rowHeights=[8*mm])
    e_t.setStyle(_ts())
    story.append(e_t)

    # ── 사고발생일시 ─────────────────────────────────────────
    adt = acc.get("accident_datetime","")
    acc_date = adt.split(" ")[0] if " " in adt else adt
    acc_time = adt.split(" ")[1] if " " in adt else ""
    dp = acc_date.split("-") if "-" in acc_date else ["","",""]
    acc_date_str = f"20{dp[0][2:] if len(dp)>0 else '  '} 년   {dp[1] if len(dp)>1 else '  '} 월   {dp[2] if len(dp)>2 else '  '} 일   {acc_time}  분경"

    acc_t_data = [[
        _p("사고발생일시", bold=True, align="CENTER"),
        _p(acc_date_str, align="LEFT"),
    ]]
    at_t = Table(acc_t_data, colWidths=[W*0.15, W*0.85], rowHeights=[8*mm])
    at_t.setStyle(_ts(("ALIGN",(1,0),(1,0),"LEFT")))
    story.append(at_t)

    # ── 작업장소 + 기인물 ────────────────────────────────────
    loc_data = [[
        _p("작업장소(사고당시)", bold=True, align="CENTER"),
        _p(acc.get("location",""), align="LEFT"),
        _p("기인물", bold=True, align="CENTER"),
        _p(acc.get("cause_object",""), align="LEFT"),
    ]]
    lc = [W*0.17, W*0.48, W*0.1, W*0.25]
    l_t = Table(loc_data, colWidths=lc, rowHeights=[8*mm])
    l_t.setStyle(_ts(("ALIGN",(1,0),(1,0),"LEFT"),("ALIGN",(3,0),(3,0),"LEFT")))
    story.append(l_t)

    # ── 재해발생 개요 ────────────────────────────────────────
    ov_data = [
        [_p("재해발생 개요(상세히 기술요함) :", bold=True, align="LEFT")],
        [_p(overview, align="LEFT")],
    ]
    ov_t = Table(ov_data, colWidths=[W], rowHeights=[7*mm, 30*mm])
    ov_t.setStyle(_ts(("ALIGN",(0,0),(-1,-1),"LEFT"),
                      ("VALIGN",(0,1),(0,1),"TOP")))
    story.append(ov_t)

    # ── 사고 직접원인 ────────────────────────────────────────
    dc_data = [
        [_p("사고 직접원인 :", bold=True, align="LEFT")],
        [_p(direct_cause, align="LEFT")],
    ]
    dc_t = Table(dc_data, colWidths=[W], rowHeights=[7*mm, 22*mm])
    dc_t.setStyle(_ts(("ALIGN",(0,0),(-1,-1),"LEFT"),
                      ("VALIGN",(0,1),(0,1),"TOP")))
    story.append(dc_t)

    # ── 작업내용 및 과정 ─────────────────────────────────────
    wp_data = [
        [_p("작업내용 및 과정 :", bold=True, align="LEFT")],
        [_p(work_proc, align="LEFT")],
    ]
    wp_t = Table(wp_data, colWidths=[W], rowHeights=[7*mm, 22*mm])
    wp_t.setStyle(_ts(("ALIGN",(0,0),(-1,-1),"LEFT"),
                      ("VALIGN",(0,1),(0,1),"TOP")))
    story.append(wp_t)

    # ── 발생형태 / 상해부위 / 상해종류 ──────────────────────
    bt_data = [
        [_p("발  생  형  태", bold=True, align="CENTER"),
         _p("상  해  부  위", bold=True, align="CENTER"),
         _p("상  해  종  류", bold=True, align="CENTER")],
        [_p(f"(예:추락,낙하,감전등으로 기술요)\n\n{acc.get('accident_type','')}", align="CENTER"),
         _p(f"(예:머리,눈,팔,다리,등으로 기술요)\n\n{acc.get('injury_part','')}", align="CENTER"),
         _p(f"(예:골절,타박상,화상 등으로 기술요)\n\n{acc.get('injury_type','')}", align="CENTER")],
    ]
    bt_t = Table(bt_data, colWidths=[W/3, W/3, W/3], rowHeights=[7*mm, 20*mm])
    bt_t.setStyle(_ts(("VALIGN",(0,1),(-1,1),"TOP")))
    story.append(bt_t)

    # ── 관련 법규 검토 ───────────────────────────────────────
    if law_review:
        lr_data = [
            [_p("관련 법규 검토", bold=True, align="LEFT")],
            [_p(law_review, align="LEFT")],
        ]
        lr_t = Table(lr_data, colWidths=[W], rowHeights=[7*mm, 18*mm])
        lr_t.setStyle(_ts(("ALIGN",(0,0),(-1,-1),"LEFT"),
                          ("VALIGN",(0,1),(0,1),"TOP"),
                          ("BACKGROUND",(0,0),(0,0),colors.HexColor("#f0f4ff"))))
        story.append(lr_t)

    doc.build(story)
    _open(path)
    return path