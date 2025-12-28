from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# -----------------------------
# Data model
# -----------------------------
@dataclass
class EmotionEvent:
    ts: datetime
    emotion: str


# -----------------------------
# Parsing utils
# -----------------------------
def _parse_iso_z(ts: str) -> Optional[datetime]:
    ts = ts.strip()
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None


_EMO_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T[^ \t]+)\s+emotion=(?P<emo>\w+)\s*$")


def parse_emotions(text: str) -> List[EmotionEvent]:
    events: List[EmotionEvent] = []
    for raw in text.splitlines():
        ln = raw.strip().replace("\t", " ")
        m = _EMO_RE.match(ln)
        if not m:
            # tolerant parse: "ts ... emotion=xxx"
            parts = re.split(r"\s+", ln)
            if len(parts) >= 2 and "emotion=" in parts[-1]:
                ts = _parse_iso_z(parts[0])
                emo = parts[-1].split("emotion=")[-1].strip().lower()
                if ts and emo:
                    events.append(EmotionEvent(ts=ts, emotion=emo))
            continue

        ts = _parse_iso_z(m.group("ts"))
        emo = (m.group("emo") or "").lower()
        if ts and emo:
            events.append(EmotionEvent(ts=ts, emotion=emo))

    events.sort(key=lambda e: e.ts)
    return events


def emotion_distribution(events: List[EmotionEvent]) -> Dict[str, float]:
    if not events:
        return {}
    counts: Dict[str, int] = {}
    for e in events:
        counts[e.emotion] = counts.get(e.emotion, 0) + 1
    total = len(events)
    # sort by frequency desc
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {k: v / total for k, v in items}


# -----------------------------
# Scoring (base=10)
# -----------------------------
def score_attitude_emotion_base10(events: List[EmotionEvent]) -> Tuple[float, Dict]:
    """
    Emotion set: ['angry','disgust','fear','happy','sad','surprise','neutral']
    Positive: happy, neutral, surprise
    Negative: angry, disgust, fear, sad

    Rule:
      score = 10
      - (1.2*angry + 1.0*disgust + 0.6*fear + 0.4*sad)*10
      + (0.15*happy + 0.10*neutral + 0.08*surprise)*10
      clamp 0..10
    """
    if not events:
        return 7.0, {"note": "No emotion events; default attitude_score=7.0"}

    counts: Dict[str, int] = {}
    for e in events:
        emo = (e.emotion or "").lower().strip()
        counts[emo] = counts.get(emo, 0) + 1

    total = sum(counts.values())
    ratios = {k: v / total for k, v in counts.items()}

    angry_r = ratios.get("angry", 0.0)
    disgust_r = ratios.get("disgust", 0.0)
    fear_r = ratios.get("fear", 0.0)
    sad_r = ratios.get("sad", 0.0)
    happy_r = ratios.get("happy", 0.0)
    neutral_r = ratios.get("neutral", 0.0)
    surprise_r = ratios.get("surprise", 0.0)

    base = 10.0
    score = base

    angry_pen = 1.2 * angry_r * 10.0
    disgust_pen = 1.0 * disgust_r * 10.0
    fear_pen = 0.6 * fear_r * 10.0
    sad_pen = 0.4 * sad_r * 10.0
    score -= (angry_pen + disgust_pen + fear_pen + sad_pen)

    happy_bonus = 0.15 * happy_r * 10.0
    neutral_bonus = 0.10 * neutral_r * 10.0
    surprise_bonus = 0.08 * surprise_r * 10.0
    score += (happy_bonus + neutral_bonus + surprise_bonus)

    score = max(0.0, min(10.0, score))
    score = round(score, 2)

    pos_ratio = happy_r + neutral_r + surprise_r
    neg_ratio = angry_r + disgust_r + fear_r + sad_r

    notes = []
    if angry_r > 0:
        notes.append("angry detected → heavy penalty (risk: conflict / low emotional control).")
    if disgust_r > 0:
        notes.append("disgust detected → heavy penalty (risk: negative/dismissive reaction).")
    if fear_r > 0:
        notes.append("fear detected → medium penalty (stress).")
    if sad_r > 0:
        notes.append("sad detected → medium penalty (discouragement).")
    if pos_ratio >= 0.7:
        notes.append("mostly positive/neutral/surprise → stable and engaged.")
    if neg_ratio >= 0.4:
        notes.append("high negative ratio → instability risk during interview.")

    detail = {
        "score": score,
        "base": base,
        "counts": counts,
        "ratios": {k: round(v, 3) for k, v in ratios.items()},
        "pos_ratio": round(pos_ratio, 3),
        "neg_ratio": round(neg_ratio, 3),
        "components": {
            "angry_penalty": round(angry_pen, 3),
            "disgust_penalty": round(disgust_pen, 3),
            "fear_penalty": round(fear_pen, 3),
            "sad_penalty": round(sad_pen, 3),
            "happy_bonus": round(happy_bonus, 3),
            "neutral_bonus": round(neutral_bonus, 3),
            "surprise_bonus": round(surprise_bonus, 3),
        },
        "rule": (
            "score = 10 - (1.2*angry + 1.0*disgust + 0.6*fear + 0.4*sad)*10 "
            "+ (0.15*happy + 0.10*neutral + 0.08*surprise)*10 (clamp 0..10)"
        ),
        "notes": notes,
    }
    return score, detail


# -----------------------------
# Main
# -----------------------------
def main():
    emotion_path = r"E:\project\Interview-Website-Project\cs311be\exports\emotion_d69972b9-feda-4011-80b4-fd3fdf51288b.txt"

    text = Path(emotion_path).read_text(encoding="utf-8")
    events = parse_emotions(text)

    print(f"[OK] emotion file = {emotion_path}")
    print(f"[OK] total events = {len(events)}")

    dist = emotion_distribution(events)
    print("\n=== Emotion distribution (ratio) ===")
    for emo, r in dist.items():
        print(f"{emo:>10}: {r:.3f}")

    score, detail = score_attitude_emotion_base10(events)
    print("\n=== Attitude score (base=10) ===")
    print("attitude_score:", score)

    print("\n=== Detail (explainable) ===")
    print(json.dumps(detail, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
