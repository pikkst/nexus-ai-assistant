"""
Nexus Face — Looi-style animated AI assistant face.

Pure SVG generation. Zero external dependencies.
Emits raw SVG strings that can be rendered in any browser/Gradio/Tkinter.

Emotions: idle, listening, thinking, speaking, happy, sad, surprised, confused, sleeping
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class Emotion(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    HAPPY = "happy"
    SAD = "sad"
    SURPRISED = "surprised"
    CONFUSED = "confused"
    SLEEPING = "sleeping"


class BlinkState(Enum):
    OPEN = "open"
    CLOSING = "closing"
    CLOSED = "closed"
    OPENING = "opening"


@dataclass
class FaceConfig:
    """Configuration for the Nexus face rendering."""

    width: int = 400
    height: int = 500
    bg_color: str = "#1a1a2e"
    head_color: str = "#2d2d44"
    head_border: str = "#3d3d55"
    eye_white: str = "#f0f0f5"
    eye_border: str = "#dddde8"
    iris_color: str = "#2a8bcc"
    iris_light: str = "#6ec6ff"
    iris_dark: str = "#1a5a8a"
    pupil_color: str = "#0a0a1a"
    pupil_light: str = "#2a2a3a"
    highlight_color: str = "#ffffff"
    brow_color: str = "#1a1a2e"
    mouth_color: str = "#4a4a62"
    blush_color: str = "#ff6b8a"
    label_color: str = "#888899"
    label_sub_color: str = "#666677"


@dataclass
class FaceState:
    """Mutable state for animation parameters."""

    emotion: Emotion = Emotion.IDLE
    blink: BlinkState = BlinkState.OPEN
    blink_timer: int = 0
    gaze_x: float = 0.0  # -1.0 to 1.0
    gaze_y: float = 0.0  # -1.0 to 1.0
    mouth_open: float = 0.0  # 0.0 to 1.0
    eye_scale: float = 1.0  # 0.5 to 1.5
    talking_frame: int = 0
    time: float = 0.0


class NexusFace:
    """Looi-style animated face for the Nexus AI assistant.

    Usage:
        face = NexusFace()
        svg = face.render(Emotion.HAPPY)
        # or animate:
        state = FaceState(emotion=Emotion.LISTENING)
        svg = face.render_state(state)
    """

    def __init__(self, config: FaceConfig | None = None) -> None:
        self.config = config or FaceConfig()
        self.state = FaceState()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, emotion: Emotion | str = Emotion.IDLE) -> str:
        """Render the face as an SVG string for a given emotion.

        Args:
            emotion: Emotion enum value or string name.

        Returns:
            Complete SVG markup as a string.
        """
        if isinstance(emotion, str):
            emotion = Emotion(emotion)
        self.state.emotion = emotion
        return self._build_svg(self.state)

    def render_state(self, state: FaceState | None = None) -> str:
        """Render the face using a custom FaceState for animation."""
        s = state or self.state
        return self._build_svg(s)

    def animate(self, dt: float = 0.05) -> str:
        """Advance animation by dt seconds and return next SVG frame.

        Handles blinking, breathing, talking, and gaze jitter.
        """
        s = self.state
        s.time += dt

        # --- Blink ---
        if s.emotion != Emotion.SLEEPING:
            s.blink_timer += 1
            if s.blink == BlinkState.OPEN and s.blink_timer > 150:
                s.blink = BlinkState.CLOSING
                s.blink_timer = 0
            elif s.blink == BlinkState.CLOSING and s.blink_timer > 2:
                s.blink = BlinkState.CLOSED
                s.blink_timer = 0
            elif s.blink == BlinkState.CLOSED and s.blink_timer > 2:
                s.blink = BlinkState.OPENING
                s.blink_timer = 0
            elif s.blink == BlinkState.OPENING and s.blink_timer > 2:
                s.blink = BlinkState.OPEN
                s.blink_timer = 0
        else:
            s.blink = BlinkState.CLOSED

        # --- Gaze jitter (alive feel) ---
        if s.emotion not in (Emotion.SLEEPING, Emotion.THINKING):
            s.gaze_x = math.sin(s.time * 0.7) * 0.05
            s.gaze_y = math.sin(s.time * 0.5 + 0.3) * 0.03
        elif s.emotion == Emotion.THINKING:
            s.gaze_x = math.sin(s.time * 0.3) * 0.15
            s.gaze_y = -0.1 + math.sin(s.time * 0.4) * 0.05

        # --- Mouth for speaking ---
        if s.emotion == Emotion.SPEAKING:
            s.talking_frame += 1
            s.mouth_open = 0.3 + 0.4 * abs(math.sin(s.talking_frame * 0.5))
        elif s.emotion == Emotion.SURPRISED:
            s.mouth_open = 0.8
        else:
            s.mouth_open = max(0.0, s.mouth_open - 0.05)

        # --- Eye scale for surprise / squinting ---
        if s.emotion == Emotion.SURPRISED:
            s.eye_scale = 1.3
        elif s.emotion in (Emotion.HAPPY, Emotion.SAD):
            s.eye_scale = 0.85
        else:
            s.eye_scale = 1.0

        return self._build_svg(s)

    # ------------------------------------------------------------------
    # SVG building
    # ------------------------------------------------------------------

    def _build_svg(self, s: FaceState) -> str:
        cfg = self.config
        cx, cy = cfg.width // 2, cfg.height // 2

        # --- Eye parameters ---
        eye_h = 55 * s.eye_scale
        eye_w = 50 * s.eye_scale
        is_closed = s.blink in (BlinkState.CLOSED, BlinkState.CLOSING, BlinkState.OPENING)
        blink_h = 2 if s.blink in (BlinkState.CLOSED,) else (
            eye_h * 0.15 if s.blink in (BlinkState.CLOSING, BlinkState.OPENING) else eye_h
        )

        left_ex, left_ey = cx - 45, cy - 40
        right_ex, right_ey = cx + 45, cy - 40

        # Gaze offset
        gaze_off_x = s.gaze_x * 12
        gaze_off_y = s.gaze_y * 8

        # --- Mouth ---
        mouth_svg = self._build_mouth(s, cx, cy)

        # --- Eyebrows ---
        brows_svg = self._build_brows(s, cx, left_ex, left_ey, right_ex, right_ey)

        # --- Blush ---
        blush_svg = self._build_blush(s, cx, cy)

        # --- Eyes ---
        eyes_svg = self._build_eyes(
            s, cfg, left_ex, left_ey, right_ex, right_ey,
            eye_w, blink_h, gaze_off_x, gaze_off_y,
        )

        # --- Sleep Z's ---
        sleep_svg = ""
        if s.emotion == Emotion.SLEEPING:
            sleep_svg = self._build_sleep_zs(s, cx)

        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {cfg.width} {cfg.height}" width="{cfg.width}" height="{cfg.height}">
  <defs>
    <radialGradient id="irisGrad" cx="40%" cy="40%" r="50%">
      <stop offset="0%" stop-color="{cfg.iris_light}"/>
      <stop offset="60%" stop-color="{cfg.iris_color}"/>
      <stop offset="100%" stop-color="{cfg.iris_dark}"/>
    </radialGradient>
    <radialGradient id="pupilGrad" cx="40%" cy="40%" r="50%">
      <stop offset="0%" stop-color="{cfg.pupil_light}"/>
      <stop offset="100%" stop-color="{cfg.pupil_color}"/>
    </radialGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.15"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect x="0" y="0" width="{cfg.width}" height="{cfg.height}" fill="{cfg.bg_color}" rx="20" ry="20"/>

  <!-- Head -->
  <rect x="{cx - 140}" y="{cy - 190}" width="280" height="340" rx="60" ry="60"
        fill="{cfg.head_color}" stroke="{cfg.head_border}" stroke-width="3" filter="url(#shadow)"/>

  <!-- Forehead highlight -->
  <ellipse cx="{cx}" cy="{cy - 140}" rx="80" ry="25" fill="{cfg.head_border}" opacity="0.4"/>

  <!-- Blush -->
  {blush_svg}

  <!-- Eyebrows -->
  {brows_svg}

  <!-- Eyes -->
  {eyes_svg}

  <!-- Nose -->
  <path d="M{cx} {cy + 30} Q{cx - 5} {cy + 40} {cx} {cy + 45} Q{cx + 5} {cy + 40} {cx} {cy + 30}"
        fill="{cfg.head_border}" stroke="{cfg.head_border}" stroke-width="1" opacity="0.6"/>

  <!-- Mouth -->
  {mouth_svg}

  <!-- Sleep Z's -->
  {sleep_svg}

  <!-- Labels -->
  <text x="{cx}" y="{cfg.height - 60}" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="18" fill="{cfg.label_color}" font-weight="bold">NEXUS</text>
  <text x="{cx}" y="{cfg.height - 35}" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="13" fill="{cfg.label_sub_color}">{s.emotion.value}</text>
</svg>"""

    def _build_eyes(
        self, s: FaceState, cfg: FaceConfig,
        lx: int, ly: int, rx: int, ry: int,
        ew: float, bh: float, gox: float, goy: float,
    ) -> str:
        is_sleep = s.emotion == Emotion.SLEEPING
        if is_sleep:
            # Closed sleepy eyes
            return f"""
  <path d="M{lx - 35} {ly} Q{lx} {ly - 8} {lx + 35} {ly}" stroke="{cfg.eye_border}" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.6"/>
  <path d="M{rx - 35} {ry} Q{rx} {ry - 8} {rx + 35} {ry}" stroke="{cfg.eye_border}" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.6"/>"""

        if bh < 5:
            # Blink line
            return f"""
  <path d="M{lx - 35} {ly} Q{lx} {ly} {lx + 35} {ly}" stroke="{cfg.eye_border}" stroke-width="3" stroke-linecap="round" fill="none"/>
  <path d="M{rx - 35} {ry} Q{rx} {ry} {rx + 35} {ry}" stroke="{cfg.eye_border}" stroke-width="3" stroke-linecap="round" fill="none"/>"""

        iris_rx = 28 * (ew / 50)
        iris_ry = 32 * (bh / 55)
        pupil_rx = 14 * (ew / 50)
        pupil_ry = 16 * (bh / 55)

        return f"""
  <!-- Left eye -->
  <ellipse cx="{lx}" cy="{ly}" rx="{ew}" ry="{bh}" fill="{cfg.eye_white}" stroke="{cfg.eye_border}" stroke-width="2"/>
  <ellipse cx="{lx + gox}" cy="{ly + goy}" rx="{iris_rx}" ry="{iris_ry}" fill="url(#irisGrad)"/>
  <ellipse cx="{lx + gox}" cy="{ly + goy}" rx="{pupil_rx}" ry="{pupil_ry}" fill="url(#pupilGrad)"/>
  <ellipse cx="{lx + gox - 12}" cy="{ly + goy - 12}" rx="{10 * ew / 50}" ry="{12 * bh / 55}" fill="{cfg.highlight_color}" opacity="0.8"/>
  <ellipse cx="{lx + gox + 10}" cy="{ly + goy + 15}" rx="4" ry="5" fill="{cfg.highlight_color}" opacity="0.25"/>

  <!-- Right eye -->
  <ellipse cx="{rx}" cy="{ry}" rx="{ew}" ry="{bh}" fill="{cfg.eye_white}" stroke="{cfg.eye_border}" stroke-width="2"/>
  <ellipse cx="{rx + gox}" cy="{ry + goy}" rx="{iris_rx}" ry="{iris_ry}" fill="url(#irisGrad)"/>
  <ellipse cx="{rx + gox}" cy="{ry + goy}" rx="{pupil_rx}" ry="{pupil_ry}" fill="url(#pupilGrad)"/>
  <ellipse cx="{rx + gox - 12}" cy="{ry + goy - 12}" rx="{10 * ew / 50}" ry="{12 * bh / 55}" fill="{cfg.highlight_color}" opacity="0.8"/>
  <ellipse cx="{rx + gox + 10}" cy="{ry + goy + 15}" rx="4" ry="5" fill="{cfg.highlight_color}" opacity="0.25"/>"""

    def _build_brows(self, s: FaceState, cx: int, lx: int, ly: int, rx: int, ry: int) -> str:
        cfg = self.config
        brow_w = 55
        brow_style = self._brow_curves(s.emotion)

        # Left brow
        bl_start = f"M{lx - brow_w} {ly - 55 + brow_style['left_yoff']}"
        bl_ctrl = f"Q{lx - brow_w // 2} {ly - 70 + brow_style['left_arch']}"
        bl_end = f"{lx + brow_w} {ly - 55 + brow_style['left_yoff']}"

        # Right brow (mirror)
        br_start = f"M{rx + brow_w} {ry - 55 + brow_style['right_yoff']}"
        br_ctrl = f"Q{rx + brow_w // 2} {ry - 70 + brow_style['right_arch']}"
        br_end = f"{rx - brow_w} {ry - 55 + brow_style['right_yoff']}"

        return f"""
  <path d="{bl_start} {bl_ctrl} {bl_end}" stroke="{cfg.brow_color}" stroke-width="4" stroke-linecap="round" fill="none"/>
  <path d="{br_start} {br_ctrl} {br_end}" stroke="{cfg.brow_color}" stroke-width="4" stroke-linecap="round" fill="none"/>"""

    def _brow_curves(self, emotion: Emotion) -> dict:
        if emotion == Emotion.HAPPY:
            return {"left_yoff": -5, "left_arch": -5, "right_yoff": -5, "right_arch": -5}
        elif emotion == Emotion.SAD:
            return {"left_yoff": 5, "left_arch": -15, "right_yoff": 5, "right_arch": -15}
        elif emotion == Emotion.SURPRISED:
            return {"left_yoff": -15, "left_arch": 5, "right_yoff": -15, "right_arch": 5}
        elif emotion == Emotion.ANGRY if hasattr(emotion, 'ANGRY') else emotion == Emotion.CONFUSED:
            return {"left_yoff": -8, "left_arch": 5, "right_yoff": 3, "right_arch": -10}
        elif emotion == Emotion.THINKING:
            return {"left_yoff": -5, "left_arch": -5, "right_yoff": -12, "right_arch": 5}
        else:
            return {"left_yoff": 0, "left_arch": 0, "right_yoff": 0, "right_arch": 0}

    def _build_mouth(self, s: FaceState, cx: int, cy: int) -> str:
        cfg = self.config
        em = s.emotion
        mo = s.mouth_open

        if em == Emotion.SLEEPING:
            # Small open mouth
            return f"""
  <ellipse cx="{cx}" cy="{cy + 75}" rx="12" ry="8" fill="{cfg.mouth_color}" stroke="{cfg.mouth_color}" stroke-width="1" opacity="0.4"/>"""

        if em == Emotion.SURPRISED:
            h = 20 + mo * 15
            return f"""
  <ellipse cx="{cx}" cy="{cy + 70}" rx="18" ry="{h}" fill="#1a1a2e" stroke="{cfg.mouth_color}" stroke-width="2"/>"""

        if em == Emotion.HAPPY:
            return f"""
  <path d="M{cx - 30} {cy + 65} Q{cx} {cy + 90} {cx + 30} {cy + 65}" stroke="{cfg.mouth_color}" stroke-width="3" stroke-linecap="round" fill="none"/>
  <!-- Cheek dimples -->
  <path d="M{cx - 42} {cy + 70} Q{cx - 38} {cy + 65} {cx - 34} {cy + 70}" stroke="{cfg.mouth_color}" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.5"/>
  <path d="M{cx + 34} {cy + 70} Q{cx + 38} {cy + 65} {cx + 42} {cy + 70}" stroke="{cfg.mouth_color}" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.5"/>"""

        if em == Emotion.SAD:
            return f"""
  <path d="M{cx - 25} {cy + 75} Q{cx} {cy + 85} {cx + 25} {cy + 75}" stroke="{cfg.mouth_color}" stroke-width="3" stroke-linecap="round" fill="none"/>
  <!-- Frown lines -->
  <path d="M{cx - 30} {cy + 72} Q{cx - 28} {cy + 78} {cx - 25} {cy + 75}" stroke="{cfg.mouth_color}" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.3"/>"""

        if em == Emotion.SPEAKING:
            h = 8 + mo * 18
            return f"""
  <ellipse cx="{cx}" cy="{cy + 72}" rx="16" ry="{h}" fill="#1a1a2e" stroke="{cfg.mouth_color}" stroke-width="2"/>"""

        if em == Emotion.CONFUSED:
            return f"""
  <path d="M{cx - 15} {cy + 65} Q{cx} {cy + 75} {cx + 15} {cy + 72}" stroke="{cfg.mouth_color}" stroke-width="3" stroke-linecap="round" fill="none"/>
  <path d="M{cx + 15} {cy + 72} Q{cx + 25} {cy + 78} {cx + 35} {cy + 70}" stroke="{cfg.mouth_color}" stroke-width="3" stroke-linecap="round" fill="none" opacity="0.7"/>"""

        # Neutral / listening / thinking
        if em == Emotion.THINKING:
            return f"""
  <path d="M{cx - 25} {cy + 68} Q{cx} {cy + 75} {cx + 25} {cy + 68}" stroke="{cfg.mouth_color}" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <!-- Finger on chin implied by tilt -->"""

        # Default: gentle smile
        return f"""
  <path d="M{cx - 28} {cy + 68} Q{cx} {cy + 82} {cx + 28} {cy + 68}" stroke="{cfg.mouth_color}" stroke-width="2.5" stroke-linecap="round" fill="none"/>"""

    def _build_blush(self, s: FaceState, cx: int, cy: int) -> str:
        cfg = self.config
        em = s.emotion
        if em in (Emotion.HAPPY, Emotion.LISTENING):
            opacity = "0.2"
        elif em == Emotion.SURPRISED:
            opacity = "0.1"
        elif em == Emotion.SAD:
            opacity = "0.08"
        else:
            opacity = "0.15"
        return f"""
  <ellipse cx="{cx - 80}" cy="{cy + 20}" rx="22" ry="14" fill="{cfg.blush_color}" opacity="{opacity}"/>
  <ellipse cx="{cx + 80}" cy="{cy + 20}" rx="22" ry="14" fill="{cfg.blush_color}" opacity="{opacity}"/>"""

    def _build_sleep_zs(self, s: FaceState, cx: int) -> str:
        """Animated Z letters floating up while sleeping."""
        offset1 = math.sin(s.time * 1.2) * 5
        offset2 = math.sin(s.time * 1.5 + 1.0) * 6
        offset3 = math.sin(s.time * 1.8 + 2.0) * 7
        return f"""
  <text x="{cx + 80}" y="{cx - 180 + offset1}" font-family="Arial, sans-serif" font-size="28" fill="#6ec6ff" opacity="0.6" font-weight="bold">Z</text>
  <text x="{cx + 110}" y="{cx - 210 + offset2}" font-family="Arial, sans-serif" font-size="22" fill="#6ec6ff" opacity="0.4" font-weight="bold">Z</text>
  <text x="{cx + 135}" y="{cx - 235 + offset3}" font-family="Arial, sans-serif" font-size="16" fill="#6ec6ff" opacity="0.25" font-weight="bold">Z</text>"""


# ------------------------------------------------------------------
# Convenience demo
# ------------------------------------------------------------------

def generate_emotion_grid() -> str:
    """Generate an HTML page showing all emotions side by side."""
    face = NexusFace()
    rows = []
    for emotion in Emotion:
        svg = face.render(emotion)
        rows.append(f"""<div class="cell">
  {svg}
  <p>{emotion.value}</p>
</div>""")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Nexus Face — Emotion Grid</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ background: #0f0f1a; font-family: Arial, sans-serif; display: flex; flex-direction: column; align-items: center; padding: 40px 20px; }}
    h1 {{ color: #8888aa; margin-bottom: 30px; font-weight: 300; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 1300px; }}
    .cell {{ background: #151528; border-radius: 16px; padding: 20px; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }}
    .cell p {{ color: #8888aa; margin-top: 10px; font-size: 14px; text-transform: uppercase; letter-spacing: 2px; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
    @media (max-width: 500px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>Nexus Face — Expressions</h1>
  <div class="grid">
    {''.join(rows)}
  </div>
</body>
</html>"""
    return html


def generate_animated_demo() -> str:
    """Generate a self-contained HTML page with an animated Nexus face cycling emotions."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Nexus Face — Animated Demo</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #0f0f1a; font-family: Arial, sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
    #face-container { width: 400px; height: 500px; border-radius: 24px; overflow: hidden; box-shadow: 0 8px 40px rgba(0,0,0,0.4); margin-bottom: 24px; }
    #face-container svg { width: 100%; height: 100%; display: block; }
    .controls { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; max-width: 500px; }
    .controls button { background: #1e1e38; color: #aaaacc; border: 1px solid #2a2a44; padding: 10px 18px; border-radius: 10px; cursor: pointer; font-size: 13px; transition: all 0.2s; text-transform: uppercase; letter-spacing: 1px; }
    .controls button:hover { background: #2a2a44; color: #ffffff; border-color: #6ec6ff; }
    .controls button.active { background: #2a2a44; color: #6ec6ff; border-color: #6ec6ff; }
    #status { color: #55556a; margin-top: 20px; font-size: 13px; }
  </style>
</head>
<body>
  <div id="face-container"></div>
  <div class="controls" id="controls">
    <button data-emotion="idle" class="active">Idle</button>
    <button data-emotion="listening">Listening</button>
    <button data-emotion="thinking">Thinking</button>
    <button data-emotion="speaking">Speaking</button>
    <button data-emotion="happy">Happy</button>
    <button data-emotion="sad">Sad</button>
    <button data-emotion="surprised">Surprised</button>
    <button data-emotion="confused">Confused</button>
    <button data-emotion="sleeping">Sleeping</button>
  </div>
  <div id="status">Click an emotion above</div>

  <script>
    const EMOTIONS = ["idle","listening","thinking","speaking","happy","sad","surprised","confused","sleeping"];
    let currentEmotion = "idle";
    let frame = 0;
    const container = document.getElementById("face-container");

    // Load face SVG from API or generate client-side
    // For this demo, we fetch from the backend
    async function renderFace(emotion, animFrame) {
      try {
        const url = animFrame !== undefined
          ? `/api/face/animate?emotion=${emotion}&dt=0.05`
          : `/api/face/render?emotion=${emotion}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("Server not available");
        const svg = await res.text();
        container.innerHTML = svg;
        document.getElementById("status").textContent = "Connected — " + emotion;
      } catch {
        // Fallback: show static placeholder
        container.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="400" height="500"><rect x="0" y="0" width="400" height="500" fill="#1a1a2e" rx="20"/><text x="200" y="240" text-anchor="middle" fill="#55556a" font-family="Arial" font-size="16">Backend offline</text><text x="200" y="270" text-anchor="middle" fill="#3d3d55" font-family="Arial" font-size="13">Run: python -m nexus.ui.face_demo</text></svg>`;
        document.getElementById("status").textContent = "Offline — start the server";
      }
    }

    // Emotion buttons
    document.querySelectorAll("[data-emotion]").forEach(btn => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("[data-emotion]").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentEmotion = btn.dataset.emotion;
        renderFace(currentEmotion, 0);
      });
    });

    // Initial render
    renderFace("idle", 0);

    // Animation loop (if backend supports it)
    setInterval(() => {
      const active = document.querySelector("[data-emotion].active");
      if (active) {
        renderFace(active.dataset.emotion, frame);
        frame++;
      }
    }, 500);
  </script>
</body>
</html>"""


if __name__ == "__main__":
    # When run directly: write demo HTML files
    import pathlib

    out = pathlib.Path(__file__).parent
    with open(out / "face_demo_grid.html", "w", encoding="utf-8") as f:
        f.write(generate_emotion_grid())
    print(f"[nexus.face] Wrote {out / 'face_demo_grid.html'}")

    with open(out / "face_demo_animated.html", "w", encoding="utf-8") as f:
        f.write(generate_animated_demo())
    print(f"[nexus.face] Wrote {out / 'face_demo_animated.html'}")
