"""BACII math practice app.

Generates a complex-number question from the backend, lets the user answer by
drawing on the canvas (handwriting -> Ollama vision transcription) or by typing,
grades the answer via the backend, and shows a step-by-step explanation.
"""
import json
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from PIL import Image, ImageDraw

from backend_client import explain, generate_question, grade
from vision_client import recognize_math

CANVAS_W, CANVAS_H = 700, 400
PEN_WIDTH = 6
IDLE_MS = 1200
SCRATCH_DIR = Path(__file__).resolve().parent / "scratchpad"
SNAPSHOT_PATH = SCRATCH_DIR / "canvas_snapshot.png"


class MathWritingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("BACII Math Practice")
        self.question = None

        self._build_ui()

        self.image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.last_x = None
        self.last_y = None
        self.idle_job = None
        self.has_new_strokes = False
        self.detecting = False

    def _build_ui(self):
        main = ttk.Frame(self.root, padding=8)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main)
        left.pack(side="left", fill="both", expand=True)

        controls = ttk.Frame(left)
        controls.pack(fill="x", pady=(0, 6))
        ttk.Button(controls, text="New Question", command=self._new_question).pack(side="left")
        self.mode_var = tk.StringVar(value="templates")
        ttk.Combobox(controls, textvariable=self.mode_var, values=["templates", "gemini"],
                     width=10, state="readonly").pack(side="left", padx=6)
        self.diff_var = tk.StringVar(value="medium")
        ttk.Combobox(controls, textvariable=self.diff_var, values=["easy", "medium", "hard"],
                     width=8, state="readonly").pack(side="left")

        self.question_var = tk.StringVar(value="Click 'New Question' to start.")
        ttk.Label(left, textvariable=self.question_var, font=("TkDefaultFont", 14, "bold"),
                  foreground="#222", wraplength=CANVAS_W).pack(anchor="w", pady=(0, 4))

        self.canvas = tk.Canvas(left, width=CANVAS_W, height=CANVAS_H, bg="white", cursor="pencil")
        self.canvas.pack(pady=6)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        btns = ttk.Frame(left)
        btns.pack(fill="x")
        ttk.Button(btns, text="Clear", command=self._clear).pack(side="left")
        ttk.Button(btns, text="Detect Now", command=self._trigger_detect).pack(side="left", padx=6)
        ttk.Button(btns, text="Explain", command=self._explain).pack(side="left")

        typed = ttk.Frame(left)
        typed.pack(fill="x", pady=(6, 0))
        ttk.Label(typed, text="Or type answer:").pack(side="left")
        self.answer_var = tk.StringVar()
        ttk.Entry(typed, textvariable=self.answer_var, width=22).pack(side="left", padx=6)
        ttk.Button(typed, text="Check", command=self._check_typed).pack(side="left")

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(left, textvariable=self.status_var, foreground="gray").pack(anchor="w", pady=(4, 0))

        right = ttk.Frame(main, padding=(12, 0, 0, 0))
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(right, text="Detected answer").pack(anchor="w")
        self.raw_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.raw_var, font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(0, 4))

        ttk.Label(right, text="Result").pack(anchor="w")
        self.result_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.result_var, font=("TkDefaultFont", 14, "bold")).pack(anchor="w", pady=(0, 8))

        ttk.Label(right, text="Explanation").pack(anchor="w")
        self.explain_box = tk.Text(right, width=48, height=14, wrap="word")
        self.explain_box.pack(fill="x")

        ttk.Label(right, text="Structured JSON").pack(anchor="w", pady=(8, 0))
        self.json_box = tk.Text(right, width=48, height=10, wrap="word")
        self.json_box.pack(fill="both", expand=True)

    def _on_press(self, event):
        self.last_x, self.last_y = event.x, event.y
        self._cancel_idle_timer()

    def _on_move(self, event):
        if self.last_x is not None:
            self.canvas.create_line(
                self.last_x, self.last_y, event.x, event.y,
                width=PEN_WIDTH, capstyle=tk.ROUND, smooth=True, fill="black",
            )
            self.draw.line(
                [self.last_x, self.last_y, event.x, event.y],
                fill="black", width=PEN_WIDTH, joint="curve",
            )
        self.last_x, self.last_y = event.x, event.y
        self.has_new_strokes = True

    def _on_release(self, event):
        self.last_x, self.last_y = None, None
        self._schedule_idle_timer()

    def _cancel_idle_timer(self):
        if self.idle_job is not None:
            self.root.after_cancel(self.idle_job)
            self.idle_job = None

    def _schedule_idle_timer(self):
        self._cancel_idle_timer()
        self.idle_job = self.root.after(IDLE_MS, self._trigger_detect)

    def _clear(self):
        self.canvas.delete("all")
        self.image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
        self.draw = ImageDraw.Draw(self.image)
        self.has_new_strokes = False
        self.raw_var.set("")
        self.result_var.set("")
        self.explain_box.delete("1.0", tk.END)
        self.json_box.delete("1.0", tk.END)
        self.status_var.set("Idle")

    def _new_question(self):
        mode = self.mode_var.get()
        diff = self.diff_var.get()
        self.status_var.set("Generating question...")
        threading.Thread(target=self._run_generate, args=(mode, diff), daemon=True).start()

    def _run_generate(self, mode, diff):
        try:
            question = generate_question(mode, diff)
            error = None
        except Exception as exc:
            question = None
            error = str(exc)
        self.root.after(0, self._on_question, question, error)

    def _on_question(self, question, error):
        if error:
            self.status_var.set(f"Error: {error}")
            return
        self.question = question
        self._clear()
        self.question_var.set(question["prompt"])
        self.status_var.set("Write your answer, then pause.")

    def _trigger_detect(self):
        self.idle_job = None
        if not self.has_new_strokes or self.detecting:
            return
        self.has_new_strokes = False
        self.detecting = True
        self.status_var.set("Detecting...")

        SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
        self.image.save(SNAPSHOT_PATH)

        threading.Thread(target=self._run_detection, daemon=True).start()

    def _run_detection(self):
        try:
            result = recognize_math(str(SNAPSHOT_PATH))
            error = None
        except Exception as exc:
            result = None
            error = str(exc)
        self.root.after(0, self._on_detection_done, result, error)

    def _on_detection_done(self, result, error):
        self.detecting = False
        if error:
            self.status_var.set(f"Error: {error}")
            return
        raw = (result.get("raw_text") or "").strip()
        self.raw_var.set(raw or "(nothing detected)")
        self.json_box.delete("1.0", tk.END)
        self.json_box.insert("1.0", json.dumps(result, indent=2))
        if raw:
            self._grade_answer(raw)
        else:
            self.status_var.set("Nothing detected.")

    def _check_typed(self):
        answer = self.answer_var.get().strip()
        if not answer:
            self.status_var.set("Type an answer first.")
            return
        self._grade_answer(answer)

    def _grade_answer(self, user_answer):
        if not self.question:
            self.status_var.set("Generate a question first.")
            return
        question = self.question
        self.status_var.set("Grading...")
        threading.Thread(target=self._run_grade, args=(question, user_answer), daemon=True).start()

    def _run_grade(self, question, user_answer):
        try:
            result = grade(question["question_type"], question["a"], question["b"], user_answer)
            error = None
        except Exception as exc:
            result = None
            error = str(exc)
        self.root.after(0, self._on_grade, result, error)

    def _on_grade(self, result, error):
        if error:
            self.status_var.set(f"Grade error: {error}")
            return
        if result["correct"]:
            self.result_var.set("Correct")
            self.status_var.set("Correct")
        else:
            self.result_var.set(f"Incorrect - expected {result['expected']}")
            self.status_var.set("Incorrect")

    def _explain(self):
        if not self.question:
            self.status_var.set("Generate a question first.")
            return
        question = self.question
        self.status_var.set("Explaining...")
        threading.Thread(target=self._run_explain, args=(question,), daemon=True).start()

    def _run_explain(self, question):
        try:
            result = explain(question["question_type"], question["a"], question["b"], use_ai=True)
            error = None
        except Exception as exc:
            result = None
            error = str(exc)
        self.root.after(0, self._on_explain, result, error)

    def _on_explain(self, result, error):
        if error:
            self.status_var.set(f"Explain error: {error}")
            return
        text = result.get("ai") or result.get("deterministic") or ""
        self.explain_box.delete("1.0", tk.END)
        self.explain_box.insert("1.0", text)
        self.status_var.set("Explanation ready.")


def main():
    root = tk.Tk()
    MathWritingApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
