"""
pdf_utils.py — PDF 생성 (한글 폰트 완전 수정)
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


def _register_font() -> tuple:
    """한글 폰트 등록 - 일반체/굵은체 모두 등록"""
    # Mac 폰트 경로들
    mac_fonts = [
        ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0, 3),
        ("/Library/Fonts/NanumGothic.ttf", None, None),
        ("/Library/Fonts/AppleGothic.ttf", None, None),
    ]
    linux_fonts = [
        ("/usr/share/fonts/truetype/nanum/NanumGothic.ttf", None, None),
        ("/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf", None, None),
    ]
    win_fonts = [
        ("C:/Windows/Fonts/malgun.ttf", None, None),
        ("C:/Windows/Fonts/malgunbd.ttf", None, None),
    ]

    def try_register(path, idx_regular, idx_bold):
        try:
            if path.endswith(".ttc"):
                pdfmetrics.registerFont(TTFont("KR", path, subfontIndex=idx_regular))
                pdfmetrics.registerFont(TTFont("KR-Bold", path, subfontIndex=idx_bold))
            else:
                pdfmetrics.registerFont(TTFont("KR", path))
                # Bold 따로 없으면 일반체로 대체
                bold_path = path.replace(".ttf", "Bold.ttf").replace("Gothic.ttf", "GothicBold.ttf")
                if os.path.exists(bold_path):
                    pdfmetrics.registerFont(TTFont("KR-Bold", bold_path))
                else:
                    pdfmetrics.registerFont(TTFont("KR-Bold", path))
            return True
        except:
            return False

    all_fonts = mac_fonts + linux_fonts + win_fonts
    for path, ir, ib in all_fonts:
        if os.path.exists(path):
            if try_register(path, ir, ib):
                return ("KR", "KR-Bold")

    return ("Helvetica", "Helvetica-Bold")

FONT, FONT_BOLD = _register_font()


def _st():
    b  = dict(fontName=FONT,      leading=18)
    bb = dict(fontName=FONT_BOLD, leading=18)
    return {
        "title":  ParagraphStyle("T",  **bb, fontSize=15, spaceAfter=3,
                                  textColor=colors.HexColor("#1a1a2e")),
        "h2":     ParagraphStyle("H2", **bb, fontSize=11, spaceAfter=2,
                                  textColor=colors.HexColor("#16213e")),
        "h3":     ParagraphStyle("H3", **bb, fontSize=10, spaceAfter=2),
        "body":   ParagraphStyle("B",  **b,  fontSize=9,  spaceAfter=2),
        "small":  ParagraphStyle("S",  **b,  fontSize=8,
                                  textColor=colors.HexColor("#555")),
        "warn":   ParagraphStyle("W",  **bb, fontSize=12,
                                  textColor=colors.red, spaceAfter=4),
        "blue":   ParagraphStyle("BL", **b,  fontSize=9,
                                  textColor=colors.HexColor("#0000cc")),
        "red":    ParagraphStyle("R",  **b,  fontSize=9,
                                  textColor=colors.red),
    }


def _path_out(filename, save_dir):
    if save_dir and os.path.isdir(save_dir):
        return os.path.join(save_dir, filename)
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base = desktop if os.path.isdir(desktop) else os.path.expanduser("~")
    return os.path.join(base, filename)


def _open(path):
    try:
        if platform.system() == "Darwin":   subprocess.run(["open", path])
        elif platform.system() == "Windows": os.startfile(path)
        else:                                subprocess.run(["xdg-open", path])
    except: pass


def _doc(path):
    return SimpleDocTemplate(path, pagesize=A4,
                              topMargin=15*mm, bottomMargin=15*mm,
                              leftMargin=15*mm, rightMargin=15*mm)


def _ts(header_bg="#16213e"):
    return TableStyle([
        ("BACKGROUND",   (0,0),(-1,0), colors.HexColor(header_bg)),
        ("TEXTCOLOR",    (0,0),(-1,0), colors.white),
        ("FONTNAME",     (0,0),(-1,0), FONT_BOLD),
        ("FONTNAME",     (0,1),(-1,-1), FONT),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("ALIGN",        (0,0),(-1,-1), "LEFT"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f5f5f5")]),
        ("GRID",         (0,0),(-1,-1), 0.4, colors.HexColor("#bbbbbb")),
        ("TOPPADDING",   (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING",  (0,0),(-1,-1), 6),
    ])


def _sig(story, st):
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 3*mm))
    data = [["안전관리자: ________________(인)",
             "현장소장: ________________(인)",
             "작업반장: ________________(인)"]]
    t = Table(data, colWidths=[60*mm, 60*mm, 57*mm])
    t.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(-1,-1), FONT),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",   (0,0),(-1,-1), 6),
    ]))
    story.append(t)


# ── 기능 2: 일일 안전일지 (표 형식) ───────────────────────────
def save_daily_log_pdf(daily: dict, report_text: str,
                        project: str = "", save_dir: str = "") -> str:
    date_c  = daily.get("date_c", datetime.today().strftime("%Y%m%d"))
    manager = daily.get("manager", "")
    path    = _path_out(f"{date_c}_안전일지_{manager}.pdf", save_dir)
    st      = _st()
    doc     = _doc(path)
    story   = []

    # 제목
    story.append(Paragraph("일 일 안 전 일 지", st["title"]))
    story.append(Paragraph(f"현장명: {project}", st["small"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 3*mm))

    # 1. 작업 현황 표
    story.append(Paragraph("1. 당일 작업 현황", st["h2"]))
    w = daily.get("weather", {})
    ws = (f"최고풍속 {w.get('wind_max','-')} ({w.get('peak_time','-')} 도달) / "
          f"평균기온 {w.get('temp_avg','-')}" if w else "-")
    rows = [
        ["항목", "내용", "항목", "내용"],
        ["일자", daily.get("date",""), "관리자", daily.get("manager","")],
        ["공정 시간", daily.get("work_time",""), "작업 위치", daily.get("location","")],
        ["작업 환경", daily.get("env",""), "주요 자재", daily.get("materials","")],
        ["날씨", ws, "신규 인원", daily.get("new_workers","없음")],
        ["진행 공정", daily.get("work_process",""), "주변 간섭", daily.get("nearby_interference","없음")],
        ["전일 미조치", daily.get("prev_issues","없음"), "", ""],
    ]
    t = Table(rows, colWidths=[25*mm, 62*mm, 25*mm, 60*mm])
    ts = _ts()
    ts.add("BACKGROUND", (0,1),(0,-1), colors.HexColor("#e8eaf6"))
    ts.add("BACKGROUND", (2,1),(2,-1), colors.HexColor("#e8eaf6"))
    ts.add("FONTNAME",   (0,1),(0,-1), FONT_BOLD)
    ts.add("FONTNAME",   (2,1),(2,-1), FONT_BOLD)
    ts.add("SPAN",       (1,6),(3,6))
    t.setStyle(ts)
    story.append(t)
    story.append(Spacer(1, 3*mm))

    # 2. 인원·장비 표
    story.append(Paragraph("2. 인원 및 장비 현황", st["h2"]))
    pw = [
        ["구분", "내용"],
        ["투입 인원 (공종별)", daily.get("workers","")],
        ["투입 장비 (기종/대수)", daily.get("equipment","없음")],
    ]
    t2 = Table(pw, colWidths=[45*mm, 127*mm])
    t2.setStyle(_ts())
    story.append(t2)
    story.append(Spacer(1, 3*mm))

    # 3. 위험 요인 표
    story.append(Paragraph("3. 위험 요인 및 안전 조치 (법규 기반)", st["h2"]))
    risk_rows = [["위험 요인", "법적 근거", "안전 조치 사항"]]
    lines = report_text.split("\n")
    risk = law = action = ""
    for line in lines:
        line = line.strip()
        if line.startswith("[위험요인]"):
            if risk: risk_rows.append([risk, law, action])
            risk = line.replace("[위험요인]","").strip(); law = ""; action = ""
        elif line.startswith("[법적 근거]"):
            law = line.replace("[법적 근거]","").strip()
        elif line.startswith("[안전 조치]"):
            action = line.replace("[안전 조치]","").strip()
    if risk: risk_rows.append([risk, law, action])

    if len(risk_rows) > 1:
        t3 = Table(risk_rows, colWidths=[45*mm, 55*mm, 72*mm])
        t3.setStyle(_ts())
        story.append(t3)
    else:
        story.append(Paragraph("(위험 요인 정보 없음)", st["body"]))
    story.append(Spacer(1, 3*mm))

    # 4. TBM 메시지
    story.append(Paragraph("4. 근로자 TBM 메시지", st["h2"]))
    tbm = ""
    in_tbm = False
    for line in lines:
        if "TBM 메시지" in line: in_tbm = True; continue
        if in_tbm and line.strip() and not line.strip().startswith("["):
            tbm += line.strip() + " "
    tbm_data = [[tbm or "(TBM 메시지 없음)"]]
    t4 = Table(tbm_data, colWidths=[172*mm])
    t4.setStyle(TableStyle([
        ("FONTNAME",     (0,0),(-1,-1), FONT),
        ("FONTSIZE",     (0,0),(-1,-1), 9),
        ("BACKGROUND",   (0,0),(-1,-1), colors.HexColor("#fff8e1")),
        ("GRID",         (0,0),(-1,-1), 0.5, colors.HexColor("#ffc107")),
        ("TOPPADDING",   (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
    ]))
    story.append(t4)
    _sig(story, st)
    doc.build(story)
    _open(path)
    return path


# ── 기능 3: 체크리스트 PDF ────────────────────────────────────
def save_checklist_pdf(content: str, date: str,
                        project: str = "", save_dir: str = "") -> str:
    path = _path_out(f"{date}_안전점검체크리스트.pdf", save_dir)
    st   = _st()
    doc  = _doc(path)
    story = []

    story.append(Paragraph("현장 안전 점검 체크리스트", st["title"]))
    if project:
        story.append(Paragraph(f"현장명: {project}  |  점검일: {date}", st["small"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 3*mm))

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 1*mm))
        elif line.startswith(("Ⅰ.","Ⅱ.")):
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(line, st["h2"]))
        elif line[:2] in ("1.","2.","3.","4.","5.") and len(line) < 20:
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(line, st["h3"]))
        elif "[!]" in line:
            story.append(Paragraph(f'<font color="red"><b>{line}</b></font>', st["body"]))
        elif line.startswith("□"):
            story.append(Paragraph(line, st["body"]))
        elif line.startswith("[점검"):
            story.append(Spacer(1, 5*mm))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
            story.append(Paragraph(line, st["h2"]))
        elif any(x in line for x in ["안전관리자","현장소장","작업반장"]):
            story.append(Paragraph(line, st["body"]))
        else:
            story.append(Paragraph(line, st["body"]))

    doc.build(story)
    _open(path)
    return path


# ── 기능 4: 사고 보고서 PDF (표 형식) ────────────────────────
def save_accident_report_pdf(content: str, date: str,
                              project: str = "", save_dir: str = "") -> str:
    path = _path_out(f"{date}_사고보고서.pdf", save_dir)
    st   = _st()
    doc  = _doc(path)
    story = []

    if "[중대재해 주의]" in content:
        story.append(Paragraph("⚠ 중대재해 주의", st["warn"]))

    story.append(Paragraph("사 고 현 장 보 고 서", st["title"]))
    if project:
        story.append(Paragraph(f"현장명: {project}", st["small"]))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 3*mm))

    current_section = ""
    section_lines = []

    def flush_section():
        if section_lines:
            for l in section_lines:
                if "[수정됨]" in l:
                    story.append(Paragraph(l.replace("[수정됨]",""), st["red"]))
                elif l.startswith("•"):
                    story.append(Paragraph(l, st["body"]))
                elif l.startswith("─"):
                    story.append(HRFlowable(width="100%", thickness=0.3, color=colors.grey))
                else:
                    story.append(Paragraph(l, st["body"]))

    for line in content.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 1*mm))
        elif line.startswith("[") and line.endswith("]") and "수정됨" not in line:
            flush_section()
            section_lines = []
            current_section = line
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(line, st["h2"]))
        elif "─" * 5 in line:
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.grey))
        elif line.startswith("[사고현장"):
            pass
        else:
            if "[수정됨]" in line:
                story.append(Paragraph(line.replace("[수정됨]",""), st["red"]))
            else:
                story.append(Paragraph(line, st["body"]))

    story.append(Spacer(1, 8*mm))
    sig_data = [["담당 (서명):", "과장 (서명):", "소장 (서명):"]]
    t = Table(sig_data, colWidths=[57*mm, 57*mm, 58*mm])
    t.setStyle(TableStyle([
        ("FONTNAME",(0,0),(-1,-1), FONT),
        ("FONTSIZE",(0,0),(-1,-1), 10),
        ("ALIGN",  (0,0),(-1,-1), "CENTER"),
        ("TOPPADDING",(0,0),(-1,-1), 8),
    ]))
    story.append(t)
    doc.build(story)
    _open(path)
    return path