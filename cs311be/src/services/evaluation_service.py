# src/services/evaluation_service.py
from __future__ import annotations

import glob
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional: dotenv
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

# Optional: Azure OpenAI SDK
try:
    from openai import AzureOpenAI  # type: ignore
except Exception:
    AzureOpenAI = None


# ============================================================
# Data models (internal)
# ============================================================

@dataclass
class EmotionEvent:
    ts: datetime
    emotion: str


@dataclass
class QATurn:
    q_index: int
    question: str
    answer: str


@dataclass
class AgentScores:
    knowledge_score: float
    attitude_score: float
    agent_final_score: float
    explanation: Dict[str, Any]


# ============================================================
# Emotion parsing + scoring (distribution-based)
# ============================================================

def _parse_iso_z(ts: str) -> Optional[datetime]:
    ts = (ts or "").strip()
    if not ts:
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None


# Accept lines like: 2025-...Z emotion=happy
_EMO_RE = re.compile(r"^(?P<ts>\d{4}-\d{2}-\d{2}T[^ \t]+)\s+emotion=(?P<emo>\w+)\s*$")


def parse_emotions(text: str) -> List[EmotionEvent]:
    events: List[EmotionEvent] = []
    for raw in (text or "").splitlines():
        ln = raw.strip().replace("\t", " ")
        if not ln:
            continue

        m = _EMO_RE.match(ln)
        if not m:
            # tolerant parse: "<ts> ... emotion=xxx"
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
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {k: v / total for k, v in items}


def score_emotion_face_base10(events: List[EmotionEvent]) -> Tuple[float, Dict[str, Any]]:
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
        return 7.0, {"note": "No emotion events; default emotion_face_score=7.0"}

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

    score = 10.0
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

    detail = {
        "score": score,
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
    }
    return score, detail

import math

MIN_REQUIRED = 10
P = 1.8          # phạt mạnh khi thiếu câu
BONUS_MAX = 0.8  # thưởng tối đa khi >10
K = 10           # tốc độ bão hoà bonus

BAD_SHORT = {"no", "idk", "i don't know", "n/a", ".", "nah", "(no answer provided)"}

def is_valid_answer(ans: str) -> bool:
    if not ans:
        return False
    t = ans.strip().lower()
    if not t or t in BAD_SHORT:
        return False
    if len(t) < 20:   # chỉnh ngưỡng tuỳ bạn
        return False
    return True

def apply_data_sufficiency(ks: float, ats: float, w_k: float, w_a: float, n_valid: int):
    ratio = min(1.0, n_valid / MIN_REQUIRED)
    coverage = ratio ** P

    # scale BOTH knowledge & attitude để UI không bị “knowledge 9 nhưng final thấp”
    ks_adj = max(0.0, min(10.0, ks * coverage))
    ats_adj = max(0.0, min(10.0, ats * coverage))

    # bonus nhẹ cho >10 câu, chia theo weights
    bonus = 0.0
    if n_valid > MIN_REQUIRED:
        bonus = BONUS_MAX * (1.0 - math.exp(-(n_valid - MIN_REQUIRED) / K))
        total_w = (w_k + w_a) or 1.0
        ks_adj = min(10.0, ks_adj + bonus * (w_k / total_w))
        ats_adj = min(10.0, ats_adj + bonus * (w_a / total_w))

    agent_final_adj = max(0.0, min(10.0, ks_adj * w_k + ats_adj * w_a))

    detail = {
        "min_required": MIN_REQUIRED,
        "n_valid_answers": n_valid,
        "coverage_factor": round(coverage, 4),
        "bonus": round(bonus, 4),
        "params": {"p": P, "bonus_max": BONUS_MAX, "k": K},
        "rule": "knowledge/attitude scaled by coverage; small bonus after 10; clamp 0..10",
        "raw": {"knowledge": ks, "attitude": ats},
        "adjusted": {"knowledge": round(ks_adj, 2), "attitude": round(ats_adj, 2), "agent_final": round(agent_final_adj, 2)},
    }
    return round(ks_adj, 2), round(ats_adj, 2), round(agent_final_adj, 2), detail

# ============================================================
# Transcript parsing (your Q/A format)
# ============================================================

_Q_HEADER_RE = re.compile(r"^\[Q(\d+)\]\s+\(([^)]+)\)\s*$")
_A_HEADER_RE = re.compile(r"^\[A(\d+)\]\s+\(([^)]+)\)\s*$")
_SUMMARY_RE = re.compile(r"^\[Summary Q(\d+)\]\s*$")


def parse_transcript_to_turns(text: str) -> List[QATurn]:
    lines = [ln.rstrip("\n") for ln in (text or "").splitlines()]
    turns: Dict[int, Dict[str, str]] = {}
    i = 0

    def collect_until(stop_pred):
        nonlocal i
        buf = []
        while i < len(lines) and not stop_pred(lines[i].strip()):
            buf.append(lines[i])
            i += 1
        return "\n".join(buf).strip()

    while i < len(lines):
        ln = lines[i].strip()
        m_q = _Q_HEADER_RE.match(ln)
        m_a = _A_HEADER_RE.match(ln)
        m_s = _SUMMARY_RE.match(ln)

        if m_q:
            idx = int(m_q.group(1))
            i += 1
            q_text = collect_until(lambda s: bool(_A_HEADER_RE.match(s))
                                            or bool(_Q_HEADER_RE.match(s))
                                            or bool(_SUMMARY_RE.match(s))
                                            or s.startswith("-----"))
            turns.setdefault(idx, {})["question"] = q_text
            continue

        if m_a:
            idx = int(m_a.group(1))
            i += 1
            a_text = collect_until(lambda s: bool(_Q_HEADER_RE.match(s))
                                            or bool(_A_HEADER_RE.match(s))
                                            or bool(_SUMMARY_RE.match(s))
                                            or s.startswith("-----"))
            turns.setdefault(idx, {})["answer"] = a_text
            continue

        if m_s:
            i += 1
            _ = collect_until(lambda s: s.startswith("-----")
                                       or bool(_Q_HEADER_RE.match(s))
                                       or bool(_A_HEADER_RE.match(s)))
            continue

        i += 1

    out: List[QATurn] = []
    for idx in sorted(turns.keys()):
        q = (turns[idx].get("question") or "").strip()
        a = (turns[idx].get("answer") or "").strip()
        if q:
            out.append(QATurn(q_index=idx, question=q, answer=a))
    return out


# ============================================================
# Azure GPT judge (agent scoring)
# ============================================================

def _clamp_0_10(x: float) -> float:
    return max(0.0, min(10.0, x))


def _safe_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


class AzureGPTClient:
    def __init__(self):
        if AzureOpenAI is None:
            raise RuntimeError("Missing dependency: openai (AzureOpenAI). Install: pip install openai")

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "").strip()
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()

        if not all([endpoint, api_key, api_version, deployment]):
            raise RuntimeError(
                "Missing Azure OpenAI env vars. Required:\n"
                "- AZURE_OPENAI_ENDPOINT\n"
                "- AZURE_OPENAI_API_KEY\n"
                "- AZURE_OPENAI_API_VERSION\n"
                "- AZURE_OPENAI_DEPLOYMENT\n"
            )

        self.deployment = deployment
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )

    def judge(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        resp = self.client.chat.completions.create(
            model=self.deployment,  # Azure uses deployment name
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = (resp.choices[0].message.content or "").strip()
        data = _safe_json(content)
        if not data:
            raise ValueError(f"Model did not return valid JSON. Raw content: {content[:500]}")
        return data


class EvaluationAgentService:
    def __init__(self, w_knowledge: float = 0.7, w_attitude: float = 0.3):
        self.gpt = AzureGPTClient()
        self.w_knowledge = w_knowledge
        self.w_attitude = w_attitude

    def _build_messages(self, role: Optional[str], turns: List[QATurn]) -> List[Dict[str, str]]:
        transcript = [{"q_index": t.q_index, "question": t.question, "answer": t.answer} for t in turns]

        system = (
            "You are an objective interview evaluator. "
            "You must score the candidate FAIRLY and CONSISTENTLY based only on the provided transcript "
            "(and the role string if provided). "
            "Do NOT assume missing info. Do NOT reward verbosity. "
            "Do NOT invent facts. Output STRICT JSON only. No markdown."
        )

        user = f"""
Inputs:
- Role (may be unknown): {role or "unknown / infer from questions/answers"}

Interview transcript (Q/A JSON):
<<<TRANSCRIPT_JSON
{json.dumps(transcript, ensure_ascii=False)}
TRANSCRIPT_JSON>>>

TASK 1 — Role Inference (ONLY if role is unknown/empty):
Infer the most likely role(s) from the transcript.
If uncertain, return top 3 roles with confidence (0..1) and reasons grounded in evidence quotes.

TASK 2 — Scoring (must be fair & explainable):
Score each dimension from 0..10 using 0.5 increments ONLY.
Compute agent_final_score = knowledge_score*{self.w_knowledge} + attitude_score*{self.w_attitude}.
agent_final_score MUST match (round to 2 decimals).

STRICT RUBRIC:
Knowledge score (0..10) is the sum of five subscores K1..K5 (each 0..2, allow 0.5 increments):
- K1 Relevance & correctness
- K2 Completeness
- K3 Specificity & evidence
- K4 Depth & reasoning
- K5 Consistency across answers

Attitude score (0..10) is the sum of five subscores A1..A5 (each 0..2, allow 0.5 increments):
- A1 Professional tone
- A2 Clarity & structure
- A3 Engagement & responsiveness
- A4 Accountability & honesty
- A5 Constructiveness

EVIDENCE REQUIREMENT:
- For EACH subscore, provide at least one evidence quote (<= 25 words) with q_index.
- If an answer is empty, use "(no answer provided)" as the quote.

OUTPUT STRICT JSON (exact schema):
{{
  "role_inference": {{
    "primary_role": "string",
    "confidence": 0.0,
    "alternatives": [
      {{"role": "string", "confidence": 0.0, "reasons": ["string"]}}
    ],
    "evidence": [{{"q_index": 0, "quote": "string"}}]
  }},
  "scores": {{
    "knowledge": {{
      "score": 0.0,
      "subscores": {{
        "K1": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "K2": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "K3": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "K4": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "K5": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}}
      }},
      "summary": {{"strengths": ["string"], "gaps": ["string"], "improvements": ["string"]}}
    }},
    "attitude": {{
      "score": 0.0,
      "subscores": {{
        "A1": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "A2": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "A3": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "A4": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}},
        "A5": {{"score": 0.0, "reason": "string", "evidence": [{{"q_index": 0, "quote": "string"}}]}}
      }},
      "summary": {{"strengths": ["string"], "risks": ["string"], "improvements": ["string"]}}
    }},
    "final": {{
      "score": 0.0,
      "weights": {{"knowledge": {self.w_knowledge}, "attitude": {self.w_attitude}}},
      "calculation": "string"
    }}
  }}
}}

Return JSON only.
""".strip()

        return [{"role": "system", "content": system}, {"role": "user", "content": user}]

    def evaluate_turns(self, turns: List[QATurn], role: Optional[str]) -> AgentScores:
        data = self.gpt.judge(self._build_messages(role, turns))

        knowledge = _clamp_0_10(float(data["scores"]["knowledge"]["score"]))
        attitude = _clamp_0_10(float(data["scores"]["attitude"]["score"]))
        agent_final = _clamp_0_10(knowledge * self.w_knowledge + attitude * self.w_attitude)

        return AgentScores(
            knowledge_score=round(knowledge, 2),
            attitude_score=round(attitude, 2),
            agent_final_score=round(agent_final, 2),
            explanation=data,
        )


# ============================================================
# File resolver (exports)
# ============================================================

class SessionFileResolver:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir

    def find_transcript_path(self, session_id: str) -> str:
        patterns = [
            os.path.join(self.base_dir, f"*{session_id}*mock*.txt"),
            os.path.join(self.base_dir, f"*{session_id}*transcript*.txt"),
            os.path.join(self.base_dir, f"*{session_id}*.txt"),
        ]
        for pat in patterns:
            for p in sorted(glob.glob(pat)):
                if "emotion" not in os.path.basename(p).lower():
                    return p
        raise FileNotFoundError(f"Transcript file not found for session_id={session_id} in {self.base_dir}")

    def find_emotion_path(self, session_id: str) -> str:
        patterns = [
            os.path.join(self.base_dir, f"*emotion*{session_id}*.txt"),
            os.path.join(self.base_dir, f"*{session_id}*emotion*.txt"),
            os.path.join(self.base_dir, f"emotion_{session_id}.txt"),
        ]
        for pat in patterns:
            for p in sorted(glob.glob(pat)):
                return p
        raise FileNotFoundError(f"Emotion file not found for session_id={session_id} in {self.base_dir}")


# ============================================================
# Overall scoring (PATCHED)
# ============================================================

def compute_total_patched(
    emotion_face_score: float,
    agent_scores: Optional[AgentScores],
    w_agent_final: float = 0.65,
    w_emotion: float = 0.35,
) -> Dict[str, Any]:
    """
    PATCHED:
      total = agent_final*w_agent_final + emotion_face_score*w_emotion
    """
    detail: Dict[str, Any] = {
        "formula": "total = agent_final*w_agent_final + emotion_face_score*w_emotion",
        "weights": {"w_agent_final": w_agent_final, "w_emotion": w_emotion},
    }

    if agent_scores is None:
        return {
            "emotion_face_score": round(emotion_face_score, 2),
            "knowledge_score": None,
            "attitude_score": None,
            "agent_final_score": None,
            "total_score": None,
            "detail": detail,
        }

    agent_final = _clamp_0_10(agent_scores.agent_final_score)
    total = _clamp_0_10(agent_final * w_agent_final + emotion_face_score * w_emotion)

    detail["components"] = {
        "agent_final_component": round(agent_final * w_agent_final, 4),
        "emotion_component": round(emotion_face_score * w_emotion, 4),
    }

    return {
        "emotion_face_score": round(emotion_face_score, 2),
        "knowledge_score": agent_scores.knowledge_score,
        "attitude_score": agent_scores.attitude_score,
        "agent_final_score": round(agent_final, 2),
        "total_score": round(total, 2),
        "detail": detail,
    }


# ============================================================
# Main EvaluationService (call from router)
# ============================================================

class EvaluationService:
    def __init__(self, base_dir: str = "exports"):
        self.base_dir = base_dir

    def evaluate(
        self,
        session_id: str,
        role: Optional[str] = "ai_engineer",
        base_dir: Optional[str] = None,
        transcript_path: str = "",
        emotion_path: str = "",
        # agent weights
        w_knowledge: float = 0.7,
        w_attitude: float = 0.3,
        # overall weights
        w_agent_final: float = 0.65,
        w_emotion: float = 0.35,
    ) -> Dict[str, Any]:
        if load_dotenv is not None:
            load_dotenv()

        use_base = (base_dir or self.base_dir).strip()
        resolver = SessionFileResolver(base_dir=use_base)

        tp = transcript_path.strip() or resolver.find_transcript_path(session_id)
        ep = emotion_path.strip() or resolver.find_emotion_path(session_id)

        # 1) Emotion score
        emo_text = Path(ep).read_text(encoding="utf-8")
        emo_events = parse_emotions(emo_text)
        emo_dist = emotion_distribution(emo_events)
        emotion_face_score, emotion_detail = score_emotion_face_base10(emo_events)

        # 2) Agent score (knowledge + attitude)
        agent_scores: Optional[AgentScores] = None
        agent_error: Optional[str] = None

        required_envs = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_API_VERSION",
            "AZURE_OPENAI_DEPLOYMENT",
        ]
        missing = [k for k in required_envs if not os.getenv(k)]
        if missing:
            agent_error = f"Missing Azure envs: {', '.join(missing)} (skip agent scoring)"
        else:
            try:
                text = Path(tp).read_text(encoding="utf-8")
                turns = parse_transcript_to_turns(text)
                agent = EvaluationAgentService(w_knowledge=w_knowledge, w_attitude=w_attitude)
                agent_scores = agent.evaluate_turns(turns=turns, role=role)
            except Exception as e:
                agent_error = f"Agent scoring failed: {type(e).__name__}: {e}"
        if agent_scores is not None:
            n_valid = sum(1 for t in turns if is_valid_answer(t.answer))

            ks_adj, ats_adj, final_adj, ds_detail = apply_data_sufficiency(
                ks=agent_scores.knowledge_score,
                ats=agent_scores.attitude_score,
                w_k=w_knowledge,
                w_a=w_attitude,
                n_valid=n_valid,
            )

            # overwrite agent_scores để downstream compute_total_patched dùng bản adjusted
            agent_scores.knowledge_score = ks_adj
            agent_scores.attitude_score = ats_adj
            agent_scores.agent_final_score = final_adj
            agent_scores.explanation.setdefault("data_sufficiency", ds_detail)
        # 3) Overall patched
        overall = compute_total_patched(
            emotion_face_score=emotion_face_score,
            agent_scores=agent_scores,
            w_agent_final=w_agent_final,
            w_emotion=w_emotion,
        )
        if ds_detail is not None:
            overall["data_sufficiency"] = ds_detail
            overall.setdefault("detail", {})["data_sufficiency"] = ds_detail
        return {
            "inputs": {
                "base_dir": use_base,
                "session_id": session_id,
                "role": role,
                "transcript_path": tp,
                "emotion_path": ep,
                "agent_internal_weights": {"knowledge": w_knowledge, "attitude": w_attitude},
                "overall_weights": {"agent_final": w_agent_final, "emotion_face": w_emotion},
            },
            "emotion": {
                "total_events": len(emo_events),
                "distribution": {k: round(v, 4) for k, v in emo_dist.items()},
                "score": emotion_face_score,
                "detail": emotion_detail,
            },
            "agent": {
                "scores": None if agent_scores is None else {
                    "knowledge_score": agent_scores.knowledge_score,
                    "attitude_score": agent_scores.attitude_score,
                    "agent_final_score": agent_scores.agent_final_score,
                },
                "error": agent_error,
                "explanation": None if agent_scores is None else agent_scores.explanation,
            },
            "overall": overall,
        }
