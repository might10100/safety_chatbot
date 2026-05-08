import os, json
from dotenv import load_dotenv
import anthropic
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from prompts import (LAW_SEARCH_PROMPT, DAILY_LOG_PROMPT,
                     CHECKLIST_PROMPT, ACCIDENT_REPORT_PROMPT,
                     LAW_SELECTION_PROMPT)

load_dotenv()

DB_PATH     = "db"
EMBED_MODEL = "jhgan/ko-sroberta-multitask"
_db = None
_client = None

def load_resources():
    global _db, _client
    if _db is None:
        emb = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        _db = FAISS.load_local(DB_PATH, emb, allow_dangerous_deserialization=True)
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("❌ .env 파일에 ANTHROPIC_API_KEY가 없습니다.")
        _client = anthropic.Anthropic(api_key=key)

def retrieve(query: str, top_k: int = 5) -> list:
    load_resources()
    docs = _db.similarity_search_with_score(query, k=top_k)
    return [doc.page_content for doc, score in docs if score < 100.0]

def get_law_candidates(query: str) -> list:
    sources = retrieve(query, top_k=8)
    if not sources:
        return []
    context = "\n\n---\n\n".join(sources)
    raw = _call_claude(LAW_SELECTION_PROMPT,
                       f"[현장 데이터]\n{query}\n\n[검색된 법령 조문]\n{context}",
                       max_tokens=1024)
    try:
        clean = raw.strip()
        if "```" in clean:
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean).get("laws", [])
    except:
        return []

def _call_claude(system: str, user: str, max_tokens: int = 2500) -> str:
    load_resources()
    resp = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text

def law_search(question: str) -> dict:
    sources = retrieve(question)
    if not sources:
        return {"answer": "해당 내용은 DB에서 찾을 수 없습니다.\nlaw.go.kr 또는 kosha.or.kr을 직접 확인해 주세요.", "sources": [], "count": 0}
    context = "\n\n---\n\n".join(sources)
    answer = _call_claude(LAW_SEARCH_PROMPT, f"[질문]\n{question}\n\n[검색된 법령 조문]\n{context}")
    return {"answer": answer, "sources": sources, "count": len(sources)}

def generate_daily_log(daily: dict, selected_laws: list = None) -> str:
    query = f"{daily.get('work_process','')} {daily.get('location','')} 안전"
    sources = retrieve(query)
    law_ctx = ("\n\n[사용자 선택 법령]\n" + "\n".join(selected_laws)
               if selected_laws else
               "\n\n[검색된 법령 조문]\n" + "\n\n---\n\n".join(sources) if sources else "")
    w = daily.get("weather", {})
    weather_str = (f"평균기온 {w.get('temp_avg','-')}, 최고기온 {w.get('temp_max','-')}, "
                   f"평균습도 {w.get('humidity','-')}, 평균풍속 {w.get('wind_speed','-')}, "
                   f"최고풍속 {w.get('wind_max','-')} ({w.get('peak_time','-')} 도달)"
                   if w else "날씨 정보 없음")
    msg = f"""[데일리 입력]
날짜: {daily.get('date','')} / 관리자: {daily.get('manager','')}
인원: {daily.get('workers','')} / 장비: {daily.get('equipment','')}
공정시간: {daily.get('work_time','')}
작업위치: {daily.get('location','')} / 환경: {daily.get('env','')}
자재: {daily.get('materials','')}
날씨: {weather_str}
진행공정: {daily.get('work_process','')}
전일미조치: {daily.get('prev_issues','없음')}
주변간섭: {daily.get('nearby_interference','없음')}
신규인원: {daily.get('new_workers','없음')}
{law_ctx}"""
    return _call_claude(DAILY_LOG_PROMPT, msg)

def generate_checklist(daily: dict, selected_laws: list = None) -> str:
    query = f"{daily.get('work_process','')} {daily.get('location','')} 점검"
    sources = retrieve(query)
    law_ctx = ("\n\n[사용자 선택 법령]\n" + "\n".join(selected_laws)
               if selected_laws else
               "\n\n[검색된 법령 조문]\n" + "\n\n---\n\n".join(sources) if sources else "")
    w = daily.get("weather", {})
    msg = f"""[현장 데이터]
공종: {daily.get('work_process','')} / 위치: {daily.get('location','')}
환경: {daily.get('env','')} / 장비: {daily.get('equipment','')}
최고풍속: {w.get('wind_max','-')} ({w.get('peak_time','-')})
주변간섭: {daily.get('nearby_interference','없음')}
전일미조치: {daily.get('prev_issues','없음')}
자재: {daily.get('materials','')}
{law_ctx}"""
    return _call_claude(CHECKLIST_PROMPT, msg)

def generate_accident_report(acc: dict, selected_laws: list = None) -> str:
    query = f"{acc.get('accident_type','')} {acc.get('location','')} 산업재해"
    sources = retrieve(query)
    law_ctx = ("\n\n[사용자 선택 법령]\n" + "\n".join(selected_laws)
               if selected_laws else
               "\n\n[검색된 법령 조문]\n" + "\n\n---\n\n".join(sources) if sources else "")
    msg = f"""[사고 입력]
작성일자: {acc.get('write_date','')} / 현장명: {acc.get('project_name','')}
작성자: {acc.get('writer_position','')} {acc.get('writer_name','')}
현장소장: {acc.get('site_manager','')} / 공사과장: {acc.get('const_manager','')} / 담당기사: {acc.get('engineer','')}
협력업체: {acc.get('subcontractor','')} / 공사종류: {acc.get('work_type','')}
재해자: {acc.get('victim_name','')} / 직종: {acc.get('victim_job','')} / 채용일: {acc.get('hire_date','')}
사고일시: {acc.get('accident_datetime','')}
작업장소: {acc.get('location','')} / 기인물: {acc.get('cause_object','')}
발생형태: {acc.get('accident_type','')}
상해부위: {acc.get('injury_part','')} / 상해종류: {acc.get('injury_type','')}
재해개요: {acc.get('overview','')}
직접원인: {acc.get('direct_cause','')}
작업과정: {acc.get('work_process','')}
{law_ctx}"""
    return _call_claude(ACCIDENT_REPORT_PROMPT, msg, max_tokens=3000)
