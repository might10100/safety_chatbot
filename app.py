"""
app.py — 건설 현장 안전관리 AI (최종판)
"""
import streamlit as st
from datetime import date, datetime, timedelta
import uuid, os
import shared_state as SS

from chain_search import (load_resources, law_search, get_law_candidates,
                           generate_daily_log, generate_checklist,
                           generate_accident_report)
from weather import fetch_weather
from pdf_utils import save_daily_log_pdf, save_checklist_pdf, save_accident_report_pdf
from accident_form import save_accident_form_pdf

st.set_page_config(page_title="건설 현장 안전관리 AI", page_icon="🏗️", layout="wide")
st.markdown("""<style>
.title{font-size:1.8rem;font-weight:900;color:#1a1a2e;}
.sub{font-size:.85rem;color:#888;margin-bottom:1rem;}
.card{background:#f8f9ff;border-radius:10px;padding:1rem;border-left:4px solid #4361ee;margin-bottom:.6rem;}
.warn{background:#fff0f0;border-radius:8px;padding:.7rem;border-left:4px solid #e74c3c;margin:.4rem 0;}
.info{background:#e3f2fd;border-radius:8px;padding:.7rem;border-left:4px solid #2196f3;margin:.4rem 0;}
.ok{background:#e8f5e9;border-radius:8px;padding:.7rem;border-left:4px solid #4caf50;margin:.4rem 0;}
.law-card{background:#fffde7;border-radius:8px;padding:.6rem;border:1px solid #ffc107;margin:.3rem 0;}
section[data-testid="stSidebar"] .stButton button{border-radius:6px;}
</style>""", unsafe_allow_html=True)

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
EQUIPMENT_TYPES=["타워크레인","이동식크레인","굴착기","불도저","지게차","덤프트럭","콘크리트펌프카","항타기","롤러","고소작업차"]

# ── Session State 초기화 ──────────────────────────────────────
for k,v in {
    "page":"landing","cur_proj_id":None,"cur_zone":None,
    "feature":None,"law_candidates":[],"selected_laws":[],
    "report_content":"","daily_input":{},"accident_input":{},
    "pdf_save_dir":"","show_new_proj":False,
    "region_sel":"서울특별시","district_sel":"강남구",
}.items():
    if k not in st.session_state: st.session_state[k]=v

# 공유 상태 세션에 반영
def sync():
    """공유 상태 → 세션 동기화"""
    pass

def pid(): return st.session_state.cur_proj_id
def proj(): return SS.get_projects().get(pid(),{})
def zone(): return st.session_state.cur_zone
def zdata():
    p,z=pid(),zone()
    if p and z: return SS.get_zone_data().get(p,{}).get(z,{"chat":[],"reports":[],"accidents":[],"daily_history":[]})
    return {}
def ensure_zd(p,z):
    zd=SS.get_zone_data()
    if p not in zd: zd[p]={}
    if z not in zd[p]: zd[p][z]={"chat":[],"reports":[],"accidents":[],"daily_history":[]}
    SS.set_zone_data(zd)
def go(page,**kw):
    st.session_state.page=page
    for k,v in kw.items(): st.session_state[k]=v
    st.rerun()

# ══════════════════════════════════════════════════════════════
# 사이드바
# ══════════════════════════════════════════════════════════════
def _pick_folder():
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk(); root.withdraw(); root.wm_attributes("-topmost",1)
    folder=filedialog.askdirectory(title="PDF 저장 폴더 선택")
    root.destroy(); return folder

def sidebar():
    page=st.session_state.page
    if page in ("landing","main_board","edit_project"): return
    p,z=proj(),zone()
    with st.sidebar:
        st.markdown(f"**{p.get('name','')}**")
        if z: st.caption(f"{z} 구역")
        st.divider()
        st.markdown("**기능**")
        if st.button("Chatbot", type="primary" if page=="chatbot" else "secondary", use_container_width=True):
            go("chatbot")
        if z:
            if st.button("금일 안전 업무 기록", type="primary" if page=="daily_input" else "secondary", use_container_width=True):
                go("daily_input")
            if st.button("사고 보고서", type="primary" if page=="accident_form" else "secondary", use_container_width=True):
                go("accident_form", accident_input={})
        st.divider()
        back_map={"gen_daily_log":"daily_input","gen_checklist":"daily_input",
                  "accident_form":"zone_board","chatbot":"zone_board",
                  "daily_input":"zone_board","zone_board":"main_board"}
        back=back_map.get(page)
        if back:
            lbl={"daily_input":"← 금일 안전 업무 기록","zone_board":"← 구역 보드","main_board":"← 메인보드"}.get(back,"← 이전")
            if st.button(lbl, use_container_width=True): go(back)
        if z and st.button("메인보드", use_container_width=True): go("main_board",cur_zone=None)
        st.divider()
        st.markdown("**PDF 저장 경로**")
        cur_dir=st.session_state.pdf_save_dir
        home=os.path.expanduser("~")
        qp={"바탕화면":os.path.join(home,"Desktop"),"다운로드":os.path.join(home,"Downloads"),"문서":os.path.join(home,"Documents")}
        c1,c2,c3=st.columns(3)
        for col,(lbl,path) in zip([c1,c2,c3],qp.items()):
            is_cur=cur_dir==path
            if col.button(lbl,key=f"qp_{lbl}",type="primary" if is_cur else "secondary",use_container_width=True):
                st.session_state.pdf_save_dir=path; st.rerun()
        if st.button("폴더 직접 선택", use_container_width=True):
            try:
                f=_pick_folder()
                if f: st.session_state.pdf_save_dir=f; st.rerun()
            except: st.info("경로를 직접 입력해 주세요.")
        if cur_dir: st.caption(f"저장: {os.path.basename(cur_dir)}")
        else: st.caption("저장: 바탕화면 (기본값)")

# ══════════════════════════════════════════════════════════════
# 위치 선택
# ══════════════════════════════════════════════════════════════
def location_selector(key_prefix=""):
    regions=list(REGIONS.keys())
    sel_r=st.selectbox("광역시/도 *",regions,
        index=regions.index(st.session_state.region_sel) if st.session_state.region_sel in regions else 0,
        key=f"{key_prefix}region")
    st.session_state.region_sel=sel_r
    dists=REGIONS[sel_r]
    sel_d=st.selectbox("시/군/구 *",dists,
        index=dists.index(st.session_state.district_sel) if st.session_state.district_sel in dists else 0,
        key=f"{key_prefix}district")
    st.session_state.district_sel=sel_d
    detail=st.text_input("상세 주소 (선택)",placeholder="예: 역삼동 123-4",key=f"{key_prefix}detail")
    return f"{sel_r} {sel_d} {detail}".strip(), sel_r, sel_d

# ══════════════════════════════════════════════════════════════
# 페이지 1: 랜딩
# ══════════════════════════════════════════════════════════════
def page_landing():
    st.markdown('<p class="title">건설 현장 안전관리 AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub">관리할 공사현장을 선택하거나 새로 등록하세요.</p>', unsafe_allow_html=True)
    projects=SS.get_projects()
    archive=SS.get_archive()

    if projects:
        st.markdown("### 저장된 공사현장")
        for pid_,p_ in list(projects.items()):
            c1,c2=st.columns([.85,.15])
            with c1:
                if st.button(f"**{p_['name']}**  |  {p_.get('address','')}  |  {p_.get('period_start','')} ~ {p_.get('period_end','')}",
                             key=f"p_{pid_}",use_container_width=True):
                    st.session_state.cur_proj_id=pid_
                    with st.spinner("AI 모델 로딩 중..."): load_resources()
                    go("main_board")
            with c2:
                if st.button("삭제",key=f"dp_{pid_}"):
                    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
                    arch=SS.get_archive(); arch[ts]={"project":p_,"zone_data":SS.get_zone_data().get(pid_,{})}
                    SS.set_archive(arch)
                    projs=SS.get_projects(); del projs[pid_]; SS.set_projects(projs)
                    st.rerun()
        st.markdown("---")

    if archive:
        with st.expander(f"이전 현장 기록 ({len(archive)}건)"):
            for ts_,arc in archive.items():
                p_=arc.get("project",{})
                st.markdown(f"""<div class='card'><b>{p_.get('name','')}</b> — {ts_}<br>
<small>{p_.get('address','')} | {p_.get('period_start','')} ~ {p_.get('period_end','')}</small></div>""",unsafe_allow_html=True)

    # 신규 등록 버튼
    if projects:
        if st.button("+ 새 공사현장 등록"):
            st.session_state.show_new_proj=not st.session_state.show_new_proj; st.rerun()
        show=st.session_state.show_new_proj
    else:
        show=True; st.markdown("### 공사현장 정보 입력")

    if show:
        name=st.text_input("시공명 *",placeholder="예: 강남 OO아파트 신축공사")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**현장 위치 ***")
            full_addr,sel_r,sel_d=location_selector("new_")
        with c2:
            st.markdown("**시공기간 ***")
            p_start=st.date_input("착공일",value=date.today(),key="new_ps")
            p_end=st.date_input("준공일",value=date.today(),key="new_pe")
        st.markdown("**구역 구획화**")
        zone_count=st.number_input("구역 수",min_value=1,max_value=20,value=3,step=1)
        cols=st.columns(min(int(zone_count),4))
        zone_names=[]
        for i in range(int(zone_count)):
            with cols[i%4]:
                z_=st.text_input(f"구역 {i+1}",value=f"구역{i+1}",key=f"nz{i}")
                zone_names.append(z_.strip() or f"구역{i+1}")
        if st.button("현장 등록 및 시작",type="primary",use_container_width=True):
            if not name: st.error("시공명은 필수입니다."); return
            new_pid=str(uuid.uuid4())[:8]
            projs=SS.get_projects()
            projs[new_pid]={"name":name,"address":full_addr,"region":sel_r,"district":sel_d,
                            "period_start":p_start.strftime("%Y-%m-%d"),"period_end":p_end.strftime("%Y-%m-%d"),
                            "zones":zone_names}
            SS.set_projects(projs)
            for z_ in zone_names: ensure_zd(new_pid,z_)
            st.session_state.cur_proj_id=new_pid; st.session_state.show_new_proj=False
            with st.spinner("AI 모델 로딩 중..."): load_resources()
            go("main_board")

# ══════════════════════════════════════════════════════════════
# 페이지 2: 메인보드
# ══════════════════════════════════════════════════════════════
def page_main_board():
    p=proj()
    st.markdown(f'<p class="title">{p.get("name","")}</p>',unsafe_allow_html=True)
    st.markdown(f'<p class="sub">{p.get("address","")}  |  {p.get("period_start","")} ~ {p.get("period_end","")}</p>',unsafe_allow_html=True)
    c1,c2,c3=st.columns([.5,.25,.25])
    with c2:
        if st.button("현장 정보 변경",use_container_width=True): go("edit_project")
    with c3:
        if st.button("Chatbot",use_container_width=True): go("chatbot")

    st.markdown("---")
    st.markdown("### 구역 현황")
    zones=p.get("zones",[])
    if not zones: st.info("등록된 구역이 없습니다."); return
    cols=st.columns(min(len(zones),3))
    for i,z_ in enumerate(zones):
        with cols[i%3]:
            zd_=SS.get_zone_data().get(pid(),{}).get(z_,{})
            acc_cnt=len(zd_.get("accidents",[])); rep_cnt=len(zd_.get("reports",[]))
            border="#e74c3c" if acc_cnt>0 else "#4361ee"
            st.markdown(f"""<div style='background:#fff;border-radius:10px;padding:1rem;border:2px solid {border};margin-bottom:.5rem;'>
<b style='font-size:1.05rem'>{z_}</b><br>
사고 {acc_cnt}건  |  보고서 {rep_cnt}건</div>""",unsafe_allow_html=True)
            if st.button(f"{z_} 구역으로",key=f"gz_{i}",use_container_width=True):
                st.session_state.cur_zone=z_; ensure_zd(pid(),z_); go("zone_board")

# ══════════════════════════════════════════════════════════════
# 페이지 2-1: 현장 정보 수정
# ══════════════════════════════════════════════════════════════
def page_edit_project():
    p=proj()
    st.markdown("## 현장 정보 수정")
    name=st.text_input("시공명 *",value=p.get("name",""))
    st.session_state.region_sel=p.get("region","서울특별시")
    st.session_state.district_sel=p.get("district","강남구")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**현장 위치**"); full_addr,sel_r,sel_d=location_selector("edit_")
    with c2:
        st.markdown("**시공기간**")
        try: ps=datetime.strptime(p.get("period_start",""),"%Y-%m-%d").date()
        except: ps=date.today()
        try: pe=datetime.strptime(p.get("period_end",""),"%Y-%m-%d").date()
        except: pe=date.today()
        p_start=st.date_input("착공일",value=ps,key="edit_ps")
        p_end=st.date_input("준공일",value=pe,key="edit_pe")
    st.markdown("**구역 구획화** (변경 시 기존 데이터는 아카이브에 저장)")
    cur_zones=p.get("zones",[])
    zone_count=st.number_input("구역 수",min_value=1,max_value=20,value=len(cur_zones),step=1)
    cols=st.columns(min(int(zone_count),4))
    new_zones=[]
    for i in range(int(zone_count)):
        with cols[i%4]:
            def_=cur_zones[i] if i<len(cur_zones) else f"구역{i+1}"
            z_=st.text_input(f"구역 {i+1}",value=def_,key=f"ez{i}")
            new_zones.append(z_.strip() or f"구역{i+1}")
    c1,c2=st.columns(2)
    with c1:
        if st.button("저장",type="primary",use_container_width=True):
            if not name: st.error("시공명은 필수입니다."); return
            if set(new_zones)!=set(cur_zones):
                ts=datetime.now().strftime("%Y%m%d_%H%M%S")
                arch=SS.get_archive(); arch[ts]={"project":p.copy(),"zone_data":SS.get_zone_data().get(pid(),{}).copy()}
                SS.set_archive(arch)
                for z_ in new_zones: ensure_zd(pid(),z_)
            projs=SS.get_projects()
            projs[pid()]={**p,"name":name,"address":full_addr,"region":sel_r,"district":sel_d,
                          "period_start":p_start.strftime("%Y-%m-%d"),"period_end":p_end.strftime("%Y-%m-%d"),"zones":new_zones}
            SS.set_projects(projs); go("main_board")
    with c2:
        if st.button("취소",use_container_width=True): go("main_board")

# ══════════════════════════════════════════════════════════════
# 페이지 3: 구역보드
# ══════════════════════════════════════════════════════════════
def page_zone_board():
    p,z=proj(),zone(); zd=zdata()
    rs=zd.get("reports",[]); ac=zd.get("accidents",[])
    st.markdown(f'<p class="title">{z} 구역</p>',unsafe_allow_html=True)
    st.markdown(f'<p class="sub">{p.get("name","")} | {p.get("address","")}</p>',unsafe_allow_html=True)

    prev_unresolved=_get_prev_unresolved()
    if prev_unresolved:
        st.markdown("""<div class='warn'><b>전일 미조치 사항</b> — 이행 여부를 확인하세요.</div>""",unsafe_allow_html=True)
        for i,item in enumerate(prev_unresolved):
            if st.checkbox(item["text"],key=f"pck_{i}"): _mark_resolved(item["text"])

    c1,c2,c3,c4=st.columns(4)
    c1.metric("전체 보고서",len(rs)); c2.metric("체크리스트",sum(1 for r in rs if r.get("type")=="checklist"))
    c3.metric("사고 건수",len(ac))
    recent=[r for r in rs if _pd(r.get("date",""))>=(datetime.now()-timedelta(days=7))]
    c4.metric("이번주 보고서",len(recent))
    st.markdown("---")

    col_l,col_r=st.columns(2)
    with col_l:
        st.markdown("**최근 일주일 보고서**")
        if recent:
            for r in reversed(recent[-5:]):
                with st.expander(f"{r.get('label','')} — {r.get('date','')}"):
                    st.text_area("내용",value=r.get("content",""),height=200,key=f"rv_{r.get('id','')}",disabled=True)
                    if r.get("path") and os.path.exists(r.get("path","")):
                        with open(r["path"],"rb") as f_:
                            st.download_button("PDF 다운로드",f_.read(),
                                               file_name=os.path.basename(r["path"]),
                                               mime="application/pdf",key=f"dl_{r.get('id','')}")
        else: st.info("최근 7일 내 보고서가 없습니다.")
    with col_r:
        st.markdown("**사고 기록**")
        if ac:
            for a in reversed(ac[-5:]):
                st.markdown(f"""<div class='warn'><b>{a.get('accident_type','')}</b> — {a.get('accident_datetime','')}<br>
<small>장소: {a.get('location','')} | 기인물: {a.get('cause_object','')}</small></div>""",unsafe_allow_html=True)
        else: st.info("기록된 사고가 없습니다.")

def _get_prev_unresolved():
    zd=zdata(); history=zd.get("daily_history",[])
    if not history: return []
    yesterday=(datetime.now()-timedelta(days=1)).strftime("%Y-%m-%d")
    for h in reversed(history):
        if h.get("date","")<=yesterday:
            return [i for i in h.get("prev_issues_items",[]) if not i.get("resolved",False) and i.get("text","")]
    return []

def _mark_resolved(text):
    p_,z_=pid(),zone()
    if not p_ or not z_: return
    zd=SS.get_zone_data()
    for h in zd.get(p_,{}).get(z_,{}).get("daily_history",[]):
        for item in h.get("prev_issues_items",[]):
            if item.get("text")==text: item["resolved"]=True
    SS.set_zone_data(zd)

def _pd(s):
    try: return datetime.strptime(s,"%Y-%m-%d")
    except: return datetime.min

# ══════════════════════════════════════════════════════════════
# 페이지 4: 금일 안전 업무 기록 (데일리 입력)
# ══════════════════════════════════════════════════════════════
def page_daily_input():
    z=zone()
    st.markdown(f"## 금일 안전 업무 기록 — {z}")
    zd=zdata(); history=zd.get("daily_history",[])
    di=st.session_state.daily_input

    # 전일 미조치
    prev_unresolved=_get_prev_unresolved()
    carry_over=[]
    if prev_unresolved:
        st.markdown("""<div class='warn'><b>전일 미조치 사항</b> — 이행 여부 확인 후 오늘 보고서에 반영할 항목을 선택하세요.</div>""",unsafe_allow_html=True)
        for i,item in enumerate(prev_unresolved):
            c1_,c2_=st.columns([.12,.88])
            done=c1_.checkbox("완료",key=f"dn_{i}")
            c2_.markdown(f"{'~~'+item['text']+'~~' if done else item['text']}")
            if not done and st.checkbox("오늘 보고서에 반영",key=f"cr_{i}",value=True):
                carry_over.append(item["text"])
        st.markdown("---")

    # 기본 사항
    st.markdown("#### 기본 사항")
    c1,c2=st.columns(2)
    try: d_def=datetime.strptime(di.get("date",""),"%Y-%m-%d").date()
    except: d_def=date.today()
    d=c1.date_input("작성 일자 *",value=d_def)
    manager=c1.text_input("관리자 *",value=di.get("manager",""),placeholder="예: 김성균")
    location=c2.text_input("작업 위치 *",value=di.get("location",""),placeholder="예: A동 12층 외벽")
    env=c2.selectbox("작업 환경",["지상","고소","밀폐","지하","수중","기타"])

    hours=[f"{h:02d}" for h in range(6,21)]; mins=["00","30"]
    tc1,tc2,tc3,tc4=st.columns(4)
    sh=tc1.selectbox("시작 시",hours,index=hours.index("08"),key="sh")
    sm=tc2.selectbox("시작 분",mins,key="sm")
    eh=tc3.selectbox("종료 시",hours,index=hours.index("17"),key="eh")
    em=tc4.selectbox("종료 분",mins,key="em")
    work_time=f"{sh}:{sm} ~ {eh}:{em}"

    materials=st.text_input("주요 자재",value=di.get("materials",""),placeholder="예: 철근, 거푸집")
    workers=st.text_area("투입 인원 현황 (공종별) *",value=di.get("workers",""),
                          placeholder="예: 철근공 10명, 형틀공 5명",height=65)
    wp=st.text_area("주요 작업 내용 *",value=di.get("work_process",""),
                     placeholder="예: 12층 외부 갱폼 인양 및 설치",height=65)

    c7,c8=st.columns(2)
    prev_default="\n".join(carry_over) if carry_over else di.get("prev_issues","")
    prev=c7.text_area("전일 미조치 사항 (없으면 공백)",value=prev_default,height=65)
    nearby=c8.text_area("주변 구역 간섭 (없으면 공백)",value=di.get("nearby_interference",""),height=65)
    nw=st.text_input("신규 인원 (없으면 공백)",value=di.get("new_workers",""))

    # 장비 현황
    st.markdown("#### 장비 현황")
    eq_counts=di.get("equipment_counts",{})
    eq_cols=st.columns(5)
    for i,eq in enumerate(EQUIPMENT_TYPES):
        with eq_cols[i%5]:
            n=st.number_input(eq,min_value=0,max_value=99,value=int(eq_counts.get(eq,0)),step=1,key=f"eq_{eq}")
            eq_counts[eq]=n
    eq_custom=st.text_input("기타 장비",value=di.get("equipment_custom",""),placeholder="예: 특수차량 1대")
    eq_list=[f"{k} {v}대" for k,v in eq_counts.items() if v>0]
    if eq_custom.strip(): eq_list.append(eq_custom.strip())
    equipment_str=", ".join(eq_list) if eq_list else "없음"

    # 날씨
    st.markdown(f"#### 날씨 — {d.strftime('%Y년 %m월 %d일')}")
    weather={}
    if st.toggle("기상청 자동 추출",value=False):
        addr=f"{proj().get('region','')} {proj().get('district','')}"
        with st.spinner("날씨 정보 가져오는 중..."): weather=fetch_weather(addr,d.strftime("%Y%m%d"))
        if weather.get("available"):
            wc1,wc2,wc3=st.columns(3)
            wc1.metric("평균기온",weather["temp_avg"]); wc1.metric("최고기온",weather["temp_max"])
            wc2.metric("평균습도",weather["humidity"]); wc2.metric("평균풍속",weather["wind_speed"])
            wc3.metric("최고풍속",weather["wind_max"]); wc3.metric("최고점시간",weather["peak_time"])
        else: st.warning(weather.get("message","")); weather=_mw()
    else: weather=_mw()

    # 현장 특이사항
    st.markdown("#### 현장 특이사항")
    env_note=st.text_area("현장 특이사항 (없으면 공백)",value=di.get("env_note",""),
                           placeholder="예: 14:00경 최고 풍속 12m/s 예보, 하부 자재 정리 공정 간섭",height=65)

    missing=[n for n,v in [("관리자",manager),("작업 위치",location),("투입 인원 현황",workers),("주요 작업 내용",wp)] if not v]
    if missing:
        st.markdown(f"""<div class='warn'>필수 입력: {'  |  '.join(missing)}</div>""",unsafe_allow_html=True)

    prev_items=[{"text":l.strip(),"resolved":False} for l in prev.split("\n") if l.strip()] if prev.strip() else []
    daily={
        "date":d.strftime("%Y-%m-%d"),"date_c":d.strftime("%Y%m%d"),
        "manager":manager,"workers":workers,"equipment":equipment_str,
        "equipment_counts":eq_counts,"equipment_custom":eq_custom,
        "work_time":work_time,"location":location,"env":env,
        "materials":materials,"weather":weather,"work_process":wp,
        "prev_issues":prev.strip() or "없음","prev_issues_items":prev_items,
        "nearby_interference":nearby.strip() or "없음","new_workers":nw.strip() or "없음",
        "env_note":env_note.strip() or "없음","missing":missing,
    }
    st.session_state.daily_input=daily
    if not missing: _save_dh(daily)

    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        if st.button("일일 안전일지 생성",type="primary",disabled=bool(missing),use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]
            go("gen_daily_log")
    with c2:
        if st.button("안전 체크리스트 생성",type="primary",disabled=bool(missing),use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]
            go("gen_checklist")

def _mw():
    c1,c2,c3=st.columns(3)
    return {"available":True,
            "temp_avg":c1.text_input("평균기온",placeholder="예:23.5°C",key="wa"),
            "temp_max":c1.text_input("최고기온",placeholder="예:28°C",key="wb"),
            "humidity":c2.text_input("평균습도",placeholder="예:65%",key="wc"),
            "wind_speed":c2.text_input("평균풍속",placeholder="예:3.2m/s",key="wd"),
            "wind_max":c3.text_input("최고풍속",placeholder="예:12m/s",key="we"),
            "peak_time":c3.text_input("최고점시간",placeholder="예:14:00",key="wf")}

def _save_dh(daily):
    p_,z_=pid(),zone()
    if not p_ or not z_: return
    ensure_zd(p_,z_)
    zd=SS.get_zone_data()
    history=zd[p_][z_].get("daily_history",[])
    for h in history:
        if h.get("date")==daily["date"]: h.update(daily); SS.set_zone_data(zd); return
    history.append(daily); zd[p_][z_]["daily_history"]=history; SS.set_zone_data(zd)

# ══════════════════════════════════════════════════════════════
# 법규 선택 UI (최대 3개)
# ══════════════════════════════════════════════════════════════
def law_ui(query):
    if not st.session_state.law_candidates:
        with st.spinner("관련 법령 검색 중..."): st.session_state.law_candidates=get_law_candidates(query)
    candidates=st.session_state.law_candidates[:3]  # 최대 3개만
    if not candidates: st.info("관련 법령 후보를 찾지 못했습니다."); return []
    st.markdown("**적용 법령 선택** (해당하는 항목 선택)")
    selected=[]
    for law in candidates:
        c1,c2=st.columns([.07,.93])
        checked=c1.checkbox("선택",key=f"lc_{law['id']}",label_visibility="hidden")
        c2.markdown(f"""<div class='law-card'><b>[{law['name']} {law['article']}]</b> {law.get('title','')}<br>
<small>{law.get('summary','')}</small></div>""",unsafe_allow_html=True)
        if checked: selected.append(f"[{law['name']} {law['article']}] {law.get('title','')} — {law.get('summary','')}")
    return selected

def review_ui(content):
    st.markdown("### 보고서 확인 및 수정")
    edited=st.text_area("내용",value=content,height=400,key="edit_area")
    c1,c2=st.columns(2)
    save=c1.button("PDF로 저장",type="primary",use_container_width=True)
    retry=c2.button("다시 생성",use_container_width=True)
    if retry:
        st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]; st.rerun()
    return save,edited

def save_report(rtype,label,path,content,rdate):
    p_,z_=pid(),zone(); ensure_zd(p_,z_)
    zd=SS.get_zone_data()
    zd[p_][z_]["reports"].append({"id":str(uuid.uuid4())[:8],"type":rtype,"label":label,"date":rdate,"path":path,"content":content})
    SS.set_zone_data(zd); st.session_state.report_content=""

# ══════════════════════════════════════════════════════════════
# 페이지 5: 일일 안전일지 생성
# ══════════════════════════════════════════════════════════════
def page_gen_daily_log():
    daily=st.session_state.daily_input
    st.markdown(f"## 일일 안전일지 — {zone()}")
    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 안전"
        st.markdown("---")
        st.session_state.selected_laws=law_ui(query)
        if st.button("안전일지 생성",type="primary",use_container_width=True):
            with st.spinner("AI가 안전일지를 작성 중입니다..."):
                st.session_state.report_content=generate_daily_log(daily,st.session_state.selected_laws)
            st.rerun()
    else:
        daily=st.session_state.daily_input
        save,edited=review_ui(st.session_state.report_content)
        if save:
            with st.spinner("PDF 저장 중..."):
                path=save_daily_log_pdf(daily,edited,proj()["name"],st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            if os.path.exists(path):
                with open(path,"rb") as f_:
                    st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
            save_report("daily","일일 안전일지",path,edited,daily["date"])

# ══════════════════════════════════════════════════════════════
# 페이지 6: 안전 체크리스트
# ══════════════════════════════════════════════════════════════
def page_gen_checklist():
    daily=st.session_state.daily_input
    st.markdown(f"## 안전 체크리스트 — {zone()}")
    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 점검"
        st.markdown("---")
        st.session_state.selected_laws=law_ui(query)
        if st.button("체크리스트 생성",type="primary",use_container_width=True):
            with st.spinner("AI가 체크리스트를 생성 중입니다..."):
                st.session_state.report_content=generate_checklist(daily,st.session_state.selected_laws)
            st.rerun()
    else:
        daily=st.session_state.daily_input
        st.markdown(f"**작성 일자:** {daily.get('date','')}  |  **주요 작업 내용:** {daily.get('work_process','')}  |  **위치:** {daily.get('location','')}")
        prev=daily.get("prev_issues","없음")
        if prev and prev!="없음":
            st.markdown("---")
            st.markdown("**전일 미조치 사항**")
            for item in prev.split("\n"):
                if item.strip(): st.markdown(f"""<div class='warn'>{item.strip()}</div>""",unsafe_allow_html=True)
        st.markdown("---")
        st.text_area("체크리스트 내용",value=st.session_state.report_content,height=400,disabled=True)
        c1,c2=st.columns(2)
        with c1:
            if c1.button("PDF로 저장",type="primary",use_container_width=True):
                with st.spinner("PDF 저장 중..."):
                    path=save_checklist_pdf(st.session_state.report_content,daily["date_c"],proj()["name"],st.session_state.pdf_save_dir)
                st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
                if os.path.exists(path):
                    with open(path,"rb") as f_:
                        st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
                save_report("checklist","안전 체크리스트",path,st.session_state.report_content,daily["date"])
        with c2:
            if c2.button("다시 생성",use_container_width=True):
                st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]; st.rerun()

# ══════════════════════════════════════════════════════════════
# 페이지 7: 사고 보고서
# ══════════════════════════════════════════════════════════════
def page_accident_form():
    st.markdown(f"## 사고 보고서 — {zone()}")
    acc=st.session_state.accident_input; p=proj()
    if not st.session_state.report_content:
        st.markdown("### 사고 정보 입력")
        with st.expander("기본 정보",expanded=True):
            c1,c2=st.columns(2)
            wd=c1.date_input("작성 일자",value=date.today())
            pname=c2.text_input("현장명",value=p.get("name",""))
            c3,c4=st.columns(2)
            wpos=c3.text_input("작성자 직위",value=acc.get("writer_position",""),placeholder="예: 안전관리자")
            wname=c4.text_input("작성자 성명",value=acc.get("writer_name",""))

        with st.expander("재해자 정보",expanded=True):
            c1,c2=st.columns(2)
            sub=c1.text_input("협력업체명",value=acc.get("subcontractor",""))
            c3,c4=st.columns(2)
            vn=c3.text_input("재해자 성명",value=acc.get("victim_name",""))
            hd=c4.text_input("채용일",value=acc.get("hire_date",""),placeholder="예: 2025-01-15")

        with st.expander("사고 발생 정보",expanded=True):
            c1,c2=st.columns(2)
            try: adf=datetime.strptime(acc.get("accident_date",""),"%Y-%m-%d").date()
            except: adf=date.today()
            adt_date=c1.date_input("사고 발생 일자",value=adf)
            hours_a=[f"{h:02d}" for h in range(0,24)]; mins_a=["00","10","20","30","40","50"]
            tc1,tc2=c1.columns(2)
            sh_=acc.get("accident_time","14:00").split(":")[0] if acc.get("accident_time") else "14"
            sm_=acc.get("accident_time","14:00").split(":")[-1] if acc.get("accident_time") else "00"
            adt_h=tc1.selectbox("시",hours_a,index=hours_a.index(sh_) if sh_ in hours_a else 14,key="adt_h")
            adt_m=tc2.selectbox("분",mins_a,index=mins_a.index(sm_) if sm_ in mins_a else 0,key="adt_m")
            adt_time=f"{adt_h}:{adt_m}"
            loc=c2.text_input("작업 장소",value=acc.get("location",""))
            cobj=c2.text_input("기인물",value=acc.get("cause_object",""),placeholder="예: 갱폼")
            atype=c1.selectbox("발생 형태",["추락","낙하","감전","협착","충돌","화재·폭발","기타"])
            c5,c6=st.columns(2)
            ip=c5.text_input("상해 부위",value=acc.get("injury_part",""),placeholder="예: 우측 하지")
            it_=c6.text_input("상해 종류",value=acc.get("injury_type",""),placeholder="예: 골절")

        with st.expander("작업 내용 및 과정 *",expanded=True):
            wp_=st.text_area("작업 내용 및 과정",value=acc.get("work_process",""),height=100,
                              placeholder="사고 발생 전 작업 단계를 순서대로 기술해주세요.")

        with st.expander("재해 발생 개요 *",expanded=True):
            ov=st.text_area("재해 발생 개요",value=acc.get("overview",""),height=100,
                             placeholder="언제, 어디서, 누가, 무엇을, 어떻게, 왜 — 육하원칙으로 기술해주세요.")

        st.markdown("""<div class='info'>사고 직접 원인은 AI가 법규 DB를 분석하여 자동으로 작성합니다.</div>""",unsafe_allow_html=True)

        new_acc={
            "write_date":wd.strftime("%Y-%m-%d"),"project_name":pname,
            "writer_position":wpos,"writer_name":wname,
            "subcontractor":sub,"victim_name":vn,"hire_date":hd,
            "accident_datetime":f"{adt_date.strftime('%Y-%m-%d')} {adt_time}",
            "accident_date":adt_date.strftime("%Y-%m-%d"),"accident_time":adt_time,
            "location":loc,"cause_object":cobj,"accident_type":atype,
            "injury_part":ip,"injury_type":it_,"overview":ov,"work_process":wp_,
        }
        st.session_state.accident_input=new_acc

        if atype and loc:
            st.markdown("---")
            st.session_state.selected_laws=law_ui(f"{atype} {loc} 산업재해")

        missing=[k for k in ["overview","work_process"] if not new_acc.get(k)]
        if missing:
            st.markdown("""<div class='warn'>재해 발생 개요와 작업 내용 및 과정은 필수입니다.</div>""",unsafe_allow_html=True)

        if st.button("사고 보고서 생성",type="primary",disabled=bool(missing),use_container_width=True):
            with st.spinner("AI가 보고서를 작성 중입니다..."):
                st.session_state.report_content=generate_accident_report(new_acc,st.session_state.selected_laws)
            st.rerun()
    else:
        acc=st.session_state.accident_input
        save,edited=review_ui(st.session_state.report_content)
        if save:
            date_c=acc.get("write_date","").replace("-","")
            with st.spinner("PDF 저장 중..."):
                path=save_accident_form_pdf(acc,edited,st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            if os.path.exists(path):
                with open(path,"rb") as f_:
                    st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
            p_,z_=pid(),zone(); ensure_zd(p_,z_)
            zd=SS.get_zone_data(); zd[p_][z_]["accidents"].append(acc); SS.set_zone_data(zd)
            st.session_state.report_content=""

# ══════════════════════════════════════════════════════════════
# 페이지 8: Chatbot
# ══════════════════════════════════════════════════════════════
def page_chatbot():
    z_=zone() or "전체"
    st.markdown(f"## Chatbot — {z_}")
    p_=pid()
    if p_ and z_ and z_!="전체":
        ensure_zd(p_,z_)
        zd=SS.get_zone_data(); chat_history=zd[p_][z_]["chat"]
    else:
        if "global_chat" not in st.session_state: st.session_state.global_chat=[]
        chat_history=st.session_state.global_chat

    for msg in chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if q:=st.chat_input("법령 관련 질문을 입력하세요..."):
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner("법령 검색 중..."): r=law_search(q)
            st.markdown(r["answer"])
            if r["count"]: st.caption(f"참조 청크: {r['count']}개")
        chat_history+=[{"role":"user","content":q},{"role":"assistant","content":r["answer"]}]
        if p_ and z_ and z_!="전체":
            zd=SS.get_zone_data(); zd[p_][z_]["chat"]=chat_history; SS.set_zone_data(zd)

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