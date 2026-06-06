import os, json, unicodedata
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
_p1_chunks: list = []

def load_resources():
    global _db, _client, _p1_chunks
    if _db is None:
        emb = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        _db = FAISS.load_local(DB_PATH, emb, allow_dangerous_deserialization=True)
        _P1_SRC = ("산업안전보건기준에 관한 규칙", "산업안전보건법", "중대재해 처벌")
        for _d in _db.docstore._dict.values():
            _s = unicodedata.normalize("NFC", _d.metadata.get("source", ""))
            if any(_p in _s for _p in _P1_SRC):
                _p1_chunks.append((_s, unicodedata.normalize("NFC", _d.page_content)))
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise EnvironmentError("❌ .env 파일에 ANTHROPIC_API_KEY가 없습니다.")
        _client = anthropic.Anthropic(api_key=key)

def _clean_chunk(content: str) -> str:
    """법제처 페이지 헤더 줄 제거 후 실제 조문 내용만 반환"""
    import re as _re
    cleaned = [l for l in content.split("\n")
               if not _re.match(r"법제처\s+\d+\s+국가법령정보센터", l.strip())]
    return "\n".join(cleaned).strip()

def _semantic_p1(query: str, top_n: int = 6, fetch_k: int = 50) -> list:
    load_resources()
    _P1 = ("산업안전보건기준에 관한 규칙", "산업안전보건법", "중대재해 처벌")
    docs = _db.similarity_search_with_score(query, k=fetch_k)
    out, seen = [], set()
    for doc, score in docs:
        if score >= 100.0: continue
        src = unicodedata.normalize("NFC", doc.metadata.get("source", ""))
        if not any(p in src for p in _P1): continue
        content = _clean_chunk(unicodedata.normalize("NFC", doc.page_content))
        key = content[:80]
        if key in seen: continue
        seen.add(key)
        first_jo = next(iter(__import__("re").findall(r"제\d+조", content)), "")
        tag = f"[출처: {src.replace('.pdf','')}{'  |  시작조: '+first_jo if first_jo else ''}]"
        out.append(f"{tag}\n{content}")
        if len(out) >= top_n: break
    return out

def _keyword_p1(query: str, top_n: int = 2) -> list:
    load_resources()
    _sfx = ["에서","에게","으로","로부터","보다","처럼","까지","부터","마다","께서","라도",
            "하여","하고","하는","한","를","을","이","가","은","는","의","과","와","도","만","로","에","서"]
    _stop = {"설치","기준","사항","경우","관련","규정","해당","작업","사업","사업주","근로자",
             "방법","조치","안전","관리","사용","이상","이하","다음","의한","위한","따른"}
    _syn = {"틈새":["틈새","틈"],"자재":["자재","재료"],"방지망":["방지망","방호망"],
            "추락방지망":["추락방지망","추락방호망"],"추락방호망":["추락방호망","추락방지망"]}
    def _strip(w):
        for s in sorted(_sfx, key=len, reverse=True):
            if w.endswith(s) and len(w)-len(s) >= 2: return w[:-len(s)]
        return w
    import re as _re
    raw_kws = list({_strip(w) for w in query.replace("?","").replace("!","").split()
                   if len(_strip(w)) >= 2 and _strip(w) not in _stop})
    expanded = list(set(sum([_syn.get(k,[k]) for k in raw_kws],[])))
    long_kws = [k for k in expanded if len(k) >= 3]
    if not long_kws: return []
    scored = []
    for src, raw_content in _p1_chunks:
        content = _clean_chunk(raw_content)
        if len(content) < 80: continue
        조cnt = len(_re.findall(r"제\d+조", content))
        if 조cnt >= 6 and len(content) < 조cnt * 30: continue
        if not any(k in content for k in long_kws): continue
        scored.append((sum(len(k) for k in expanded if k in content), src, content))
    scored.sort(key=lambda x: -x[0])
    out, seen = [], set()
    for _, src, content in scored:
        key = content[:80]
        if key in seen: continue
        seen.add(key)
        first_jo2 = next(iter(__import__("re").findall(r"제\d+조", content)), "")
        tag2 = f"[출처: {src.replace('.pdf','')}{'  |  시작조: '+first_jo2 if first_jo2 else ''}]"
        out.append(f"{tag2}\n{content}")
        if len(out) >= top_n: break
    return out

def retrieve(query: str, top_k: int = 5) -> list:
    load_resources()
    docs = _db.similarity_search_with_score(query, k=top_k)
    out = []
    for doc, score in docs:
        if score < 100.0:
            src = unicodedata.normalize("NFC", (doc.metadata or {}).get("source", "")).replace(".pdf", "")
            content = _clean_chunk(unicodedata.normalize("NFC", doc.page_content))
            first_jo = next(iter(__import__("re").findall(r"제\d+조", content)), "")
            tag = f"[출처: {src}{'  |  시작조: '+first_jo if first_jo else ''}]"
            out.append(f"{tag}\n{content}" if src else content)
    return out

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
    import time
    load_resources()
    for attempt in range(3):
        try:
            resp = _client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        except Exception as e:
            if attempt < 2:
                time.sleep(10 * (attempt + 1))
            else:
                raise

def law_search(question: str) -> dict:
    p1  = _semantic_p1(question, top_n=6, fetch_k=50)
    kw  = _keyword_p1(question, top_n=2)
    gen = retrieve(question, top_k=12)
    merged, seen = [], set()
    for s in (p1 + kw + gen):
        key = s[:100]
        if key not in seen:
            seen.add(key); merged.append(s)
    if not merged:
        return {"answer": "해당 내용은 DB에서 찾을 수 없습니다.\nlaw.go.kr 또는 kosha.or.kr을 직접 확인해 주세요.", "sources": [], "count": 0}
    merged = merged[:20]
    context = "\n\n---\n\n".join(merged)
    answer = _call_claude(LAW_SEARCH_PROMPT, f"[질문]\n{question}\n\n[검색된 법령 조문]\n{context}")
    return {"answer": answer, "sources": merged, "count": len(merged)}

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
{law_ctx}"""
    return _call_claude(ACCIDENT_REPORT_PROMPT, msg, max_tokens=3000)
