"""HTTP client for the BACII math backend."""
import requests

BACKEND_URL = "http://localhost:8016"


def generate_question(generation_mode="templates", difficulty="medium"):
    resp = requests.post(
        f"{BACKEND_URL}/problems/generate",
        json={"generation_mode": generation_mode, "difficulty": difficulty},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def grade(question_type, a, b, user_answer):
    resp = requests.post(
        f"{BACKEND_URL}/grade",
        json={"question_type": question_type, "a": a, "b": b, "user_answer": user_answer},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def explain(question_type, a, b, use_ai=True):
    resp = requests.post(
        f"{BACKEND_URL}/explain",
        json={"question_type": question_type, "a": a, "b": b, "use_ai": use_ai},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()
