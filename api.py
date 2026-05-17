from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from chain_search import load_resources, law_search, get_law_candidates, generate_daily_log, generate_checklist, generate_accident_report
from weather import fetch_weather

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_resources()

class QuestionRequest(BaseModel):
    question: str

class LawCandidatesRequest(BaseModel):
    question: str

class DailyLogRequest(BaseModel):
    project: str
    date: str
    weather: Optional[str] = ""
    workers: Optional[int] = 0
    work_content: Optional[str] = ""
    equipment: Optional[str] = ""
    risk: Optional[str] = ""
    law_ids: Optional[list] = []

class ChecklistRequest(BaseModel):
    project: str
    date: str
    items: Optional[list] = []
    law_ids: Optional[list] = []

class AccidentReportRequest(BaseModel):
    project: str
    date: str
    accident_type: Optional[str] = ""
    description: Optional[str] = ""
    law_ids: Optional[list] = []

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/law-search")
def api_law_search(req: QuestionRequest):
    result = law_search(req.question)
    return {"answer": result}

@app.post("/law-candidates")
def api_law_candidates(req: LawCandidatesRequest):
    candidates = get_law_candidates(req.question)
    return {"candidates": candidates}

@app.post("/daily-log")
def api_daily_log(req: DailyLogRequest):
    result = generate_daily_log(req.dict())
    return {"result": result}

@app.post("/checklist")
def api_checklist(req: ChecklistRequest):
    result = generate_checklist(req.dict())
    return {"result": result}

@app.post("/accident-report")
def api_accident_report(req: AccidentReportRequest):
    result = generate_accident_report(req.dict())
    return {"result": result}

@app.get("/weather")
def api_weather(district: str = "서울"):
    return fetch_weather(district)
