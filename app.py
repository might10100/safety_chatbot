"""
app.py — 건설 현장 안전관리 AI v3
"""
import streamlit as st
from datetime import date, datetime, timedelta
import uuid, os
import shared_state as SS

from chain_search import (load_resources, law_search, get_law_candidates,
                           generate_daily_log, generate_checklist,
                           generate_accident_report)
from weather import fetch_weather
from pdf_utils import save_daily_log_pdf, save_checklist_pdf
from accident_form import save_accident_form_pdf

st.set_page_config(page_title="건설 현장 안전관리 AI", page_icon="🏗", layout="wide")
st.markdown("""<style>
.title{font-size:1.8rem;font-weight:900;color:#1a1a2e;}
.sub{font-size:.85rem;color:#888;margin-bottom:1rem;}
.card{background:#f8f9ff;border-radius:10px;padding:1rem;border-left:4px solid #4361ee;margin-bottom:.6rem;}
.warn{background:#fff0f0;border-radius:8px;padding:.7rem;border-left:4px solid #e74c3c;margin:.4rem 0;}
.info{background:#e3f2fd;border-radius:8px;padding:.7rem;border-left:4px solid #2196f3;margin:.4rem 0;}
.ok{background:#e8f5e9;border-radius:8px;padding:.7rem;border-left:4px solid #4caf50;margin:.4rem 0;}
.law-card{background:#fffde7;border-radius:8px;padding:.6rem;border:1px solid #ffc107;margin:.3rem 0;}
.req{color:#e74c3c;font-weight:bold;}
.sec-label{font-weight:bold;font-size:1rem;margin:1rem 0 .3rem 0;color:#1a1a2e;}
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

for k,v in {
    "page":"landing","cur_proj_id":None,"cur_zone":None,
    "feature":None,"law_candidates":[],"selected_laws":[],
    "report_content":"","daily_input":{},"accident_input":{},
    "pdf_save_dir":"","show_new_proj":False,
    "region_sel":"서울특별시","district_sel":"강남구",
}.items():
    if k not in st.session_state: st.session_state[k]=v

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

def _pd(s):
    try: return datetime.strptime(s,"%Y-%m-%d")
    except: return datetime.min

# ── 사이드바 ─────────────────────────────────────────────────
def _pick_folder():
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk(); root.withdraw(); root.wm_attributes("-topmost",1)
    f=filedialog.askdirectory(); root.destroy(); return f

def sidebar():
    page=st.session_state.page
    if page in ("landing","main_board","edit_project"): return
    p,z=proj(),zone()
    with st.sidebar:
        st.markdown(f"**{p.get('name','')}**")
        if z: st.caption(f"{z}")
        st.divider()
        st.markdown("**기능**")
        if st.button("Chatbot", type="primary" if page=="chatbot" else "secondary", use_container_width=True):
            go("chatbot")
        if z:
            if st.button("금일 안전 업무 기록", type="primary" if page=="daily_input" else "secondary", use_container_width=True):
                go("daily_input")
            if st.button("사고 보고서", type="primary" if page=="accident_form" else "secondary", use_container_width=True):
                go("accident_form", accident_input={}, report_content="")
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
        c1,c2=st.columns(2)
        items=list(qp.items())
        for i,(lbl,path) in enumerate(items):
            col=c1 if i%2==0 else c2
            if col.button(lbl,key=f"qp_{lbl}",type="primary" if cur_dir==path else "secondary",use_container_width=True):
                st.session_state.pdf_save_dir=path; st.rerun()
        if st.button("폴더 직접 선택", use_container_width=True):
            try:
                f=_pick_folder()
                if f: st.session_state.pdf_save_dir=f; st.rerun()
            except: st.info("경로를 직접 입력해 주세요.")
        if cur_dir: st.caption(f"저장: {os.path.basename(cur_dir)}")
        else: st.caption("저장: 바탕화면 (기본값)")

# ── 위치 선택 ─────────────────────────────────────────────────
def location_selector(key_prefix="", cur_region="서울특별시", cur_dist="강남구"):
    regions=list(REGIONS.keys())
    sel_r=st.selectbox("광역시/도 *",regions,
        index=regions.index(cur_region) if cur_region in regions else 0,
        key=f"{key_prefix}region")
    dists=REGIONS[sel_r]
    sel_d=st.selectbox("시/군/구 *",dists,
        index=dists.index(cur_dist) if cur_dist in dists else 0,
        key=f"{key_prefix}district")
    detail=st.text_input("상세 주소",placeholder="예: 역삼동 123-4",key=f"{key_prefix}detail")
    return f"{sel_r} {sel_d} {detail}".strip(), sel_r, sel_d

# ══════════════════════════════════════════════════════════════
# 랜딩
# ══════════════════════════════════════════════════════════════
def page_landing():
    st.markdown('<p class="title">건설 현장 안전관리 AI</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub">관리할 공사 현장을 선택하거나 새로 등록하세요.</p>', unsafe_allow_html=True)
    projects=SS.get_projects(); archive=SS.get_archive()

    if projects:
        st.markdown("### 저장된 공사 현장")
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
                    projs=SS.get_projects(); del projs[pid_]; SS.set_projects(projs); st.rerun()
        st.markdown("---")

    if archive:
        with st.expander(f"이전 현장 기록 ({len(archive)}건)"):
            for ts_,arc in archive.items():
                p_=arc.get("project",{})
                st.markdown(f"""<div class='card'><b>{p_.get('name','')}</b> — {ts_}<br>
<small>{p_.get('address','')} | {p_.get('period_start','')} ~ {p_.get('period_end','')}</small></div>""",unsafe_allow_html=True)

    if projects:
        if st.button("+ 새 공사 현장 등록"):
            st.session_state.show_new_proj=not st.session_state.show_new_proj; st.rerun()
        show=st.session_state.show_new_proj
    else:
        show=True; st.markdown("### 공사 현장 정보 입력")

    if show:
        st.markdown("**시공명 ***")
        name=st.text_input("시공명",placeholder="예: 강남 OO아파트 신축공사",label_visibility="collapsed")
        c1,c2=st.columns(2)
        with c1:
            st.markdown("**현장 위치 ***")
            full_addr,sel_r,sel_d=location_selector("new_")
        with c2:
            st.markdown("**시공 기간 ***")
            p_start=st.date_input("착공일 *",value=date.today(),key="new_ps")
            p_end=st.date_input("완공일 *",value=date.today(),key="new_pe")
        st.markdown("**구역 구획화**")
        zone_count=st.number_input("구역 수 *",min_value=1,max_value=20,value=3,step=1)
        cols=st.columns(min(int(zone_count),4))
        zone_names=[]
        for i in range(int(zone_count)):
            with cols[i%4]:
                z_=st.text_input(f"구역 {i+1}",value=f"구역{i+1}",key=f"nz{i}")
                zone_names.append(z_.strip() or f"구역{i+1}")
        if st.button("공사 현장 등록 및 시작",type="primary",use_container_width=True):
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
# 메인 보드
# ══════════════════════════════════════════════════════════════
def page_main_board():
    p=proj()
    st.markdown(f'<p class="title">{p.get("name","")}</p>',unsafe_allow_html=True)
    st.markdown(f'<p class="sub">{p.get("address","")}  |  {p.get("period_start","")} ~ {p.get("period_end","")}</p>',unsafe_allow_html=True)
    c1,c2=st.columns([.8,.2])
    with c2:
        if st.button("현장 정보 변경",use_container_width=True): go("edit_project")
    st.markdown("---")
    st.markdown("### 구역 현황")
    zones=p.get("zones",[])
    if not zones: st.info("등록된 구역이 없습니다."); return
    cols=st.columns(min(len(zones),3))
    for i,z_ in enumerate(zones):
        with cols[i%3]:
            zd_=SS.get_zone_data().get(pid(),{}).get(z_,{})
            acc_cnt=len(zd_.get("accidents",[]))
            border="#e74c3c" if acc_cnt>0 else "#4361ee"
            if st.button(f"**{z_}**\n\n사고 {acc_cnt}건",key=f"gz_{i}",use_container_width=True):
                st.session_state.cur_zone=z_; ensure_zd(pid(),z_); go("zone_board")

# ══════════════════════════════════════════════════════════════
# 현장 정보 수정
# ══════════════════════════════════════════════════════════════
def page_edit_project():
    p=proj()
    st.markdown("## 현장 정보 수정")
    st.markdown("**시공명 ***")
    name=st.text_input("시공명",value=p.get("name",""),label_visibility="collapsed")
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**현장 위치 ***")
        full_addr,sel_r,sel_d=location_selector("edit_",p.get("region","서울특별시"),p.get("district","강남구"))
    with c2:
        st.markdown("**시공 기간 ***")
        try: ps=datetime.strptime(p.get("period_start",""),"%Y-%m-%d").date()
        except: ps=date.today()
        try: pe=datetime.strptime(p.get("period_end",""),"%Y-%m-%d").date()
        except: pe=date.today()
        p_start=st.date_input("착공일 *",value=ps,key="edit_ps")
        p_end=st.date_input("완공일 *",value=pe,key="edit_pe")
    st.markdown("**구역 구획화** (변경 시 기존 데이터는 아카이브에 저장)")
    cur_zones=p.get("zones",[])
    zone_count=st.number_input("구역 수 *",min_value=1,max_value=20,value=len(cur_zones),step=1)
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
# 구역 보드
# ══════════════════════════════════════════════════════════════
def page_zone_board():
    p,z=proj(),zone(); zd=zdata()
    ac=zd.get("accidents",[])
    st.markdown(f'<p class="title">{z}</p>',unsafe_allow_html=True)
    st.markdown(f'<p class="sub">{p.get("name","")} | {p.get("address","")}</p>',unsafe_allow_html=True)

    # 전일 미조치 확인
    prev_unresolved=_get_prev_unresolved()
    if prev_unresolved:
        st.markdown("""<div class='warn'><b>전일 미조치 사항</b> — 이행 여부를 확인하세요.</div>""",unsafe_allow_html=True)
        for i,item in enumerate(prev_unresolved):
            if st.checkbox(item["text"],key=f"pck_{i}"): _mark_resolved(item["text"])

    # 사고 건수 + 파이차트
    col_stat, col_chart = st.columns([1,1])
    with col_stat:
        st.metric("사고 건수", len(ac))
    with col_chart:
        if ac:
            types={}
            for a in ac: types[a.get("accident_type","기타")]=types.get(a.get("accident_type","기타"),0)+1
            try:
                import matplotlib.pyplot as plt, matplotlib
                matplotlib.use("Agg")
                fig,ax=plt.subplots(figsize=(3,3))
                ax.pie(types.values(),labels=types.keys(),autopct="%1.0f%%",textprops={"fontsize":8})
                ax.set_title("유형별 사고",fontsize=9)
                st.pyplot(fig); plt.close()
            except: st.write(str(types))

    st.markdown("---")
    # 사고 기록 전체 표시
    st.markdown("**사고 기록**")
    if ac:
        for a in reversed(ac):
            st.markdown(f"""<div class='warn'><b>{a.get('accident_type','')}</b> — {a.get('accident_datetime','')}<br>
<small>장소: {a.get('location','')} | 기인물: {a.get('cause_object','')}</small></div>""",unsafe_allow_html=True)
    else:
        st.info("기록된 사고가 없습니다.")

    # 최근 보고서
    rs=zd.get("reports",[])
    if rs:
        st.markdown("**최근 보고서**")
        one_week_ago=datetime.now()-timedelta(days=7)
        recent=[r for r in rs if _pd(r.get("date",""))>=one_week_ago]
        for r in reversed(recent[-5:]):
            with st.expander(f"{r.get('label','')} — {r.get('date','')}"):
                st.text_area("",value=r.get("content",""),height=200,key=f"rv_{r.get('id','')}",disabled=True,label_visibility="collapsed")
                if r.get("path") and os.path.exists(r.get("path","")):
                    with open(r["path"],"rb") as f_:
                        st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(r["path"]),mime="application/pdf",key=f"dl_{r.get('id','')}")

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

# ══════════════════════════════════════════════════════════════
# 금일 안전 업무 기록
# ══════════════════════════════════════════════════════════════
def page_daily_input():
    z=zone()
    st.markdown(f"## 금일 안전 업무 기록 — {z}")
    di=st.session_state.daily_input

    # 필수 항목 안내
    st.markdown("""<div class='info'>* 표시가 있는 항목은 반드시 입력해 주세요.</div>""",unsafe_allow_html=True)

    # ── 기본 사항 ──
    st.markdown('<p class="sec-label">기본 사항</p>',unsafe_allow_html=True)
    c1,c2=st.columns(2)
    try: d_def=datetime.strptime(di.get("date",""),"%Y-%m-%d").date()
    except: d_def=date.today()
    d=c1.date_input("작성 일자 *",value=d_def)

    hours=[f"{h:02d}" for h in range(6,21)]; mins=["00","30"]
    tc1,tc2,tc3,tc4=st.columns(4)
    sh=tc1.selectbox("시작 시 *",hours,index=hours.index("08"),key="sh")
    sm=tc2.selectbox("시작 분 *",mins,key="sm")
    eh=tc3.selectbox("종료 시 *",hours,index=hours.index("17"),key="eh")
    em=tc4.selectbox("종료 분 *",mins,key="em")
    work_time=f"{sh}:{sm} ~ {eh}:{em}"

    c3,c4=st.columns(2)
    manager=c3.text_input("관리자 *",value=di.get("manager",""),placeholder="예: 김성균")
    location=c4.text_input("작업 위치 *",value=di.get("location",""),placeholder="예: A동 12층 외벽")
    env=c3.selectbox("작업 환경 *",["지상","고소","밀폐","지하","수중","기타"])
    materials=c4.text_input("주요 자재",value=di.get("materials",""),placeholder="예: 철근, 거푸집")

    workers=st.text_area("투입 인원 현황 (공종별) *",value=di.get("workers",""),
                          placeholder="예: 철근공 10명, 형틀공 5명",height=65)
    wp=st.text_area("주요 작업 내용 *",value=di.get("work_process",""),
                     placeholder="예: 12층 외부 갱폼 인양 및 설치",height=65)

    # ── 특이 사항 ──
    st.markdown('<p class="sec-label">특이 사항</p>',unsafe_allow_html=True)
    prev_unresolved=_get_prev_unresolved()
    carry_over=[]
    if prev_unresolved:
        st.markdown("""<div class='warn'><b>전일 미조치 사항</b> — 이행 여부를 확인하세요.</div>""",unsafe_allow_html=True)
        for i,item in enumerate(prev_unresolved):
            c1_,c2_=st.columns([.12,.88])
            done=c1_.checkbox("완료",key=f"dn_{i}")
            c2_.markdown(f"{'~~'+item['text']+'~~' if done else item['text']}")
            if not done and st.checkbox("오늘 보고서에 반영",key=f"cr_{i}",value=True):
                carry_over.append(item["text"])

    prev_default="\n".join(carry_over) if carry_over else di.get("prev_issues","")
    c7,c8=st.columns(2)
    prev=c7.text_area("전일 미조치 사항",value=prev_default,height=65,placeholder="없으면 공백")
    nearby=c8.text_area("주변 구역 간섭",value=di.get("nearby_interference",""),height=65,placeholder="없으면 공백")
    nw=st.text_input("신규 인원",value=di.get("new_workers",""),placeholder="없으면 공백")

    # ── 장비 현황 ──
    st.markdown('<p class="sec-label">장비 현황</p>',unsafe_allow_html=True)
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

    # ── 날씨 * ──
    st.markdown('<p class="sec-label">날씨 *</p>',unsafe_allow_html=True)
    weather={}
    if st.toggle("기상청 자동 추출",value=False):
        p_=proj()
        addr=f"{p_.get('region','')} {p_.get('district','')}"
        with st.spinner("날씨 정보 가져오는 중..."):
            weather=fetch_weather(addr,d.strftime("%Y%m%d"),region=p_.get("region",""),district=p_.get("district",""))
        if weather.get("available"):
            wc1,wc2,wc3=st.columns(3)
            wc1.metric("평균기온",weather["temp_avg"]); wc1.metric("최고기온",weather["temp_max"])
            wc2.metric("평균습도",weather["humidity"]); wc2.metric("평균풍속",weather["wind_speed"])
            wc3.metric("최고풍속",weather["wind_max"]); wc3.metric("최고점시간",weather["peak_time"])
        else:
            st.warning(weather.get("message","")); weather=_mw()
    else:
        weather=_mw()

    # 필수 항목 체크
    required_checks=[("관리자",manager),("작업 위치",location),("투입 인원 현황",workers),("주요 작업 내용",wp)]
    weather_ok=any(weather.get(k) for k in ["temp_avg","wind_max"])
    if not weather_ok: required_checks.append(("날씨",None))
    missing=[n for n,v in required_checks if not v]

    if missing:
        for n,v in required_checks:
            if not v:
                st.markdown(f'<span class="req">{n} 항목을 입력해 주세요.</span>',unsafe_allow_html=True)

    prev_items=[{"text":l.strip(),"resolved":False} for l in prev.split("\n") if l.strip()] if prev.strip() else []
    daily={
        "date":d.strftime("%Y-%m-%d"),"date_c":d.strftime("%Y%m%d"),
        "manager":manager,"workers":workers,"equipment":equipment_str,
        "equipment_counts":eq_counts,"equipment_custom":eq_custom,
        "work_time":work_time,"location":location,"env":env,
        "materials":materials,"weather":weather,"work_process":wp,
        "prev_issues":prev.strip() or "없음","prev_issues_items":prev_items,
        "nearby_interference":nearby.strip() or "없음","new_workers":nw.strip() or "없음",
        "missing":missing,
    }
    st.session_state.daily_input=daily
    if not missing: _save_dh(daily)

    st.markdown("---")
    c1,c2=st.columns(2)
    with c1:
        if st.button("금일 안전 일지 작성",type="primary",disabled=bool(missing),use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]
            go("gen_daily_log")
    with c2:
        if st.button("안전 점검 체크리스트 작성",type="primary",disabled=bool(missing),use_container_width=True):
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

# ── 법규 선택 ─────────────────────────────────────────────────
def law_ui(query):
    if not st.session_state.law_candidates:
        with st.spinner("법령 검색 중..."): st.session_state.law_candidates=get_law_candidates(query)
    candidates=st.session_state.law_candidates[:3]
    if not candidates: st.info("관련 법령 후보를 찾지 못했습니다."); return []
    st.markdown("**준거 기준 선택**")
    selected=[]
    for law in candidates:
        c1,c2=st.columns([.07,.93])
        checked=c1.checkbox("선택",key=f"lc_{law['id']}",label_visibility="hidden")
        c2.markdown(f"""<div class='law-card'><b>[{law['name']} {law['article']}]</b> {law.get('title','')}<br>
<small>{law.get('summary','')}</small></div>""",unsafe_allow_html=True)
        if checked: selected.append(f"[{law['name']} {law['article']}] {law.get('title','')} — {law.get('summary','')}")
    return selected

def render_daily_log_html(daily,report_text):
    lines=report_text.split("\n")
    risk_sets=[]; risk=law_=action=""
    for line in lines:
        s=line.strip()
        if s.startswith("[위험요인]"):
            if risk: risk_sets.append((risk,law_,action))
            risk=s.replace("[위험요인]","").strip(); law_=""; action=""
        elif s.startswith("[법적 근거]"): law_=s.replace("[법적 근거]","").strip()
        elif s.startswith("[안전 조치]"): action=s.replace("[안전 조치]","").strip()
    if risk: risk_sets.append((risk,law_,action))
    if not risk_sets: risk_sets=[("(위험 요인 없음)","","")]

    tbm=""; in_tbm=False
    for line in lines:
        if "TBM 메시지" in line: in_tbm=True; continue
        if in_tbm and line.strip() and not line.strip().startswith("["): tbm+=line.strip()+" "
    tbm=tbm.strip() or "(TBM 메시지 없음)"

    w=daily.get("weather",{})
    ws=(f"최고풍속 {w.get('wind_max','-')} ({w.get('peak_time','-')} 도달) / 평균기온 {w.get('temp_avg','-')}"
        if w and w.get("temp_avg") else "날씨 데이터 없음")

    risk_html=""
    for r,l,a in risk_sets:
        risk_html+=f"""<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;width:18%;">위험 요인</td>
<td colspan="3" style="padding:6px;border:1px solid #aaa;">{r}</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">법적 근거</td>
<td colspan="3" style="padding:6px;border:1px solid #aaa;">{l}</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">안전 조치 사항</td>
<td colspan="3" style="padding:6px;border:1px solid #aaa;">{a}</td></tr>
<tr><td colspan="4" style="padding:2px;background:#f0f0f0;"></td></tr>"""

    return f"""<table style="width:100%;border-collapse:collapse;font-size:.88rem;margin:8px 0;">
<tr><td colspan="4" style="background:#1a1a2e;color:white;text-align:center;padding:12px;font-size:1.05rem;font-weight:bold;letter-spacing:.15em;">금일 안전 일지</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;width:15%;">작성 일자</td>
<td style="padding:6px;border:1px solid #aaa;width:35%;">{daily.get("date","")}</td>
<td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;width:15%;">관리자</td>
<td style="padding:6px;border:1px solid #aaa;width:35%;">{daily.get("manager","")}</td></tr>
<tr><td colspan="4" style="background:#e8eaf6;font-weight:bold;padding:7px;border:1px solid #aaa;">1. 기본 사항</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">투입 인원</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("workers","")}</td>
<td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">장비 현황</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("equipment","")}</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">주요 작업 내용</td>
<td colspan="3" style="padding:6px;border:1px solid #aaa;">{daily.get("work_process","")}</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">작업 위치</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("location","")}</td>
<td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">공종 시간</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("work_time","")}</td></tr>
<tr><td colspan="4" style="background:#e8eaf6;font-weight:bold;padding:7px;border:1px solid #aaa;">2. 특이 사항</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">전일 미조치</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("prev_issues","없음")}</td>
<td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">주변 간섭</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("nearby_interference","없음")}</td></tr>
<tr><td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">신규 인원</td>
<td style="padding:6px;border:1px solid #aaa;">{daily.get("new_workers","없음")}</td>
<td style="background:#e8eaf6;font-weight:bold;padding:6px;border:1px solid #aaa;">날씨</td>
<td style="padding:6px;border:1px solid #aaa;">{ws}</td></tr>
<tr><td colspan="4" style="background:#e8eaf6;font-weight:bold;padding:7px;border:1px solid #aaa;">3. 위험 요인 및 안전 조치 (법규 기반)</td></tr>
{risk_html}
<tr><td colspan="4" style="background:#e8eaf6;font-weight:bold;padding:7px;border:1px solid #aaa;">4. TBM 메시지</td></tr>
<tr><td colspan="4" style="background:#fff8e1;padding:16px;border:2px solid #ffc107;">{tbm}</td></tr>
<tr><td colspan="4" style="text-align:center;padding:10px;border:1px solid #aaa;background:#fafafa;">
관리자 서명 (인): &nbsp;&nbsp;{daily.get("manager","")}&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</td></tr>
</table>"""

def save_report(rtype,label,path,content,rdate):
    p_,z_=pid(),zone(); ensure_zd(p_,z_)
    zd=SS.get_zone_data()
    zd[p_][z_]["reports"].append({"id":str(uuid.uuid4())[:8],"type":rtype,"label":label,"date":rdate,"path":path,"content":content})
    SS.set_zone_data(zd); st.session_state.report_content=""

# ══════════════════════════════════════════════════════════════
# 금일 안전 일지 생성
# ══════════════════════════════════════════════════════════════
def page_gen_daily_log():
    daily=st.session_state.daily_input
    st.markdown(f"## 금일 안전 일지 — {zone()}")
    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 안전"
        st.markdown("---"); st.session_state.selected_laws=law_ui(query)
        if st.button("금일 안전 일지 작성",type="primary",use_container_width=True):
            with st.spinner("작성 중입니다..."):
                st.session_state.report_content=generate_daily_log(daily,st.session_state.selected_laws)
            st.rerun()
    else:
        daily=st.session_state.daily_input
        st.markdown("### 보고서 확인 및 수정")
        st.markdown(render_daily_log_html(daily,st.session_state.report_content),unsafe_allow_html=True)
        with st.expander("내용 직접 수정"):
            edited=st.text_area("",value=st.session_state.report_content,height=300,label_visibility="collapsed")
            if st.button("수정 적용"): st.session_state.report_content=edited; st.rerun()
        st.markdown("---")
        c1,c2,c3=st.columns(3)
        if c1.button("PDF로 저장",type="primary",use_container_width=True):
            with st.spinner("PDF 저장 중..."):
                path=save_daily_log_pdf(daily,st.session_state.report_content,proj()["name"],st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            if os.path.exists(path):
                with open(path,"rb") as f_:
                    st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
            save_report("daily","금일 안전 일지",path,st.session_state.report_content,daily["date"])
            go("daily_input")
        if c2.button("다시 작성",use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]; st.rerun()

# ══════════════════════════════════════════════════════════════
# 안전 점검 체크리스트
# ══════════════════════════════════════════════════════════════
def page_gen_checklist():
    daily=st.session_state.daily_input
    st.markdown(f"## 안전 점검 체크리스트 — {zone()}")
    if not st.session_state.report_content:
        query=f"{daily.get('work_process','')} {daily.get('location','')} 점검"
        st.markdown("---"); st.session_state.selected_laws=law_ui(query)
        if st.button("안전 점검 체크리스트 작성",type="primary",use_container_width=True):
            with st.spinner("작성 중입니다..."):
                st.session_state.report_content=generate_checklist(daily,st.session_state.selected_laws)
            st.rerun()
    else:
        daily=st.session_state.daily_input
        st.markdown("### 보고서 확인 및 수정")
        st.text_area("",value=st.session_state.report_content,height=400,disabled=True,label_visibility="collapsed")
        with st.expander("내용 직접 수정"):
            edited=st.text_area("수정",value=st.session_state.report_content,height=300,label_visibility="collapsed")
            if st.button("수정 적용"): st.session_state.report_content=edited; st.rerun()
        st.markdown("---")
        c1,c2=st.columns(2)
        if c1.button("PDF로 저장",type="primary",use_container_width=True):
            with st.spinner("PDF 저장 중..."):
                from pdf_utils import save_checklist_pdf
                path=save_checklist_pdf(st.session_state.report_content,daily["date_c"],proj()["name"],st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            if os.path.exists(path):
                with open(path,"rb") as f_:
                    st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
            save_report("checklist","안전 점검 체크리스트",path,st.session_state.report_content,daily["date"])
            go("zone_board")
        if c2.button("다시 작성",use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]; st.rerun()

# ══════════════════════════════════════════════════════════════
# 사고 보고서
# ══════════════════════════════════════════════════════════════
def page_accident_form():
    st.markdown(f"## 사고 보고서 — {zone()}")
    acc=st.session_state.accident_input; p=proj()

    if not st.session_state.report_content:
        st.markdown("""<div class='info'>* 표시가 있는 항목은 반드시 입력해 주세요. 미입력 항목은 AI가 작업 내용을 바탕으로 채워 넣습니다.</div>""",unsafe_allow_html=True)

        # 기본 정보 (모두 필수)
        st.markdown('<p class="sec-label">기본 정보</p>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        wd=c1.date_input("작성 일자 *",value=date.today())
        pname=c2.text_input("현장명 *",value=p.get("name",""))
        c3,c4=st.columns(2)
        wpos=c3.text_input("작성자 직위 *",value=acc.get("writer_position",""),placeholder="예: 안전관리자")
        wname=c4.text_input("작성자 성명 *",value=acc.get("writer_name",""))

        # 사고 현장 정보
        st.markdown('<p class="sec-label">사고 현장 정보</p>',unsafe_allow_html=True)
        c1,c2=st.columns(2)
        try: adf=datetime.strptime(acc.get("accident_date",""),"%Y-%m-%d").date()
        except: adf=date.today()
        adt_date=c1.date_input("사고 발생 일자 *",value=adf)
        hours_a=[f"{h:02d}" for h in range(0,24)]; mins_a=["00","10","20","30","40","50"]
        tc1,tc2=c1.columns(2)
        sh_=acc.get("accident_time","14:00").split(":")[0] if acc.get("accident_time") else "14"
        sm_=acc.get("accident_time","14:00").split(":")[-1] if acc.get("accident_time") else "00"
        adt_h=tc1.selectbox("시 *",hours_a,index=hours_a.index(sh_) if sh_ in hours_a else 14,key="adt_h")
        adt_m=tc2.selectbox("분 *",mins_a,index=mins_a.index(sm_) if sm_ in mins_a else 0,key="adt_m")
        adt_time=f"{adt_h}:{adt_m}"
        loc=c2.text_input("작업 장소",value=acc.get("location",""))
        cobj=c2.text_input("기인물",value=acc.get("cause_object",""),placeholder="예: 갱폼")
        atype=c1.selectbox("발생 형태",["추락","낙하","감전","협착","충돌","화재·폭발","기타"])

        # 재해자 정보 (발생형태와 상해부위 사이)
        st.markdown('<p class="sec-label">재해자 정보</p>',unsafe_allow_html=True)
        c1,c2,c3=st.columns(3)
        sub=c1.text_input("협력업체명",value=acc.get("subcontractor",""))
        vn=c2.text_input("재해자 성명",value=acc.get("victim_name",""))
        hd=c3.text_input("채용일",value=acc.get("hire_date",""),placeholder="예: 2025-01-15")

        c4,c5=st.columns(2)
        ip=c4.text_input("상해 부위",value=acc.get("injury_part",""),placeholder="예: 우측 하지")
        it_=c5.text_input("상해 종류",value=acc.get("injury_type",""),placeholder="예: 골절")

        # 작업 내용 및 과정 (필수)
        st.markdown('<p class="sec-label">작업 내용 및 과정 *</p>',unsafe_allow_html=True)
        wp_=st.text_area("",value=acc.get("work_process",""),height=100,
                          placeholder="사고 발생 전 작업 단계를 순서대로 기술해주세요.",
                          label_visibility="collapsed")

        # 재해 발생 개요 (필수)
        st.markdown('<p class="sec-label">재해 발생 개요 *</p>',unsafe_allow_html=True)
        ov=st.text_area("",value=acc.get("overview",""),height=100,
                         placeholder="자세히 기술해주세요. (언제, 어디서, 누가, 무엇을, 어떻게, 왜)",
                         label_visibility="collapsed")

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

        # 준거 기준 선택
        if atype and loc:
            st.markdown("---"); st.session_state.selected_laws=law_ui(f"{atype} {loc} 산업재해")

        # 필수 항목 체크
        basic_required=[("작성자 직위",wpos),("작성자 성명",wname)]
        scene_required=[("사고 발생 일자",str(adt_date)),("사고 발생 시분",adt_time)]
        content_required=[("작업 내용 및 과정",wp_),("재해 발생 개요",ov)]
        all_required=basic_required+scene_required+content_required
        missing=[n for n,v in all_required if not v]

        if missing:
            for n,v in all_required:
                if not v:
                    st.markdown(f'<span class="req">{n} 항목을 입력해 주세요.</span>',unsafe_allow_html=True)

        if st.button("사고 보고서 작성",type="primary",disabled=bool(missing),use_container_width=True):
            with st.spinner("AI가 보고서를 작성 중입니다..."):
                st.session_state.report_content=generate_accident_report(new_acc,st.session_state.selected_laws)
            st.rerun()
    else:
        acc=st.session_state.accident_input
        st.markdown("### 보고서 확인 및 수정")
        edited=st.text_area("",value=st.session_state.report_content,height=500,label_visibility="collapsed")
        st.markdown("---")
        c1,c2,c3=st.columns(3)
        if c1.button("PDF로 저장",type="primary",use_container_width=True):
            with st.spinner("PDF 저장 중..."):
                path=save_accident_form_pdf(acc,edited,st.session_state.pdf_save_dir)
            st.markdown(f'<div class="ok">PDF 저장 완료: <b>{path}</b></div>',unsafe_allow_html=True)
            if os.path.exists(path):
                with open(path,"rb") as f_:
                    st.download_button("PDF 다운로드",f_.read(),file_name=os.path.basename(path),mime="application/pdf")
            p_,z_=pid(),zone(); ensure_zd(p_,z_)
            zd=SS.get_zone_data(); zd[p_][z_]["accidents"].append(acc); SS.set_zone_data(zd)
            st.session_state.report_content=""
        if c2.button("수정 저장",use_container_width=True):
            st.session_state.report_content=edited; st.rerun()
        if c3.button("다시 작성",use_container_width=True):
            st.session_state.report_content=""; st.session_state.selected_laws=[]; st.session_state.law_candidates=[]; st.rerun()

# ══════════════════════════════════════════════════════════════
# Chatbot
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