"""
shared_state.py — 멀티유저 공유 상태 (파일 영속화)
재배포/재시작 후에도 프로젝트·구역 데이터가 유지되도록 JSON 파일에 저장한다.
"""
import json, os

_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_state.json")
_DEFAULT = {"projects": {}, "zone_data": {}, "archive": {}}

def _load():
    try:
        with open(_FILE, encoding="utf-8") as f:
            d = json.load(f)
        return {k: d.get(k, {}) for k in _DEFAULT}
    except Exception:
        return {k: {} for k in _DEFAULT}

_state = _load()

def _save():
    try:
        with open(_FILE, "w", encoding="utf-8") as f:
            json.dump(_state, f, ensure_ascii=False)
    except Exception:
        pass

def get_projects():   return _state["projects"]
def get_zone_data():  return _state["zone_data"]
def get_archive():    return _state["archive"]

def set_projects(v):  _state["projects"] = v; _save()
def set_zone_data(v): _state["zone_data"] = v; _save()
def set_archive(v):   _state["archive"] = v; _save()

def get_all():        return _state
def update(d):        _state.update(d); _save()
