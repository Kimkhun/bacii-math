# Render image for lesson animations: the pinned official Manim image (Python,
# Manim, TeX Live) + SymPy, so every scene can check the answer it shows
# against the same CAS the grader uses, + a static ffmpeg for transcoding.
FROM manimcommunity/manim:v0.21.0
USER root
RUN pip install --no-cache-dir "sympy==1.14.0" "imageio-ffmpeg==0.6.0"
USER manimuser
