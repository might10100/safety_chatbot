"""
app.py — 건설 현장 안전관리 AI v2
페이지: 랜딩 → 메인보드 → 구역보드 → (데일리입력 / 보고서 / 체크리스트 / 사고보고서 / 챗봇)
"""
import streamlit as st
from datetime import date, datetime, timedelta
import uuid, os

from chain_search import (load_resources, law_search, get_law_candidates,
                           generate_daily_log, generate_checklist,
                           generate_accident_report)
from weather import fetch_weather
from pdf_utils import save_daily_log_pdf, save_checklist_pdf
from accident_form import save_accident_form_pdf

st.set_page_config(page_title="건설 현장 안전관리 AI", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.title{font-size:2rem;font-weight:900;color:#1a1a2e;}
.sub{font-size:.9rem;color:#888;margin-bottom:1rem;}
.card{background:#f8f9ff;border-radius:12px;padding:1rem;border-left:5px solid #4361ee;margin-bottom:.7rem;}
.zone-card{background:#fff;border-radius:12px;padding:1.2rem;border:2px solid #dde3ff;
           margin-bottom:.5rem;cursor:pointer;transition:.2s;}
.warn{background:#fff0f0;border-radius:8px;padding:.8rem;border-left:4px solid #e74c3c;margin:.4rem 0;}
.info{background:#e3f2fd;border-radius:8px;padding:.8rem;border-left:4px solid #2196f3;margin:.4rem 0;}
.ok{background:#e8f5e9;border-radius:8px;padding:.8rem;border-left:4px solid #4caf50;margin:.4rem 0;}
.law-card{background:#fffde7;border-radius:8px;padding:.7rem;border:1px solid #ffc107;margin:.4rem 0;}
</style>""", unsafe_allow_html=True)

# ── 대한민국 시/군/구 ─────────────────────────────────────────
REGIONS = {
    "서울특별시":["강남구","강동구","강북구","강서구","관악구","광진구","구로구","금천구","노원구","도봉구","동대문구","동작구","마포구","서대문구","서초구","성동구","성북구","송파구","양천구","영등포구","용산구","은평구","종로구","중구","중랑구"],
    "부산광역시":["강서구","금정구","기장군","남구","동구","동래구","부산진구","북구","사상구","사하구","서구","수영구","연제구","영도구","중구","해운대구"],
    "대구광역시":["남구","달서구","달성군","동구","북구","서구","수성구","중구"],
    "인천광역시":["강화군","계양구","남동구","동구","미추홀구","부평구","서구","연수구","옹진군","중구"],
    "광주광역시":["광산구","남구","동구","북구","서구"],
    "대전광역시":["대덕구","동구","서구","유성구","중구"],
    "울산광역시":["남구","동구","북구","울주군","중구"],
    "세종특별자치시":["세종시"],
    "경기도":["가평군","고양시 덕양구","고양시 일산동구","고양시 일산서구","과천시","광명시","광주시","구리시","군포시","김포시","남양주시","동두천시","부천시","성남시 분당구","성남시 수정구","성남시 중원구","수원시 권선구","수원시 영통구","수원시 장안구","수원시 팔달구","시흥시","안산시 단원구","안산시 상록구","안성시","안양시 동안구","안양시 만안구","양주시","양평군","여주시","연천군","오산시","용인시 기흥구","용인시 수지구","용인시 처인구","의왕시","의정부시","이천시","파주시","평택시","포천시","하남시","화성시"],
    "강원도":["강릉시","고성군","동해시","삼척시","속초시","양구군","양양군","영월군","원주시","인제군","정선군","철원군","춘천시","태백시","평창군","홍천군","화천군","횡성군"],
    "충청북도":["괴산군","단양군","보은군","옥천군","음성군","제천시","진천군","청주시 상당구","청주시 서원구","청주시 청원구","청주시 흥덕구","충주시"],
    "충청남도":["계룡시","공주시","금산군","논산시","당진시","보령시","부여군","서산시","서천군","아산시","예산군","천안시 동남구","천안시 서북구","청양군","태안군","홍성군"],
    "전라북도":["고창군","군산시","김제시","남원시","무주군","부안군","순창군","완주군","익산시","임실군","장수군","전주시 덕진구","전주시 완산구","정읍시","진안군"],
    "전라남도":["강진군","고흥군","곡성군","광양시","구례군","나주시","담양군","목포시","무안군","보성군","순천시","신안군","여수시","영광군","영암군","완도군","장성군","장흥군","진도군","함평군","해남군","화순군"],
    "경상북도":["경산시","경주시","고령군","구미시","군위군","김천시","문경시","봉화군","상주시","성주군","안동시","영덕군","영양군","영주시","영천시","예천군","울릉군","울진군","의성군","청도군","청송군","칠곡군","포항시 남구","포항시 북구"],
    "경상남도":["거제시","거창군","고성군","김해시","남해군","밀양시","사천시","산청군","양산시","의령군","진주시","창녕군","창원시 마산합포구","창원시 마산회원구","창원시 성산구","창원시 의창구","창원시 진해구","통영시","하동군","함안군","함양군","합천군"],
    "제주특별자치도":["서귀포시","제주시"],
}

EQUIPMENT_TYPES = ["타워크레인","이동식크레인","굴착기","불도저","지게차",
                   "덤프트럭","콘크리트펌프카","항타기","롤러","고소작업차"]

# ── Session State 초기화 ──────────────────────────────────────
DEFAULTS = {
    "page":"landing","projects":{},"archive":{},"cur_proj_id":None,"cur_zone":None,
    "zone_data":{},"feature":None,"law_candidates":[],"selected_laws":[],
    "report_content":"","daily_input":{},"accident_input":{},"pdf_save_dir":"",
    "checklist_items":[],"show_new_proj":False,
    "region_sel":"서울특별시","district_sel":"강남구",
}
for k,v in DEFAULTS.items():
    if k not in st.session_state: st.session_state[k]=v

def pid(): return st.session_state.cur_proj_id
def proj(): return st.session_state.projects.get(pid(),{})
def zone(): return st.session_state.cur_zone
def zdata():
    p,z=pid(),zone()
    if p and z: return st.session_state.zone_data.get(p,{}).get(z,{"chat":[],"reports":[],"accidents":[],"daily_history":[]})
    return {}
def ensure_zd(p,z):
    if p not in st.session_state.zone_data: st.session_state.zone_data[p]={}
    if z not in st.session_state.zone_data[p]:
        st.session_state.zone_data[p][z]={"chat":[],"reports":[],"accidents":[],"daily_history":[]}
def go(page,**kw):
    st.session_state.page=page
    for k,v in kw.items(): st.session_state[k]=v
    st.rerun()

# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
def _pick_folder():
    """tkinter로 폴더 선택 다이얼로그 열기"""
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    folder = filedialog.askdirectory(title="PDF 저장 폴더 선택")
    root.destroy()
    return folder

def sidebar():
    page = st.session_state.page
    if page in ("landing","main_board","edit_project"): return
    p,z = proj(),zone()
    with st.sidebar:
        st.markdown(f"## 🏗️ {p.get('name','')}")
        if z: st.markdown(f"📍 **{z}** 구역")
        st.divider()

        # 항상 표시되는 기능 버튼 3개
        st.markdown("**🛠️ 기능**")
        if st.button("💬 법규 검색 챗봇",
                     type="primary" if page=="chatbot" else "secondary",
                     use_container_width=True):
            go("chatbot")
        if z:
            if st.button("📝 데일리 입력",
                         type="primary" if page=="daily_input" else "secondary",
                         use_container_width=True):
                go("daily_input")
            if st.button("🚨 사고 보고서",
                         type="primary" if page=="accident_form" else "secondary",
                         use_container_width=True):
                go("accident_form", accident_input={})

        st.divider()

        # 이전으로 / 구역보드로 버튼
        back_page = {
            "gen_daily_log": "daily_input",
            "gen_checklist": "daily_input",
            "accident_form": "zone_board",
            "chatbot":       "zone_board",
            "daily_input":   "zone_board",
            "zone_board":    "main_board",
        }.get(page)
        if back_page:
            label = {
                "daily_input": "← 데일리 입력으로",
                "zone_board":  "← 구역 보드로",
                "main_board":  "← 메인보드로",
            }.get(back_page, "← 이전으로")
            if st.button(label, use_container_width=True):
                go(back_page)

        if z and st.button("🏠 메인보드", use_container_width=True):
            go("main_board", cur_zone=None)

        st.divider()

        # PDF 저장 경로 선택
        st.markdown("**📁 PDF 저장 경로**")
        cur_dir = st.session_state.pdf_save_dir

        # 빠른 선택 버튼
        import os
        home = os.path.expanduser("~")
        quick_paths = {
            "🖥️ 바탕화면": os.path.join(home, "Desktop"),
            "📂 다운로드":  os.path.join(home, "Downloads"),
            "📄 문서":      os.path.join(home, "Documents"),
        }
        cols_q = st.columns(3)
        for i, (label, path) in enumerate(quick_paths.items()):
            with cols_q[i]:
                is_cur = cur_dir == path
                if st.button(label, key=f"qp_{i}",
                              type="primary" if is_cur else "secondary",
                              use_container_width=True):
                    st.session_state.pdf_save_dir = path
                    st.rerun()

        if st.button("📁 폴더 직접 선택", use_container_width=True):
            try:
                folder = _pick_folder()
                if folder:
                    st.session_state.pdf_save_dir = folder
                    st.rerun()
            except Exception:
                st.info("터미널에서 경로를 직접 입력해 주세요.")

        if cur_dir:
            st.caption(f"저장 위치: {cur_dir}")
        else:
            st.caption("저장 위치: 바탕화면 (기본값)")

# ══════════════════════════════════════════════════════════════
# 위치 선택기
# ══════════════════════════════════════════════════════════════
def location_selector(key_prefix=""):
    regions = list(REGIONS.keys())
    sel_region = st.selectbox("광역시/도 *", regions,
        index=regions.index(st.session_state.region_sel) if st.session_state.region_sel in regions else 0,
        key=f"{key_prefix}region")
    st.session_state.region_sel = sel_region
    districts = REGIONS[sel_region]
    sel_dist = st.selectbox("시/군/구 *", districts,
        index=districts.index(st.session_state.district_sel) if st.session_state.district_sel in districts else 0,
        key=f"{key_prefix}district")
    st.session_state.district_sel = sel_dist
    detail = st.text_input("상세 주소 (선택)", placeholder="예: 역삼동 123-4", key=f"{key_prefix}detail")
    full_addr = f"{sel_region} {sel_dist} {detail}".strip()
    return full_addr, sel_region, sel_dist

# ══════════════════════════════════════════════════════════════
# 페이지 1: 랜딩
# ══════════════════════════════════════════════════════════════
def page_landing():
    st.markdown('<p class="title">🏗️ 건설 현장 안전관리 AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub">관리할 공사현장을 선택하거나 새로 등록하세요.</p>', unsafe_allow_html=True)

    projects = st.session_state.projects
    archive  = st.session_state.archive

    if projects:
        st.markdown("### 📂 저장된 공사현장")
        for pid_,p_ in list(projects.items()):
            c1,c2 = st.columns([.85,.15])
            with c1:
                if st.button(f"**{p_['name']}**\n\n📍 {p_.get('address','')}  |  📅 {p_.get('period_start','')} ~ {p_.get('period_end','')}",
                             key=f"p_{pid_}", use_container_width=True):
                    st.session_state.cur_proj_id = pid_
                    with st.spinner("AI 모델 로딩 중..."): load_resources()
                    go("main_board")
            with c2:
                if st.button("🗑️", key=f"dp_{pid_}", help="삭제"):
                    # 아카이브로 이동
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.session_state.archive[ts] = {"project":p_, "zone_data": st.session_state.zone_data.get(pid_,{})}
                    del st.session_state.projects[pid_]
                    if pid_ in st.session_state.zone_data: del st.session_state.zone_data[pid_]
                    st.rerun()
        st.markdown("---")

    # 아카이브 보기
    if archive:
        with st.expander(f"📦 이전 현장 기록 ({len(archive)}건)"):
            for ts_, arc in archive.items():
                p_ = arc.get("project",{})
                st.markdown(f"""<div class='card'>
<b>{p_.get('name','')}</b> — {ts_}<br>
<small>📍 {p_.get('address','')} | {p_.get('period_start','')} ~ {p_.get('period_end','')}</small>
</div>""", unsafe_allow_html=True)

    # 신규 등록
    if projects:
        if st.button("➕ 새 공사현장 등록", use_container_width=False):
            st.session_state.show_new_proj = not st.session_state.show_new_proj
            st.rerun()
        show = st.session_state.show_new_proj
    else:
        show = True
        st.markdown("### ➕ 공사현장 정보 입력")

    if show:
        name = st.text_input("시공명 *", placeholder="예: 강남 OO아파트 신축공사")
        st.markdown("**현장 위치 ***")
        c1,c2 = st.columns(2)
        with c1:
            full_addr, sel_region, sel_dist = location_selector("new_")
        with c2:
            st.markdown("**시공기간 ***")
            p_start = st.date_input("착공일", value=date.today(), key="new_ps")
            p_end   = st.date_input("준공일", value=date.today(), key="new_pe")

        st.markdown("**📍 구역 구획화**")
        zone_count = st.number_input("구역 수", min_value=1, max_value=20, value=3, step=1)
        cols = st.columns(min(int(zone_count),4))
        zone_names = []
        for i in range(int(zone_count)):
            with cols[i%4]:
                z_ = st.text_input(f"구역 {i+1}", value=f"구역{i+1}", key=f"nz{i}")
                zone_names.append(z_.strip() or f"구역{i+1}")

        if st.button("✅ 현장 등록 및 시작", type="primary", use_container_width=True):
            if not name:
                st.error("시공명은 필수입니다.")
                return
            new_pid = str(uuid.uuid4())[:8]
            st.session_state.projects[new_pid] = {
                "name":name, "address":full_addr,
                "region":sel_region, "district":sel_dist,
                "period_start":p_start.strftime("%Y-%m-%d"),
                "period_end":  p_end.strftime("%Y-%m-%d"),
                "zones":zone_names,
            }
            for z_ in zone_names: ensure_zd(new_pid, z_)
            st.session_state.cur_proj_id   = new_pid
            st.session_state.show_new_proj = False
            with st.spinner("AI 모델 로딩 중..."): load_resources()
            go("main_board")

# ══════════════════════════════════════════════════════════════
# 페이지 2: 메인보드
# ══════════════════════════════════════════════════════════════
def page_main_board():
    p = proj()
    st.markdown(f'<p class="title">🏗️ {p.get("name","")}</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub">📍 {p.get("address","")}  |  📅 {p.get("period_start","")} ~ {p.get("period_end","")}</p>', unsafe_allow_html=True)

    # 현장 정보 변경 버튼
    c_info, c_chat = st.columns([.8,.2])
    with c_info:
        st.markdown(f"""<div class='info'>
📍 위치: {p.get('address','')} &nbsp;|&nbsp;
📅 기간: {p.get('period_start','')} ~ {p.get('period_end','')}
</div>""", unsafe_allow_html=True)
    with c_chat:
        if st.button("⚙️ 현장 정보 변경", use_container_width=True):
            go("edit_project")
        if st.button("💬 법규 검색", use_container_width=True):
            go("chatbot")

    st.markdown("---")
    st.markdown("### 📍 구역 현황")
    st.markdown("구역을 클릭하면 해당 구역 보드로 이동합니다.")

    zones = p.get("zones",[])
    if not zones:
        st.info("등록된 구역이 없습니다.")
        return

    cols = st.columns(min(len(zones), 3))
    for i, z_ in enumerate(zones):
        with cols[i%3]:
            zd_ = st.session_state.zone_data.get(pid(),{}).get(z_,{})
            acc_cnt  = len(zd_.get("accidents",[]))
            rep_cnt  = len(zd_.get("reports",[]))
            chat_cnt = len(zd_.get("chat",[])) // 2

            # 사고 있으면 빨간 강조
            border = "#e74c3c" if acc_cnt > 0 else "#4361ee"
            st.markdown(f"""<div style='background:#fff;border-radius:12px;padding:1rem;
border:2px solid {border};margin-bottom:.5rem;'>
<b style='font-size:1.1rem'>{z_}</b><br>
🚨 사고 {acc_cnt}건 &nbsp;|&nbsp; 📋 보고서 {rep_cnt}건 &nbsp;|&nbsp; 💬 검색 {chat_cnt}건
</div>""", unsafe_allow_html=True)
            if st.button(f"→ {z_} 보드", key=f"goto_{i}", use_container_width=True):
                st.session_state.cur_zone = z_
                ensure_zd(pid(), z_)
                go("zone_board")

# ══════════════════════════════════════════════════════════════
# 페이지 2-1: 현장 정보 수정
# ══════════════════════════════════════════════════════════════
def page_edit_project():
    p = proj()
    st.markdown("## ⚙️ 현장 정보 수정")

    name = st.text_input("시공명 *", value=p.get("name",""))
    st.markdown("**현장 위치**")
    # 현재 지역 복원
    cur_region = p.get("region","서울특별시")
    cur_dist   = p.get("district","강남구")
    st.session_state.region_sel   = cur_region
    st.session_state.district_sel = cur_dist

    c1,c2 = st.columns(2)
    with c1:
        full_addr, sel_region, sel_dist = location_selector("edit_")
    with c2:
        st.markdown("**시공기간**")
        try: ps_def = datetime.strptime(p.get("period_start",""), "%Y-%m-%d").date()
        except: ps_def = date.today()
        try: pe_def = datetime.strptime(p.get("period_end",""), "%Y-%m-%d").date()
        except: pe_def = date.today()
        p_start = st.date_input("착공일", value=ps_def, key="edit_ps")
        p_end   = st.date_input("준공일", value=pe_def, key="edit_pe")

    st.markdown("**📍 구역 구획화** (변경 시 기존 데이터는 아카이브에 저장됩니다)")
    cur_zones = p.get("zones",[])
    zone_count = st.number_input("구역 수", min_value=1, max_value=20, value=len(cur_zones), step=1)
    cols = st.columns(min(int(zone_count),4))
    new_zones = []
    for i in range(int(zone_count)):
        with cols[i%4]:
            default = cur_zones[i] if i < len(cur_zones) else f"구역{i+1}"
            z_ = st.text_input(f"구역 {i+1}", value=default, key=f"ez{i}")
            new_zones.append(z_.strip() or f"구역{i+1}")

    c1,c2 = st.columns(2)
    with c1:
        if st.button("💾 저장", type="primary", use_container_width=True):
            if not name: st.error("시공명은 필수입니다."); return
            # 구역 변경 시 아카이브
            if set(new_zones) != set(cur_zones):
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.session_state.archive[ts] = {
                    "project": p.copy(),
                    "zone_data": st.session_state.zone_data.get(pid(),{}).copy()
                }
                for z_ in new_zones: ensure_zd(pid(), z_)
            st.session_state.projects[pid()] = {
                **p,
                "name":name, "address":full_addr,
                "region":sel_region, "district":sel_dist,
                "period_start":p_start.strftime("%Y-%m-%d"),
                "period_end":  p_end.strftime("%Y-%m-%d"),
                "zones":new_zones,
            }
            go("main_board")
    with c2:
        if st.button("취소", use_container_width=True): go("main_board")

# ══════════════════════════════════════════════════════════════
# 페이지 3: 구역보드
# ══════════════════════════════════════════════════════════════
def page_zone_board():
    p,z = proj(),zone()
    zd  = zdata()
    rs  = zd.get("reports",[])
    ac  = zd.get("accidents",[])

    st.markdown(f'<p class="title">📍 {z} 구역 보드</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub">{p.get("name","")} | {p.get("address","")}</p>', unsafe_allow_html=True)

    st.markdown("---")

    # 전일 미조치 사항 체크
    prev_unresolved = _get_prev_unresolved()
    if prev_unresolved:
        st.markdown("""<div class='warn'>⚠️ <b>전일 미조치 사항</b> — 이행 여부를 확인하세요.</div>""", unsafe_allow_html=True)
        for i, item in enumerate(prev_unresolved):
            checked = st.checkbox(item, key=f"prev_check_{i}")
            if checked:
                _mark_resolved(item)

    # 통계
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("📋 전체 보고서", len(rs))
    col2.metric("✅ 체크리스트", sum(1 for r in rs if r.get("type")=="checklist"))
    col3.metric("🚨 사고 건수",  len(ac))
    one_week_ago = datetime.now()-timedelta(days=7)
    recent = [r for r in rs if _parse_date(r.get("date","")) >= one_week_ago]
    col4.metric("📅 이번주 보고서", len(recent))

    st.markdown("---")
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**📂 최근 일주일 보고서**")
        if recent:
            for r in reversed(recent[-5:]):
                with st.expander(f"{r.get('label','')} — {r.get('date','')}"):
                    st.text_area("내용", value=r.get("content","(없음)"),
                                 height=200, key=f"rv_{r.get('id','')}",disabled=True)
                    if r.get("path") and os.path.exists(r.get("path","")):
                        st.caption(f"💾 {r['path']}")
        else:
            st.info("최근 7일 내 보고서가 없습니다.")

    with col_r:
        st.markdown("**🚨 사고 기록**")
        if ac:
            for a in reversed(ac[-5:]):
                st.markdown(f"""<div class='warn'>
<b>{a.get('accident_type','')}</b> — {a.get('accident_datetime','')}<br>
<small>장소: {a.get('location','')} | 기인물: {a.get('cause_object','')}</small>
</div>""", unsafe_allow_html=True)
        else:
            st.info("기록된 사고가 없습니다.")

def _get_prev_unresolved():
    """전일 미조치 사항 가져오기"""
    zd = zdata()
    history = zd.get("daily_history",[])
    if not history: return []
    yesterday = (datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
    for h in reversed(history):
        if h.get("date","") <= yesterday:
            items = h.get("prev_issues_items",[])
            return [i for i in items if not i.get("resolved",False) and i.get("text","")]
    return []

def _mark_resolved(text):
    p_,z_ = pid(),zone()
    if not p_ or not z_: return
    history = st.session_state.zone_data.get(p_,{}).get(z_,{}).get("daily_history",[])
    for h in history:
        for item in h.get("prev_issues_items",[]):
            if item.get("text")==text:
                item["resolved"] = True

# ══════════════════════════════════════════════════════════════
# 페이지 4: 데일리 입력
# ══════════════════════════════════════════════════════════════
def page_daily_input():
    p,z = proj(),zone()
    st.markdown(f"## 📝 데일리 입력 — {z}")

    zd = zdata()
    history = zd.get("daily_history",[])

    # 전일 미조치 확인
    prev_unresolved = _get_prev_unresolved()
    carry_over = []
    if prev_unresolved:
        st.markdown("""<div class='warn'>⚠️ <b>전일 미조치 사항</b> — 이행 여부를 확인하고 오늘 보고서에 반영할 항목을 선택하세요.</div>""", unsafe_allow_html=True)
        for i, item in enumerate(prev_unresolved):
            c1_,c2_ = st.columns([.1,.9])
            done = c1_.checkbox("완료", key=f"done_{i}")
            c2_.markdown(f"{'~~'+item['text']+'~~' if done else item['text']}")
            if not done:
                if st.checkbox("오늘 보고서에 반영", key=f"carry_{i}", value=True):
                    carry_over.append(item["text"])
        st.markdown("---")

    # ── 날짜·시간 ──
    c1,c2 = st.columns(2)
    di = st.session_state.daily_input
    try:    d_def = datetime.strptime(di.get("date",""),"%Y-%m-%d").date()
    except: d_def = date.today()
    d = c1.date_input("날짜 *", value=d_def)

    hours=[ f"{h:02d}" for h in range(6,21)]
    mins=["00","30"]
    tc1,tc2,tc3,tc4 = st.columns(4)
    sh=tc1.selectbox("시작 시",hours,index=hours.index("08"),key="sh")
    sm=tc2.selectbox("시작 분",mins,key="sm")
    eh=tc3.selectbox("종료 시",hours,index=hours.index("17"),key="eh")
    em=tc4.selectbox("종료 분",mins,key="em")
    work_time=f"{sh}:{sm} ~ {eh}:{em}"

    manager  = c1.text_input("관리자 이름 *", value=di.get("manager",""),  placeholder="예: 김성균")
    location = c2.text_input("작업 위치 *",   value=di.get("location",""), placeholder="예: A동 12층 외벽")

    c3,c4 = st.columns(2)
    env       = c3.selectbox("작업 환경", ["지상","고소","밀폐","지하","수중","기타"])
    materials = c4.text_input("주요 자재", value=di.get("materials",""), placeholder="예: 철근, 거푸집")
    workers   = st.text_area("인원 현황 (공종별) *", value=di.get("workers",""),
                              placeholder="예: 철근공 10명, 형틀공 5명", height=70)
    wp        = st.text_area("진행 공정 *", value=di.get("work_process",""),
                              placeholder="예: 12층 외부 갱폼 인양 및 설치", height=70)

    # ── 장비 현황 ──
    st.markdown("#### 🚧 장비 현황")
    eq_counts = di.get("equipment_counts", {})
    eq_cols   = st.columns(5)
    for i, eq in enumerate(EQUIPMENT_TYPES):
        with eq_cols[i%5]:
            n = st.number_input(eq, min_value=0, max_value=99,
                                value=int(eq_counts.get(eq,0)), step=1, key=f"eq_{eq}")
            eq_counts[eq] = n
    eq_custom = st.text_input("기타 장비 (직접 입력)", value=di.get("equipment_custom",""),
                               placeholder="예: 특수차량 1대, 발전기 2대")
    # 장비 문자열 생성
    eq_list = [f"{k} {v}대" for k,v in eq_counts.items() if v>0]
    if eq_custom.strip(): eq_list.append(eq_custom.strip())
    equipment_str = ", ".join(eq_list) if eq_list else "없음"

    # ── 미조치/신규 ──
    c7,c8 = st.columns(2)
    # 전일 미조치: carry_over + 직접 입력
    prev_default = "\n".join(carry_over) if carry_over else di.get("prev_issues","")
    prev   = c7.text_area("전일 미조치 사항", value=prev_default, height=70,
                           placeholder="없으면 공백으로 두세요")
    nearby = c8.text_area("주변 구역 간섭", value=di.get("nearby_interference",""),
                           height=70, placeholder="없으면 공백으로 두세요")
    nw     = st.text_input("신규 인원", value=di.get("new_workers",""),
                            placeholder="없으면 공백으로 두세요")

    # ── 날씨 ──
    st.markdown("#### 🌤️ 날씨 데이터")
    weather={}
    if st.toggle("기상청 자동 추출", value=False):
        addr = f"{p.get('region','')} {p.get('district','')}"
        with st.spinner("날씨 정보 가져오는 중..."):
            weather = fetch_weather(addr, d.strftime("%Y%m%d"))
        if weather.get("available"):
            wc1,wc2,wc3=st.columns(3)
            wc1.metric("평균기온",weather["temp_avg"]); wc1.metric("최고기온",weather["temp_max"])
            wc2.metric("평균습도",weather["humidity"]); wc2.metric("평균풍속",weather["wind_speed"])
            wc3.metric("최고풍속",weather["wind_max"]); wc3.metric("최고점시간",weather["peak_time"])
        else:
            st.warning(weather.get("message","")); weather=_mw()
    else:
        weather=_mw()

    missing=[n for n,v in [("관리자 이름",manager),("작업 위치",location),
                             ("인원 현황",workers),("진행 공정",wp)] if not v]
    if missing:
        st.markdown(f"""<div class='warn'>⚠️ 필수 입력: {'  |  '.join(missing)}</div>""", unsafe_allow_html=True)

    # 미조치 항목 파싱 (줄 단위)
    prev_items = [{"text":l.strip(),"resolved":False}
                  for l in prev.split("\n") if l.strip()] if prev.strip() else []

    daily = {
        "date":d.strftime("%Y-%m-%d"), "date_c":d.strftime("%Y%m%d"),
        "manager":manager, "workers":workers, "equipment":equipment_str,
        "equipment_counts":eq_counts, "equipment_custom":eq_custom,
        "work_time":work_time, "location":location, "env":env,
        "materials":materials, "weather":weather, "work_process":wp,
        "prev_issues":         prev.strip()   or "없음",
        "prev_issues_items":   prev_items,
        "nearby_interference": nearby.strip() or "없음",
        "new_workers":         nw.strip()     or "없음",
        "missing":missing,
    }
    st.session_state.daily_input = daily

    st.markdown("---")
    st.markdown("### 이 데이터로 생성할 문서를 선택하세요")
    c1,c2 = st.columns(2)
    with c1:
        if st.button("📋 일일 안전일지 생성", type="primary",
                     disabled=bool(missing), use_container_width=True):
            st.session_state.report_content=""
            st.session_state.selected_laws=[]
            st.session_state.law_candidates=[]
            go("gen_daily_log")
    with c2:
        if st.button("✅ 안전 체크리스트 생성", type="primary",
                     disabled=bool(missing), use_container_width=True):
            st.session_state.report_content=""
            st.session_state.selected_laws=[]
            st.session_state.law_candidates=[]
            go("gen_checklist")

    # 데일리 히스토리 저장 (미조치 추적용)
    if not missing:
        _save_daily_history(daily)


def _mw():
    c1,c2,c3=st.columns(3)
    return {"available":True,
            "temp_avg":  c1.text_input("평균기온",  placeholder="예:23.5°C",key="wa"),
            "temp_max":  c1.text_input("최고기온",  placeholder="예:28°C",  key="wb"),
            "humidity":  c2.text_input("평균습도",  placeholder="예:65%",   key="wc"),
            "wind_speed":c2.text_input("평균풍속",  placeholder="예:3.2m/s",key="wd"),
            "wind_max":  c3.text_input("최고풍속",  placeholder="예:12m/s", key="we"),
            "peak_time": c3.text_input("최고점시간",placeholder="예:14:00", key="wf")}

def _save_daily_history(daily):
    p_,z_=pid(),zone()
    if not p_ or not z_: return
    ensure_zd(p_,z_)
    history=st.session_state.zone_data[p_][z_].get("daily_history",[])
    # 같은 날짜면 덮어쓰기
    for h in history:
        if h.get("date")==daily["date"]:
            h.update(daily); return
    history.append(daily)
    st.session_state.zone_data[p_][z_]["daily_history"]=history

# ══════════════════════════════════════════════════════════════
# 공통: 법규 선택 UI
# ══════════════════════════════════════════════════════════════
def law_ui(query):
    if not st.session_state.law_candidates:
        with st.spinner("관련 법령 후보 검색 중..."):
            st.session_state.law_candidates = get_law_candidates(query)
    candidates = st.session_state.law_candidates
    if not candidates:
        st.info("관련 법령 후보를 찾지 못했습니다. DB 전체 검색 결과를 사용합니다.")
        return []
    st.markdown("#### ⚖️ 적용할 법령 선택 (복수 선택 가능)")
    selected=[]
    for law in candidates:
        c1,c2=st.columns([.07,.93])
        checked=c1.checkbox("선택",key=f"lc_{law['id']}",label_visibility="hidden")
        c2.markdown(f"""<div class='law-card'><b>[{law['name']} {law['article']}]</b> {law.get('title','')}<br>
<small>{law.get('summary','')}</small></div>""",unsafe_allow_html=True)
        if checked:
            selected.append(f"[{law['name']} {law['article']}] {law.get('title','')} — {law.get('summary','')}")
    return selected

def review_ui(content):
    st.markdown("### 📄 보고서 확인 및 수정")
    st.markdown("""<div class='info'>✏️ 내용을 검토하고 수정한 후 PDF로 저장하세요.</div>""",unsafe_allow_html=True)
    edited=st.text_area("내용",value=content,height=450,key="edit_area")
    c1,c2=st.columns(2)
    save=c1.button("📥 PDF로 저장",type="primary",use_container_width=True)
    retry=c2.button("🔄 다시 생성",use_container_width=True)
    if retry:
        st.session_state.report_content=""
        st.session_state.selected_laws=[]
        st.session_state.law_candidates=[]
        st.rerun()
    return save, edited

def save_report(rtype,label,path,content,rdate):
    p_,z_=pid(),zone()
    ensure_zd(p_,z_)
    st.session_state.zone_data[p_][z_]["reports"].append({
        "id":str(uuid.uuid4())[:8],"type":rtype,"label":label,
        "date":rdate,"path":path,"content":content,
    })
    st.session_state.report_content=""

# ══════════════════════════════════════════════════════════════
# 페이지 5: 일일 안전일지 생성
# ══════════════════════════════════════════════════════════════
def page_gen_daily_log():
    daily=st.session_state.daily_input
    st.markdown(f"## 📋 일일 안전일지 — {zone()}")

    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 안전"
        st.markdown("---")
        st.session_state.selected_laws=law_ui(query)
        if st.button("📝 안전일지 생성",type="primary",use_container_width=True):
            with st.spinner("AI가 안전일지를 작성 중입니다..."):
                st.session_state.report_content=generate_daily_log(daily,st.session_state.selected_laws)
            st.rerun()
        if st.button("← 데일리 입력으로",use_container_width=False): go("daily_input")
    else:
        daily=st.session_state.daily_input
        save,edited=review_ui(st.session_state.report_content)
        if save:
            with st.spinner("PDF 저장 중..."):
                path=save_daily_log_pdf(daily,edited,proj()["name"],st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">✅ PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            save_report("daily","📋 일일 안전일지",path,edited,daily["date"])

# ══════════════════════════════════════════════════════════════
# 페이지 6: 안전 체크리스트 생성 (인터랙티브 체크박스)
# ══════════════════════════════════════════════════════════════
def page_gen_checklist():
    daily=st.session_state.daily_input
    st.markdown(f"## ✅ 안전 체크리스트 — {zone()}")

    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 점검"
        st.markdown("---")
        st.session_state.selected_laws=law_ui(query)
        if st.button("✅ 체크리스트 생성",type="primary",use_container_width=True):
            with st.spinner("AI가 체크리스트를 생성 중입니다..."):
                st.session_state.report_content=generate_checklist(daily,st.session_state.selected_laws)
            # 체크박스 항목 파싱
            items=[]
            for line in st.session_state.report_content.split("\n"):
                line=line.strip()
                if line.startswith("□"):
                    items.append({"text":line[1:].strip(),"checked":False,"important":"[!]" in line})
            st.session_state.checklist_items=items
            st.rerun()
        if st.button("← 데일리 입력으로",use_container_width=False): go("daily_input")

    else:
        daily=st.session_state.daily_input
        st.markdown(f"**날짜:** {daily.get('date','')}  |  **공종:** {daily.get('work_process','')}  |  **위치:** {daily.get('location','')}")

        # 전일 미조치 섹션
        prev=daily.get("prev_issues","없음")
        if prev and prev != "없음":
            st.markdown("---")
            st.markdown("#### ⚠️ 전일 미조치 사항")
            for item in prev.split("\n"):
                if item.strip():
                    st.markdown(f"""<div class='warn'>⚠️ {item.strip()}</div>""",unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📋 점검 항목 체크 (완료한 항목에 체크하세요)")

        items=st.session_state.checklist_items
        checked_count=sum(1 for i in items if i["checked"])
        st.markdown(f"**진행:** {checked_count}/{len(items)} 완료")
        st.progress(checked_count/len(items) if items else 0)

        # 원본 텍스트를 섹션별로 표시
        content=st.session_state.report_content
        lines=content.split("\n")
        item_idx=0
        for line in lines:
            s=line.strip()
            if not s: continue
            if s.startswith(("Ⅰ.","Ⅱ.")):
                st.markdown(f"### {s}")
            elif s[:2] in ("1.","2.","3.","4.","5.") and len(s)<25:
                st.markdown(f"**{s}**")
            elif s.startswith("□") and item_idx<len(items):
                item=items[item_idx]
                label=item["text"]
                color="🔴 " if item["important"] else ""
                checked=st.checkbox(f"{color}{label}",
                                    value=item["checked"],
                                    key=f"cl_{item_idx}")
                items[item_idx]["checked"]=checked
                item_idx+=1
            elif any(x in s for x in ["안전관리자","현장소장","작업반장","서명"]):
                st.markdown(s)
            elif s.startswith("[점검"):
                st.markdown(f"---\n**{s}**")
        st.session_state.checklist_items=items

        st.markdown("---")
        # 체크리스트를 텍스트로 변환 후 PDF 저장
        checklist_text="\n".join(
            f"{'☑' if i['checked'] else '□'} {i['text']}"
            for i in items
        )
        c1,c2=st.columns(2)
        with c1:
            if st.button("📥 PDF로 저장",type="primary",use_container_width=True):
                with st.spinner("PDF 저장 중..."):
                    path=save_checklist_pdf(
                        content.replace("□","☑" if True else "□"),
                        daily["date_c"],proj()["name"],st.session_state.pdf_save_dir)
                st.markdown(f'<div class="ok">✅ PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
                save_report("checklist","✅ 안전 체크리스트",path,content,daily["date"])
        with c2:
            if st.button("🔄 다시 생성",use_container_width=True):
                st.session_state.report_content=""
                st.session_state.checklist_items=[]
                st.session_state.selected_laws=[]
                st.session_state.law_candidates=[]
                st.rerun()

# ══════════════════════════════════════════════════════════════
# 페이지 7: 사고 보고서
# ══════════════════════════════════════════════════════════════
def page_accident_form():
    st.markdown(f"## 🚨 사고 보고서 — {zone()}")
    acc=st.session_state.accident_input
    p=proj()

    if not st.session_state.report_content:
        with st.expander("1️⃣ 기본 정보",expanded=True):
            c1,c2=st.columns(2)
            wd   =c1.date_input("작성일자",value=date.today())
            pname=c2.text_input("현장명",value=p.get("name",""))
            c3,c4=st.columns(2)
            wpos=c3.text_input("작성자 직위",value=acc.get("writer_position",""),placeholder="예:안전관리자")
            wname=c4.text_input("작성자 성명",value=acc.get("writer_name",""))
        with st.expander("2️⃣ 안전관리 책임자",expanded=True):
            c1,c2,c3=st.columns(3)
            sm=c1.text_input("현장소장",value=acc.get("site_manager",""))
            cm=c2.text_input("공사과장",value=acc.get("const_manager",""))
            eng=c3.text_input("담당기사",value=acc.get("engineer",""))
        with st.expander("3️⃣ 재해자 정보",expanded=True):
            c1,c2=st.columns(2)
            sub=c1.text_input("협력업체명",value=acc.get("subcontractor",""))
            wt=c2.text_input("공사종류",value=acc.get("work_type",""))
            c3,c4,c5=st.columns(3)
            vn=c3.text_input("재해자 성명",value=acc.get("victim_name",""))
            vj=c4.text_input("직종",value=acc.get("victim_job",""))
            hd=c5.text_input("채용일",value=acc.get("hire_date",""),placeholder="예:2025-01-15")
        with st.expander("4️⃣ 사고 발생 정보",expanded=True):
            c1,c2=st.columns(2)
            try:    adf=datetime.strptime(acc.get("accident_date",""),"%Y-%m-%d").date()
            except: adf=date.today()
            adt_date=c1.date_input("사고 발생 일자",value=adf)
            hours_a=[f"{h:02d}" for h in range(0,24)]
            mins_a=["00","10","20","30","40","50"]
            tc1,tc2=c1.columns(2)
            sh_=acc.get("accident_time","14:00").split(":")[0] if acc.get("accident_time") else "14"
            sm_=acc.get("accident_time","14:00").split(":")[-1] if acc.get("accident_time") else "00"
            adt_h=tc1.selectbox("사고 시",hours_a,index=hours_a.index(sh_) if sh_ in hours_a else 14,key="adt_h")
            adt_m=tc2.selectbox("사고 분",mins_a,index=mins_a.index(sm_) if sm_ in mins_a else 0,key="adt_m")
            adt_time=f"{adt_h}:{adt_m}"
            loc=c2.text_input("작업 장소",value=acc.get("location",""))
            cobj=c2.text_input("기인물",value=acc.get("cause_object",""),placeholder="예:갱폼")
            atype=c1.selectbox("발생 형태",["추락","낙하","감전","협착","충돌","화재·폭발","기타"])
            c5,c6=st.columns(2)
            ip=c5.text_input("상해 부위",value=acc.get("injury_part",""),placeholder="예:우측 하지")
            it_=c6.text_input("상해 종류",value=acc.get("injury_type",""),placeholder="예:골절")
            ov=st.text_area("재해 발생 개요 *",value=acc.get("overview",""),height=100)
            dc=st.text_area("사고 직접 원인 *",value=acc.get("direct_cause",""),height=80)
            wp_=st.text_area("작업 내용 및 과정 *",value=acc.get("work_process",""),height=80)

        new_acc={
            "write_date":wd.strftime("%Y-%m-%d"),"project_name":pname,
            "writer_position":wpos,"writer_name":wname,
            "site_manager":sm,"const_manager":cm,"engineer":eng,
            "subcontractor":sub,"work_type":wt,
            "victim_name":vn,"victim_job":vj,"hire_date":hd,
            "accident_datetime":f"{adt_date.strftime('%Y-%m-%d')} {adt_time}",
            "accident_date":adt_date.strftime("%Y-%m-%d"),"accident_time":adt_time,
            "location":loc,"cause_object":cobj,"accident_type":atype,
            "injury_part":ip,"injury_type":it_,"overview":ov,
            "direct_cause":dc,"work_process":wp_,
        }
        st.session_state.accident_input=new_acc

        if atype and loc:
            st.markdown("---")
            st.session_state.selected_laws=law_ui(f"{atype} {loc} 산업재해")

        missing=[k for k in ["overview","direct_cause","work_process"] if not new_acc.get(k)]
        if missing:
            st.markdown("""<div class='warn'>⚠️ 재해 발생 개요, 사고 직접 원인, 작업 내용 및 과정은 필수입니다.</div>""",unsafe_allow_html=True)

        if st.button("🚨 사고 보고서 생성",type="primary",disabled=bool(missing),use_container_width=True):
            with st.spinner("AI가 보고서를 작성 중입니다..."):
                st.session_state.report_content=generate_accident_report(new_acc,st.session_state.selected_laws)
            st.rerun()

    else:
        acc=st.session_state.accident_input
        save,edited=review_ui(st.session_state.report_content)
        if save:
            with st.spinner("PDF 저장 중..."):
                path=save_accident_form_pdf(acc,edited,st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">✅ PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            # 사고 기록 저장
            p_,z_=pid(),zone()
            ensure_zd(p_,z_)
            st.session_state.zone_data[p_][z_]["accidents"].append(acc)
            st.session_state.report_content=""

# ══════════════════════════════════════════════════════════════
# 페이지 8: 챗봇 (법규 검색)
# ══════════════════════════════════════════════════════════════
def page_chatbot():
    z_=zone() or "전체"
    st.markdown(f"## 💬 법규 검색 챗봇 — {z_}")
    p_=pid()
    if p_ and z_ and z_!="전체":
        ensure_zd(p_,z_)
        chat_history=st.session_state.zone_data[p_][z_]["chat"]
    else:
        if "global_chat" not in st.session_state: st.session_state.global_chat=[]
        chat_history=st.session_state.global_chat

    for msg in chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if q:=st.chat_input("법령 관련 질문을 입력하세요..."):
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("법령 검색 중..."):
                r=law_search(q)
            st.markdown(r["answer"])
            if r["count"]: st.caption(f"📄 참조 청크: {r['count']}개")
        chat_history+=[{"role":"user","content":q},{"role":"assistant","content":r["answer"]}]

def _parse_date(s):
    try: return datetime.strptime(s,"%Y-%m-%d")
    except: return datetime.min

# ══════════════════════════════════════════════════════════════
# 라우터
# ══════════════════════════════════════════════════════════════
sidebar()
page=st.session_state.page
if   page=="landing":          page_landing()
elif page=="main_board":       page_main_board()
elif page=="edit_project":     page_edit_project()
elif page=="zone_board":       page_zone_board()
elif page=="daily_input":      page_daily_input()
elif page=="gen_daily_log":    page_gen_daily_log()
elif page=="gen_checklist":    page_gen_checklist()
elif page=="accident_form":    page_accident_form()
elif page=="chatbot":          page_chatbot()