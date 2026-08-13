"""HTTP client for the BACII math backend (auth-aware)."""
import requests

BACKEND_URL = "http://localhost:8016"

_access_token = None
_refresh_token = None


def _set_tokens(data):
    global _access_token, _refresh_token
    _access_token = data.get("access_token")
    _refresh_token = data.get("refresh_token")


def _headers():
    return {"Authorization": f"Bearer {_access_token}"} if _access_token else {}


def _raise_for_status(resp):
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise RuntimeError(detail)


def signup(email, password):
    resp = requests.post(f"{BACKEND_URL}/auth/signup", json={"email": email, "password": password}, timeout=30)
    _raise_for_status(resp)
    _set_tokens(resp.json())
    return resp.json()


def login(email, password):
    resp = requests.post(f"{BACKEND_URL}/auth/login", json={"email": email, "password": password}, timeout=30)
    _raise_for_status(resp)
    _set_tokens(resp.json())
    return resp.json()


def refresh():
    resp = requests.post(f"{BACKEND_URL}/auth/refresh", json={"refresh_token": _refresh_token}, timeout=30)
    _raise_for_status(resp)
    _set_tokens(resp.json())
    return resp.json()


def _request(method, path, json=None, timeout=60):
    resp = requests.request(method, f"{BACKEND_URL}{path}", json=json, headers=_headers(), timeout=timeout)
    if resp.status_code == 401 and _refresh_token:
        refresh()
        resp = requests.request(method, f"{BACKEND_URL}{path}", json=json, headers=_headers(), timeout=timeout)
    _raise_for_status(resp)
    return resp.json()


def generate_question(generation_mode="templates", difficulty="medium"):
    return _request("POST", "/problems/generate",
                    {"generation_mode": generation_mode, "difficulty": difficulty}, timeout=90)


def grade(question_id, user_answer):
    return _request("POST", "/problems/grade",
                    {"question_id": question_id, "user_answer": user_answer}, timeout=90)


def explain(question_id):
    return _request("POST", "/problems/explain", {"question_id": question_id}, timeout=180)
