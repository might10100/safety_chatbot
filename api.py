"""
app.py — Streamlit 웹 앱 (전면 개선판)
"""
import streamlit as st
from datetime import date, datetime, timedelta
import json, os

from chain_search import (load_resources, law_search, get_law_candidates,
                           generate_daily_log, generate_checklist,
                           generate_accident_report)
from weather import fetch_weather
from pdf_utils import (save_daily_log_pdf, save_checklist_pdf,
                        save_accident_report_pdf)

st.set_page_config(page_title="건설 현장 안전관리 AI", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
.main-title  {font-size:2rem;font-weight:800;color:#1a1a2e;}
.sub-title   {font-size:0.9rem;color:#888;margin-bottom:1.5rem;}
.card        {background:#f8f9ff;border-radius:12px;padding:1.2rem;
               border-left:5px solid #4361ee;margin-bottom:0.8rem;}
.law-card    {background:#fffde7;border-radius:8px;padding:0.8rem;
               border:1px solid #ffc107;margin-bottom:0.5rem;}
.warn-box    {background:#fff0f0;border-radius:8px;padding:0.8rem;
               border-left:4px solid #e74c3c;margin:0.5rem 0;}
.info-box    {background:#e3f2fd;border-radius:8px;padding:0.8rem;
               border-left:4px solid #2196f3;margin:0.5rem 0;}
.ok-box      {background:#e8f5e9;border-radius:8px;padding:0.8rem;
               border-left:4px solid #4caf50;margin:0.5rem 0;}
.report-card {background:#fff;border-radius:8px;padding:0.8rem;
               border:1px solid #ddd;margin-bottom:0.5rem;cursor:pointer;}
</style>
""", unsafe_allow_html=True)

# ── Session State 초기화 ──────────────────────────────────────
for k, v in {
    "page":"setup","project":{},"zones":[],"cur_zone":0,
    "zone_data":{},"feature":None,"law_candidates":[],
    "selected_laws":[],"report_content":"","daily_input":{},
    "accident_input":{},"pdf_save_dir":"","view_report":None,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏗️ 안전관리 AI")
    p = st.session_state.project
    if p:
        st.markdown(f"""<div class='card'>
<b>{p.get('name','')}</b><br>
<small>📅 {p.get('period_start','')} ~ {p.get('period_end','')}</small><br>
<small>📍 {p.get('address','')}</small></div>""", unsafe_allow_html=True)

    if st.session_state.page != "setup":
        st.divider()
        if st.session_state.zones:
            st.markdown("**📍 구역 선택**")
            for i, z in enumerate(st.session_state.zones):
                label = f"{'▶ ' if i==st.session_state.cur_zone else ''}{z}"
                if st.button(label, key=f"z{i}", use_container_width=True):
                    st.session_state.cur_zone = i
                    st.session_state.page = "main"
                    st.session_state.feature = None
                    st.rerun()

        st.divider()
        st.markdown("**🛠️ 기능**")
        for label, key in [("💬 법규 검색","law"),("📋 일일 안전일지","daily"),
                            ("✅ 안전 체크리스트","checklist"),("🚨 사고 보고서","accident")]:
            if st.button(label, key=f"m{key}", use_container_width=True):
                st.session_state.feature = key
                st.session_state.page = "feature"
                st.session_state.report_content = ""
                st.session_state.selected_laws = []
                st.session_state.law_candidates = []
                st.session_state.view_report = None
                st.rerun()

        st.divider()
        st.markdown("**📁 PDF 저장 경로**")
        st.session_state.pdf_save_dir = st.text_input(
            "경로", value=st.session_state.pdf_save_dir,
            placeholder="비우면 바탕화면", label_visibility="collapsed")

        if st.button("⚙️ 현장 정보 수정", use_container_width=True):
            st.session_state.page = "setup"
            st.rerun()


# ══════════════════════════════════════════════════════════════
# 페이지: 초기 설정
# ══════════════════════════════════════════════════════════════
def page_setup():
    st.markdown('<p class="main-title">🏗️ 건설 현장 안전관리 AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">현장 정보를 입력하고 AI 안전관리를 시작하세요.</p>', unsafe_allow_html=True)

    p = st.session_state.project  # 기존 값 유지

    c1, c2 = st.columns(2)
    name    = c1.text_input("시공명 *", value=p.get("name",""),
                             placeholder="예: 강남 OO아파트 신축공사")
    address = c2.text_input("현장주소 *", value=p.get("address",""),
                             placeholder="예: 서울시 강남구 역삼동 123-4")

    st.markdown("**시공기간 ***")
    dc1, dc2 = st.columns(2)

    # 기존 날짜 파싱
    try:
        ps_default = datetime.strptime(p.get("period_start",""), "%Y-%m-%d").date() if p.get("period_start") else date.today()
        pe_default = datetime.strptime(p.get("period_end",""), "%Y-%m-%d").date() if p.get("period_end") else date.today()
    except:
        ps_default = date.today()
        pe_default = date.today()

    period_start = dc1.date_input("착공일", value=ps_default, key="ps")
    period_end   = dc2.date_input("준공일", value=pe_default, key="pe")

    save_dir = st.text_input("PDF 저장 경로", value=st.session_state.pdf_save_dir,
                              placeholder="비우면 바탕화면에 저장")

    st.markdown("---")
    st.markdown("**📍 구역 구획화**")
    zone_count = st.number_input("구역 수", min_value=1, max_value=20,
                                  value=max(1, len(st.session_state.zones)), step=1)

    zone_names = []
    cols = st.columns(min(int(zone_count), 4))
    for i in range(int(zone_count)):
        default_val = st.session_state.zones[i] if i < len(st.session_state.zones) else f"구역{i+1}"
        with cols[i % 4]:
            name_i = st.text_input(f"구역 {i+1}", value=default_val, key=f"zone_name_{i}")
            zone_names.append(name_i.strip() if name_i.strip() else f"구역{i+1}")

    st.markdown("""<div class='info-box'>
💡 구역을 나누면 구역별로 대화 기록과 보고서를 따로 저장·관리합니다.<br>
구역을 새로 설정하면 기존 데이터는 별도 저장되고 새 구역이 초기화됩니다.
</div>""", unsafe_allow_html=True)

    if st.button("✅ 저장하고 시작", type="primary", use_container_width=True):
        if not all([name, address]):
            st.error("시공명과 현장주소는 필수입니다.")
            return

        new_project = {
            "name": name, "address": address,
            "period_start": period_start.strftime("%Y-%m-%d"),
            "period_end":   period_end.strftime("%Y-%m-%d"),
        }

        # 구역 재설정: 기존 데이터는 archive로 보존
        old_zones = st.session_state.zones
        new_zones = zone_names

        if old_zones and set(old_zones) != set(new_zones):
            # 기존 데이터 archive 저장
            if "zone_archive" not in st.session_state:
                st.session_state.zone_archive = {}
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.session_state.zone_archive[ts] = {
                "zones":     old_zones,
                "zone_data": st.session_state.zone_data.copy(),
                "project":   st.session_state.project.copy(),
            }

        st.session_state.project      = new_project
        st.session_state.zones        = new_zones
        st.session_state.cur_zone     = 0
        st.session_state.pdf_save_dir = save_dir

        # 새 구역 초기화 (기존 구역 데이터 유지)
        for z in new_zones:
            if z not in st.session_state.zone_data:
                st.session_state.zone_data[z] = {"chat":[], "reports":[]}

        with st.spinner("AI 모델 로딩 중..."):
            load_resources()

        st.session_state.page = "main"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# 페이지: 메인 대시보드
# ══════════════════════════════════════════════════════════════
def page_main():
    p    = st.session_state.project
    zone = st.session_state.zones[st.session_state.cur_zone]

    st.markdown(f'<p class="main-title">{p["name"]}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-title">📅 {p.get("period_start","")} ~ {p.get("period_end","")}  |  📍 {p.get("address","")}</p>',
                unsafe_allow_html=True)

    # 구역 탭 — 선택된 구역만 내용 표시
    tabs = st.tabs(st.session_state.zones)
    for i, tab in enumerate(tabs):
        with tab:
            z  = st.session_state.zones[i]
            zd = st.session_state.zone_data.get(z, {"chat":[], "reports":[]})
            rs = zd.get("reports", [])

            # 이 탭이 현재 선택된 구역일 때만 클릭 반응
            if i != st.session_state.cur_zone:
                if st.button(f"📍 {z} 구역으로 이동", key=f"tab_go_{i}"):
                    st.session_state.cur_zone = i
                    st.rerun()
                continue

            # ── 통계 카드 ──
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("💬 법규 검색", len(zd.get("chat",[])) // 2)
            c2.metric("📋 안전일지",  sum(1 for r in rs if r["type"]=="daily"))
            c3.metric("✅ 체크리스트", sum(1 for r in rs if r["type"]=="checklist"))
            c4.metric("🚨 사고보고서", sum(1 for r in rs if r["type"]=="accident"))

            st.markdown("---")

            # ── 최근 일주일 보고서 ──
            one_week_ago = datetime.now() - timedelta(days=7)
            recent = [r for r in rs if _parse_report_date(r.get("date","")) >= one_week_ago]

            col_left, col_right = st.columns([1,1])

            with col_left:
                st.markdown("**📂 최근 일주일 보고서**")
                if recent:
                    for r in reversed(recent):
                        with st.expander(f"{r['label']} — {r.get('date','')}"):
                            st.text_area("내용", value=r.get("content","(내용 없음)"),
                                         height=300, key=f"view_{r.get('id','')}",
                                         disabled=True)
                            if r.get("path") and os.path.exists(r.get("path","")):
                                st.caption(f"💾 PDF: {r['path']}")
                else:
                    st.info("최근 7일 내 작성된 보고서가 없습니다.")

            with col_right:
                st.markdown("**📋 전체 보고서 목록**")
                if rs:
                    for r in reversed(rs[-10:]):
                        st.markdown(f"""<div class='card'>
<b>{r['label']}</b> — {r.get('date','')}<br>
<small>💾 {r.get('path','PDF 없음')}</small></div>""", unsafe_allow_html=True)
                else:
                    st.info("작성된 보고서가 없습니다. 왼쪽 메뉴에서 기능을 선택하세요.")


def _parse_report_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return datetime.min


# ══════════════════════════════════════════════════════════════
# 공통: 데일리 입력 폼
# ══════════════════════════════════════════════════════════════
def daily_form(key_prefix: str = "") -> dict:
    st.markdown("### 📝 데일리 입력")
    di = st.session_state.daily_input  # 이전 입력값 유지

    c1, c2 = st.columns(2)

    # 날짜 달력
    try:
        d_default = datetime.strptime(di.get("date",""), "%Y-%m-%d").date()
    except:
        d_default = date.today()
    d = c1.date_input("날짜 *", value=d_default, key=f"{key_prefix}date")

    # 시간 선택 (클릭으로)
    hours   = [f"{h:02d}" for h in range(6, 21)]
    minutes = ["00", "30"]
    tc1, tc2, tc3, tc4 = st.columns(4)
    start_h = tc1.selectbox("시작 시", hours,
                              index=hours.index("08") if "08" in hours else 0,
                              key=f"{key_prefix}sh")
    start_m = tc2.selectbox("시작 분", minutes, key=f"{key_prefix}sm")
    end_h   = tc3.selectbox("종료 시", hours,
                              index=hours.index("17") if "17" in hours else 9,
                              key=f"{key_prefix}eh")
    end_m   = tc4.selectbox("종료 분", minutes, key=f"{key_prefix}em")
    work_time = f"{start_h}:{start_m} ~ {end_h}:{end_m}"

    manager  = c1.text_input("관리자 이름 *", value=di.get("manager",""),
                              placeholder="예: 김성균", key=f"{key_prefix}mgr")
    location = c2.text_input("작업 위치 *", value=di.get("location",""),
                              placeholder="예: A동 12층 외벽", key=f"{key_prefix}loc")

    c3, c4 = st.columns(2)
    workers   = c3.text_area("인원 현황 (공종별) *", value=di.get("workers",""),
                              placeholder="예: 철근공 10명, 형틀공 5명",
                              height=80, key=f"{key_prefix}wk")
    equipment = c4.text_area("장비 현황 (기종/대수)", value=di.get("equipment",""),
                              placeholder="예: 타워크레인 1대, 굴착기 1대",
                              height=80, key=f"{key_prefix}eq")

    c5, c6 = st.columns(2)
    env          = c5.selectbox("작업 환경", ["지상","고소","밀폐","지하","수중","기타"],
                                 key=f"{key_prefix}env")
    materials    = c6.text_input("주요 자재", value=di.get("materials",""),
                                  placeholder="예: 철근, 거푸집", key=f"{key_prefix}mat")
    work_process = st.text_area("진행 공정 *", value=di.get("work_process",""),
                                 placeholder="예: 12층 외부 갱폼 인양 및 설치",
                                 height=80, key=f"{key_prefix}wp")

    # 선택적 입력 (빈칸 → "없음")
    c7, c8 = st.columns(2)
    prev_issues = c7.text_area("전일 미조치 사항 (없으면 공백)",
                                value=di.get("prev_issues",""),
                                placeholder="없으면 공백으로 두세요",
                                height=70, key=f"{key_prefix}pi")
    nearby      = c8.text_area("주변 구역 간섭 공정 (없으면 공백)",
                                value=di.get("nearby_interference",""),
                                placeholder="없으면 공백으로 두세요",
                                height=70, key=f"{key_prefix}nb")
    new_workers = st.text_input("신규 인원 (없으면 공백)",
                                 value=di.get("new_workers",""),
                                 placeholder="없으면 공백으로 두세요",
                                 key=f"{key_prefix}nw")

    # 날씨
    st.markdown("#### 🌤️ 날씨 데이터")
    weather = {}
    if st.toggle("기상청 자동 추출 (API 키 필요)", value=False, key=f"{key_prefix}wt"):
        with st.spinner("날씨 정보 가져오는 중..."):
            weather = fetch_weather(st.session_state.project.get("address","서울"),
                                    d.strftime("%Y%m%d"))
        if weather.get("available"):
            wc1,wc2,wc3 = st.columns(3)
            wc1.metric("평균 기온", weather["temp_avg"])
            wc1.metric("최고 기온", weather["temp_max"])
            wc2.metric("평균 습도", weather["humidity"])
            wc2.metric("평균 풍속", weather["wind_speed"])
            wc3.metric("최고 풍속", weather["wind_max"])
            wc3.metric("최고점 시간", weather["peak_time"])
        else:
            st.warning(weather.get("message","날씨 정보를 가져올 수 없습니다."))
            weather = _manual_weather(key_prefix)
    else:
        weather = _manual_weather(key_prefix)

    missing = [n for n,v in [("관리자 이름",manager),("작업 위치",location),
                               ("인원 현황",workers),("진행 공정",work_process)] if not v]

    return {
        "date":    d.strftime("%Y-%m-%d"),
        "date_c":  d.strftime("%Y%m%d"),
        "manager": manager, "workers": workers, "equipment": equipment,
        "work_time": work_time, "location": location, "env": env,
        "materials": materials, "weather": weather,
        "work_process": work_process,
        "prev_issues":         prev_issues.strip() or "없음",
        "nearby_interference": nearby.strip()      or "없음",
        "new_workers":         new_workers.strip() or "없음",
        "missing": missing,
    }


def _manual_weather(prefix="") -> dict:
    c1,c2,c3 = st.columns(3)
    return {
        "available":  True,
        "temp_avg":   c1.text_input("평균 기온",   placeholder="예: 23.5°C", key=f"{prefix}wa"),
        "temp_max":   c1.text_input("최고 기온",   placeholder="예: 28°C",   key=f"{prefix}wb"),
        "humidity":   c2.text_input("평균 습도",   placeholder="예: 65%",    key=f"{prefix}wc"),
        "wind_speed": c2.text_input("평균 풍속",   placeholder="예: 3.2m/s", key=f"{prefix}wd"),
        "wind_max":   c3.text_input("최고 풍속",   placeholder="예: 12m/s",  key=f"{prefix}we"),
        "peak_time":  c3.text_input("최고점 시간", placeholder="예: 14:00",  key=f"{prefix}wf"),
    }


# ══════════════════════════════════════════════════════════════
# 공통: 법규 선택 UI
# ══════════════════════════════════════════════════════════════
def law_selection_ui(query: str) -> list[str]:
    if not st.session_state.law_candidates:
        with st.spinner("관련 법령 후보 검색 중..."):
            st.session_state.law_candidates = get_law_candidates(query)
    candidates = st.session_state.law_candidates
    if not candidates:
        st.info("관련 법령 후보를 찾지 못했습니다. DB 전체 검색 결과를 사용합니다.")
        return []
    st.markdown("#### ⚖️ 적용할 법령 선택 (복수 선택 가능)")
    selected = []
    for law in candidates:
        col_chk, col_txt = st.columns([0.07, 0.93])
        checked = col_chk.checkbox("", key=f"lc_{law['id']}")
        col_txt.markdown(f"""<div class='law-card'>
<b>[{law['name']} {law['article']}]</b> {law.get('title','')}<br>
<small>{law.get('summary','')}</small></div>""", unsafe_allow_html=True)
        if checked:
            selected.append(f"[{law['name']} {law['article']}] {law.get('title','')} — {law.get('summary','')}")
    return selected


# ══════════════════════════════════════════════════════════════
# 공통: 보고서 확인·수정 → PDF 저장
# ══════════════════════════════════════════════════════════════
def report_review_ui(content: str) -> tuple[bool, str]:
    st.markdown("### 📄 보고서 확인 및 수정")
    st.markdown("""<div class='info-box'>
✏️ 내용을 검토하고 필요한 부분을 수정한 후 PDF로 저장하세요.</div>""",
                unsafe_allow_html=True)
    edited = st.text_area("보고서 내용 (직접 수정 가능)",
                           value=content, height=500, key="edit_area")
    c1,c2 = st.columns(2)
    save  = c1.button("📥 PDF로 저장", type="primary", use_container_width=True)
    retry = c2.button("🔄 다시 생성",  use_container_width=True)
    if retry:
        st.session_state.report_content = ""
        st.session_state.selected_laws  = []
        st.session_state.law_candidates = []
        st.session_state.daily_input    = {}
        st.rerun()
    return save, edited


def _save_to_zone(zone, rtype, label, path, content, report_date):
    if zone not in st.session_state.zone_data:
        st.session_state.zone_data[zone] = {"chat":[],"reports":[]}
    import uuid
    st.session_state.zone_data[zone]["reports"].append({
        "id":      str(uuid.uuid4())[:8],
        "type":    rtype,
        "label":   label,
        "date":    report_date,
        "path":    path,
        "content": content,
    })
    st.session_state.report_content = ""


# ══════════════════════════════════════════════════════════════
# 페이지: 기능 화면
# ══════════════════════════════════════════════════════════════
def page_feature():
    feat     = st.session_state.feature
    zone     = st.session_state.zones[st.session_state.cur_zone]
    proj     = st.session_state.project
    save_dir = st.session_state.pdf_save_dir

    # ── 기능 1: 법규 검색 ─────────────────────────────────────
    if feat == "law":
        st.markdown(f"## 💬 법규 검색 — {zone}")
        zd = st.session_state.zone_data.get(zone, {"chat":[]})
        for msg in zd.get("chat",[]):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if q := st.chat_input("법령 관련 질문을 입력하세요..."):
            with st.chat_message("user"):   st.markdown(q)
            with st.chat_message("assistant"):
                with st.spinner("법령 검색 중..."):
                    r = law_search(q)
                st.markdown(r["answer"])
                if r["count"]: st.caption(f"📄 참조 청크: {r['count']}개")
            if zone not in st.session_state.zone_data:
                st.session_state.zone_data[zone] = {"chat":[],"reports":[]}
            st.session_state.zone_data[zone]["chat"] += [
                {"role":"user","content":q},
                {"role":"assistant","content":r["answer"]}]

    # ── 기능 2: 일일 안전일지 ──────────────────────────────────
    elif feat == "daily":
        st.markdown(f"## 📋 일일 안전일지 — {zone}")
        if not st.session_state.report_content:
            daily = daily_form("dl_")
            # 입력값 임시 저장 (현장 정보 수정 후 복원용)
            st.session_state.daily_input = daily

            if daily["missing"]:
                st.markdown(f"""<div class='warn-box'>
⚠️ 아래 항목을 입력해 주세요:<br>
{'<br>'.join(f'• <b>{m}</b> 정보가 부족합니다.' for m in daily['missing'])}
</div>""", unsafe_allow_html=True)

            if daily["work_process"]:
                st.markdown("---")
                sel = law_selection_ui(f"{daily['work_process']} {daily['location']}")
                st.session_state.selected_laws = sel

            if st.button("📝 안전일지 생성", type="primary",
                          disabled=bool(daily["missing"]), use_container_width=True):
                with st.spinner("AI가 안전일지를 작성 중입니다..."):
                    content = generate_daily_log(daily, st.session_state.selected_laws)
                st.session_state.report_content = content
                st.rerun()
        else:
            daily = st.session_state.daily_input
            save, edited = report_review_ui(st.session_state.report_content)
            if save:
                with st.spinner("PDF 저장 중..."):
                    path = save_daily_log_pdf(
                        daily, edited,
                        proj["name"], save_dir
                    )
                st.markdown(f'<div class="ok-box">✅ PDF 저장 완료: <b>{path}</b></div>',
                            unsafe_allow_html=True)
                _save_to_zone(zone,"daily","📋 일일 안전일지",
                              path, edited, daily["date"])

    # ── 기능 3: 체크리스트 ─────────────────────────────────────
    elif feat == "checklist":
        st.markdown(f"## ✅ 안전 점검 체크리스트 — {zone}")
        if not st.session_state.report_content:
            daily = daily_form("cl_")
            st.session_state.daily_input = daily

            if daily["missing"]:
                st.markdown(f"""<div class='warn-box'>
⚠️ 아래 항목을 입력해 주세요:<br>
{'<br>'.join(f'• <b>{m}</b> 정보가 부족합니다.' for m in daily['missing'])}
</div>""", unsafe_allow_html=True)

            if daily["work_process"]:
                st.markdown("---")
                sel = law_selection_ui(f"{daily['work_process']} {daily['location']} 점검")
                st.session_state.selected_laws = sel

            if st.button("✅ 체크리스트 생성", type="primary",
                          disabled=bool(daily["missing"]), use_container_width=True):
                with st.spinner("AI가 체크리스트를 생성 중입니다..."):
                    content = generate_checklist(daily, st.session_state.selected_laws)
                st.session_state.report_content = content
                st.rerun()
        else:
            daily = st.session_state.daily_input
            save, edited = report_review_ui(st.session_state.report_content)
            if save:
                with st.spinner("PDF 저장 중..."):
                    path = save_checklist_pdf(edited, daily["date_c"],
                                              proj["name"], save_dir)
                st.markdown(f'<div class="ok-box">✅ PDF 저장 완료: <b>{path}</b></div>',
                            unsafe_allow_html=True)
                _save_to_zone(zone,"checklist","✅ 안전 체크리스트",
                              path, edited, daily["date"])

    # ── 기능 4: 사고 보고서 ────────────────────────────────────
    elif feat == "accident":
        st.markdown(f"## 🚨 사고 보고서 — {zone}")
        if not st.session_state.report_content:
            st.markdown("### 📝 사고 정보 입력")
            acc = st.session_state.accident_input  # 이전 입력 유지

            with st.expander("1️⃣ 기본 정보", expanded=True):
                c1,c2 = st.columns(2)
                wd    = c1.date_input("작성일자", value=date.today())
                pname = c2.text_input("현장명", value=proj["name"])
                c3,c4 = st.columns(2)
                wpos  = c3.text_input("작성자 직위", value=acc.get("writer_position",""),
                                       placeholder="예: 안전관리자")
                wname = c4.text_input("작성자 성명", value=acc.get("writer_name",""))

            with st.expander("2️⃣ 안전관리 책임자", expanded=True):
                c1,c2,c3 = st.columns(3)
                sm  = c1.text_input("현장소장", value=acc.get("site_manager",""))
                cm  = c2.text_input("공사과장", value=acc.get("const_manager",""))
                eng = c3.text_input("담당기사",  value=acc.get("engineer",""))

            with st.expander("3️⃣ 재해자 정보", expanded=True):
                c1,c2 = st.columns(2)
                sub  = c1.text_input("협력업체명", value=acc.get("subcontractor",""))
                wt   = c2.text_input("공사종류",   value=acc.get("work_type",""))
                c3,c4,c5 = st.columns(3)
                vn   = c3.text_input("재해자 성명", value=acc.get("victim_name",""))
                vj   = c4.text_input("직종",        value=acc.get("victim_job",""))
                hd   = c5.text_input("채용일",      value=acc.get("hire_date",""),
                                      placeholder="예: 2025-01-15")

            with st.expander("4️⃣ 사고 발생 정보", expanded=True):
                c1,c2 = st.columns(2)
                # 사고 발생 일시: 달력 + 시간 입력
                try:
                    adt_date_default = datetime.strptime(
                        acc.get("accident_date",""), "%Y-%m-%d").date()
                except:
                    adt_date_default = date.today()
                adt_date = c1.date_input("사고 발생 일자", value=adt_date_default)
                hours_a = [f"{h:02d}" for h in range(0, 24)]
                mins_a  = ["00", "10", "20", "30", "40", "50"]
                tc1, tc2 = c1.columns(2)
                saved_h = acc.get("accident_time","14:00").split(":")[0] if acc.get("accident_time") else "14"
                saved_m = acc.get("accident_time","14:00").split(":")[1] if acc.get("accident_time") and ":" in acc.get("accident_time","") else "00"
                adt_h   = tc1.selectbox("사고 시", hours_a,
                           index=hours_a.index(saved_h) if saved_h in hours_a else 14,
                           key="adt_h")
                adt_m   = tc2.selectbox("사고 분", mins_a,
                           index=mins_a.index(saved_m) if saved_m in mins_a else 0,
                           key="adt_m")
                adt_time = f"{adt_h}:{adt_m}"
                loc      = c2.text_input("작업 장소", value=acc.get("location",""))
                cobj     = c2.text_input("기인물",    value=acc.get("cause_object",""),
                                          placeholder="예: 갱폼")
                atype    = c1.selectbox("발생 형태",
                    ["추락","낙하","감전","협착","충돌","화재·폭발","기타"])
                c5,c6 = st.columns(2)
                ip   = c5.text_input("상해 부위", value=acc.get("injury_part",""),
                                      placeholder="예: 우측 하지")
                it_  = c6.text_input("상해 종류", value=acc.get("injury_type",""),
                                      placeholder="예: 골절")
                ov   = st.text_area("재해 발생 개요 *",
                                     value=acc.get("overview",""), height=100)
                dc   = st.text_area("사고 직접 원인 *",
                                     value=acc.get("direct_cause",""), height=80)
                wp   = st.text_area("작업 내용 및 과정 *",
                                     value=acc.get("work_process",""), height=80)

            new_acc = {
                "write_date": wd.strftime("%Y-%m-%d"),
                "project_name": pname,
                "writer_position": wpos, "writer_name": wname,
                "site_manager": sm, "const_manager": cm, "engineer": eng,
                "subcontractor": sub, "work_type": wt,
                "victim_name": vn, "victim_job": vj, "hire_date": hd,
                "accident_datetime": f"{adt_date.strftime('%Y-%m-%d')} {adt_time}",
                "accident_date": adt_date.strftime("%Y-%m-%d"),
                "accident_time": adt_time,
                "location": loc, "cause_object": cobj,
                "accident_type": atype,
                "injury_part": ip, "injury_type": it_,
                "overview": ov, "direct_cause": dc, "work_process": wp,
            }
            st.session_state.accident_input = new_acc

            if atype and loc:
                st.markdown("---")
                sel = law_selection_ui(f"{atype} {loc} 산업재해")
                st.session_state.selected_laws = sel

            missing = [k for k in ["overview","direct_cause","work_process"]
                       if not new_acc.get(k)]
            if missing:
                st.markdown("""<div class='warn-box'>
⚠️ <b>재해 발생 개요</b>, <b>사고 직접 원인</b>, <b>작업 내용 및 과정</b>은 필수입니다.
</div>""", unsafe_allow_html=True)

            if st.button("🚨 사고 보고서 생성", type="primary",
                          disabled=bool(missing), use_container_width=True):
                with st.spinner("AI가 보고서를 작성 중입니다..."):
                    content = generate_accident_report(
                        new_acc, st.session_state.selected_laws)
                st.session_state.report_content = content
                st.rerun()

        else:
            acc  = st.session_state.accident_input
            save, edited = report_review_ui(st.session_state.report_content)
            if save:
                date_c = acc.get("write_date","").replace("-","")
                with st.spinner("PDF 저장 중..."):
                    path = save_accident_report_pdf(edited, date_c,
                                                     proj["name"], save_dir)
                st.markdown(f'<div class="ok-box">✅ PDF 저장 완료: <b>{path}</b></div>',
                            unsafe_allow_html=True)
                _save_to_zone(zone,"accident","🚨 사고 보고서",
                              path, edited, acc.get("write_date",""))


# ══════════════════════════════════════════════════════════════
# 라우터
# ══════════════════════════════════════════════════════════════
if   st.session_state.page == "setup":   page_setup()
elif st.session_state.page == "main":    page_main()
elif st.session_state.page == "feature": page_feature()