# src/services/evaluation_agent_service.py
from __future__ import annotations

import os
import re
import json
import glob
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from dotenv import load_dotenv
load_dotenv() 
# -----------------------------
# Data models
# -----------------------------

@dataclass
class QATurn:
    q_index: int
    question: str
    answer: str


@dataclass
class EvaluationResult:
    session_id: str
    role: Optional[str]
    knowledge_score: float
    attitude_score: float
    final_score: float
    explanation: Dict[str, Any]
    raw: Dict[str, Any]


# -----------------------------
# Transcript parsing (your format)
# -----------------------------

_Q_HEADER_RE = re.compile(r"^\[Q(\d+)\]\s+\(([^)]+)\)\s*$")
_A_HEADER_RE = re.compile(r"^\[A(\d+)\]\s+\(([^)]+)\)\s*$")
_SUMMARY_RE = re.compile(r"^\[Summary Q(\d+)\]\s*$")


def parse_transcript_to_turns(text: str) -> List[QATurn]:
    """
    Parse transcript like:
      [Q1] (timestamp)
      question lines...
      [A1] (timestamp)
      answer lines...
      [Summary Q1] ... (ignored)
    """
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
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
            # skip summary block
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


# -----------------------------
# Utilities
# -----------------------------

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
    # try extract first {...}
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


# -----------------------------
# File resolver
# -----------------------------

class SessionFileResolver:
    """
    Finds transcript file by session_id.
    Adjust patterns to match your storage convention.
    """
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
                # Avoid emotion file if mixed
                if "emotion" not in os.path.basename(p).lower():
                    return p
        raise FileNotFoundError(f"Transcript file not found for session_id={session_id} in {self.base_dir}")

    def read_text(self, path: str) -> str:
        with open(path, "rt", encoding="utf-8") as f:
            return f.read()


# -----------------------------
# Azure GPT client wrapper
# -----------------------------

class AzureGPTClient:
    def __init__(self):
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
                "- AZURE_OPENAI_DEPLOYMENT (deployment name)\n"
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
            response_format={"type": "json_object"},  # helps force JSON if supported
        )
        content = (resp.choices[0].message.content or "").strip()
        data = _safe_json(content)
        if not data:
            raise ValueError(f"Model did not return valid JSON. Raw content: {content[:500]}")
        return data


# -----------------------------
# Main service
# -----------------------------

class EvaluationAgentService:
    """
    Reads transcript (Q/A), calls Azure GPT, returns scores + explainability.
    """
    def __init__(
        self,
        base_dir: str,
        default_weights: Optional[Dict[str, float]] = None,
        weights_by_role: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        self.resolver = SessionFileResolver(base_dir=base_dir)
        self.gpt = AzureGPTClient()
        self.default_weights = default_weights or {"knowledge": 0.7, "attitude": 0.3}

    def _weights(self) -> Dict[str, float]:
        return dict(self.default_weights)

    def _build_messages(self,role: Optional[str],turns: List[QATurn],weights: Dict[str, float],) -> List[Dict[str, str]]:
        transcript = [
        {"q_index": t.q_index, "question": t.question, "answer": t.answer}
        for t in turns
        ]

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
Compute final_score = knowledge_score*{weights["knowledge"]} + attitude_score*{weights["attitude"]}.
final_score MUST match (round to 1 decimal).

STRICT RUBRIC:
Knowledge score (0..10) is the sum of five subscores K1..K5 (each 0..2, allow 0.5 increments):
- K1 Relevance & correctness: answers address the question and are technically correct.
- K2 Completeness: covers key points; not missing essential aspects.
- K3 Specificity & evidence: concrete details (tools, steps, constraints, examples) rather than vague claims.
- K4 Depth & reasoning: explains tradeoffs, why decisions were made, shows understanding.
- K5 Consistency across answers: no contradictions; aligns across Q/A.

Attitude score (0..10) is the sum of five subscores A1..A5 (each 0..2, allow 0.5 increments):
- A1 Professional tone: respectful, calm, non-defensive.
- A2 Clarity & structure: coherent, organized communication.
- A3 Engagement & responsiveness: answers the asked question; doesn't dodge; missing answers reduce this.
- A4 Accountability & honesty: admits gaps appropriately; realistic claims.
- A5 Constructiveness: solution-oriented, collaborative mindset.

FAIRNESS RULES (must follow):
- Do NOT reward long answers by default; reward only correct, relevant, specific content.
- Missing answers: a clear penalty to Knowledge, and a small penalty to Attitude (engagement).
- If the transcript has too few answered questions to be confident, avoid extreme scores and list limitations.
- Do not infer skills not evidenced in text.

EVIDENCE REQUIREMENT (mandatory):
- For EACH subscore, provide at least one evidence quote from candidate answers (<= 25 words) with q_index.
- If an answer is empty, use the quote "(no answer provided)" and explain it as missing.

OUTPUT STRICT JSON (exact schema):
{{
  "role_inference": {{
    "primary_role": string,
    "confidence": number,
    "alternatives": [
      {{"role": string, "confidence": number, "reasons": [string, ...]}}
    ],
    "evidence": [{{"q_index": int, "quote": string}}]
  }},
  "scores": {{
    "knowledge": {{
      "score": number,
      "subscores": {{
        "K1": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "K2": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "K3": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "K4": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "K5": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}}
      }},
      "summary": {{
        "strengths": [string, ...],
        "gaps": [string, ...],
        "improvements": [string, ...]
      }}
    }},
    "attitude": {{
      "score": number,
      "subscores": {{
        "A1": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "A2": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "A3": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "A4": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}},
        "A5": {{"score": number, "reason": string, "evidence": [{{"q_index": int, "quote": string}}]}}
      }},
      "summary": {{
        "strengths": [string, ...],
        "risks": [string, ...],
        "improvements": [string, ...]
      }}
    }},
    "final": {{
      "score": number,
      "weights": {json.dumps(weights)},
      "calculation": string
    }}
  }},
  "fairness_checks": {{
    "used_only_evidence": boolean,
    "penalized_missing_answers": boolean,
    "did_not_reward_verbosity": boolean,
    "limitations": [string, ...]
  }}
}}

SELF-CHECKS (must obey):
- Ensure knowledge.score == sum(K1..K5).
- Ensure attitude.score == sum(A1..A5).
- Ensure final.score == knowledge.score*{weights["knowledge"]} + attitude.score*{weights["attitude"]} (round to 1 decimal).
- If fewer than 3 answered questions, add a limitation: "low data; lower confidence".
Return JSON only.
""".strip()
        return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    def evaluate(self, session_id: str, role: Optional[str] = None) -> EvaluationResult:
        path = self.resolver.find_transcript_path(session_id)
        text = self.resolver.read_text(path)
        turns = parse_transcript_to_turns(text)

        weights = dict(self.default_weights) 
        messages = self._build_messages(role, turns, weights)
        data = self.gpt.judge(messages)

        # Normalize + ensure final is consistent
        ks = _clamp_0_10(float(data["scores"]["knowledge"]["score"]))
        ats = _clamp_0_10(float(data["scores"]["attitude"]["score"]))
        final = round(ks * weights["knowledge"] + ats * weights["attitude"], 1)

        # giữ nguyên toàn bộ JSON để show giải thích đầy đủ
        explanation = data

        return EvaluationResult(
            session_id=session_id,
            role=role,
            knowledge_score=round(ks, 2),
            attitude_score=round(ats, 2),
            final_score=final,
            explanation=explanation,
            raw=data,
        )
def main():
    # ====== CONFIG ======
    session_id = "d69972b9-feda-4011-80b4-fd3fdf51288b"

    # Nếu bạn đang test với file user upload trong sandbox:
    base_dir = r"E:\project\Interview-Website-Project\cs311be\exports"

    # Nếu project bạn lưu logs ở ./data thì đổi:
    # base_dir = "./data"

    role = "ai_engineer"  # hoặc None

    # ====== 1) Resolve + parse transcript ======
    resolver = SessionFileResolver(base_dir=base_dir)
    transcript_path = resolver.find_transcript_path(session_id)
    print(f"[OK] transcript_path = {transcript_path}")

    transcript_text = resolver.read_text(transcript_path)
    turns = parse_transcript_to_turns(transcript_text)
    print(f"[OK] parsed turns = {len(turns)}")

    for t in turns[:3]:
        q_preview = (t.question[:120] + "...") if len(t.question) > 120 else t.question
        a_preview = (t.answer[:160] + "...") if len(t.answer) > 160 else t.answer
        print(f"\n--- Q{t.q_index} ---\n{q_preview}")
        print(f"--- A{t.q_index} ---\n{a_preview if a_preview else '(EMPTY ANSWER)'}")

    # ====== 2) Call Azure GPT evaluation (if env ready) ======
    required_envs = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT",
    ]
    missing = [k for k in required_envs if not os.getenv(k)]
    if missing:
        print("\n[SKIP] Azure env missing, cannot call GPT evaluation:")
        print("       missing:", ", ".join(missing))
        print("       => You can still validate parsing above.")
        return

    service = EvaluationAgentService(
        base_dir=base_dir,
        weights_by_role={
            "ai_engineer": {"knowledge": 0.8, "attitude": 0.2},
            "sales": {"knowledge": 0.5, "attitude": 0.5},
        },
    )

    result = service.evaluate(session_id=session_id, role=role)

    print("\n========= EVALUATION RESULT =========")
    print("knowledge_score:", result.knowledge_score)
    print("attitude_score :", result.attitude_score)
    print("final_score    :", result.final_score)
    print("\nexplanation:")
    print(json.dumps(result.explanation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()