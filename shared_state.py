"""
shared_state.py — 멀티유저 공유 상태 (모듈 레벨 변수로 세션 간 공유)
"""
_state = {
    "projects": {},
    "zone_data": {},
    "archive": {},
}

def get_projects():   return _state["projects"]
def get_zone_data():  return _state["zone_data"]
def get_archive():    return _state["archive"]

def set_projects(v):  _state["projects"] = v
def set_zone_data(v): _state["zone_data"] = v
def set_archive(v):   _state["archive"] = v

def get_all():        return _state
def update(d):        _state.update(d)