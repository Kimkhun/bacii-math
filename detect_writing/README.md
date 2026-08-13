# Digital Math Writing Detector

Detects numbers, math symbols, and math functions as you write them by hand
(with a mouse/stylus) on a digital canvas, using a local vision LLM to
transcribe the equation into structured JSON.

## Tech stack

| Layer            | Choice                                   | Notes |
|-------------------|-------------------------------------------|-------|
| UI / canvas        | Python `tkinter` (stdlib)                | Drawing surface, live strokes, side panel for results |
| Image handling      | `Pillow` (PIL)                            | Mirrors on-screen strokes into an in-memory image that gets saved as a PNG snapshot |
| Vision inference    | [Ollama](https://ollama.com) local server, model `qwen2.5vl:7b` | Runs fully locally, no cloud calls |
| HTTP client         | `requests`                                | Talks to Ollama's REST API (`/api/generate`) |
| Detection trigger   | Idle-timer debounce (1.2s after last stroke) | Runs in a background thread so the UI never freezes |

## How it works

1. You draw on the Tkinter canvas; every stroke is mirrored onto a Pillow
   image in memory.
2. Once you stop drawing for ~1.2 seconds, the canvas is saved as a PNG to
   the scratch directory and handed to `vision_client.recognize_math()`.
3. That function base64-encodes the image and sends it to the local Ollama
   server (`http://localhost:11434/api/generate`) with a prompt that
   restricts the model to transcribing digits, operators, variables, and
   math functions (ignoring stray marks).
4. Ollama returns JSON (`raw_text`, `latex`, `tokens`, `confidence`), which
   is parsed and rendered in the side panel.

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.com) installed and running locally
- The vision model pulled:
  ```bash
  ollama pull qwen2.5vl:7b
  ```
- Python packages:
  ```bash
  pip install pillow requests
  ```
  (`tkinter` ships with most Python installs; on Debian/Ubuntu you may need
  `sudo apt install python3-tk` if it's missing.)

## Install & run

```bash
# 1. Make sure the Ollama server is running (usually starts automatically,
#    or run it explicitly):
ollama serve &

# 2. From the project directory, launch the app:
cd /home/lavid/writing_detect
python3 app.py
```

A window opens with a white canvas on the left and a results panel on the
right. Write a math expression (e.g. `y = ax + b`) with your mouse, pause
briefly, and the detected equation + structured JSON will appear on the
right. Use **Clear** to reset the canvas or **Detect Now** to force
detection immediately instead of waiting for the idle timer.

## Files

- `app.py` — Tkinter app: canvas, stroke tracking, idle-detection trigger, results UI.
- `vision_client.py` — Builds the prompt, calls the local Ollama API, parses the JSON response.

## Checklist — what was done today (2026-08-12)

- [x] Checked locally installed Ollama models and picked `qwen2.5vl:7b` as the vision model
- [x] Built `vision_client.py` to send an image to Ollama and parse a structured JSON response (`raw_text`, `latex`, `tokens`, `confidence`)
- [x] Built `app.py`, a Tkinter canvas app for real-time digital writing with mouse/stylus input
- [x] Wired up an idle-timer debounce so detection auto-fires ~1.2s after the user stops writing (runs in a background thread, non-blocking)
- [x] Added manual "Detect Now" and "Clear" controls
- [x] Verified the end-to-end pipeline with a synthetic `y = ax + b` test image — confirmed correct JSON output
- [x] Syntax-checked `app.py`
- [x] Wrote this README

## Known limitations / not yet done

- [ ] Not tested with real mouse-drawn handwriting (only synthetic typed-text image was verified end-to-end)
- [ ] No support for touch/stylus devices beyond standard mouse events (should work the same via OS-level translation, but unverified)
- [ ] No history/log of previously detected equations across sessions
- [ ] Only handles single equations per canvas — multi-line or multi-equation writing untested
- [ ] Broader "digital writing" detection (letters, words, general text) is out of scope for now, per current focus on numbers/math only
