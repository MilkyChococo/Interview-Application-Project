from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import re
from fastapi import HTTPException
from src.engines.llm_engine import get_llm_engine
from pathlib import Path

_engine = get_llm_engine()

def llm_chat(system: str, user: str) -> str:
    return _engine.chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ])

@dataclass
class MockTurn:
    question: Optional[str]
    answer: Optional[str]
    time: datetime = field(default_factory=datetime.utcnow)
    summary: Optional[str] = None

@dataclass
class MockSession:
    session_id: str
    cv_text: str
    jd_text: str
    role: Optional[str]
    turns: List[MockTurn] = field(default_factory=list)

class MockAgentService:
    def __init__(self) -> None:
        self.sessions: Dict[str, MockSession] = {}

    def _role_from_jd(self, jd_text: str, fallback: Optional[str]) -> str:
        if fallback:
            return fallback
        m = re.search(r"(Senior|Junior|Lead)?\s*([A-Za-z ]+(Engineer|Developer|Scientist|Manager))", jd_text, re.I)
        return m.group(0).strip() if m else "the position"

    def start_session(self, session_id: str, cv_text: str, jd_text: str, role: Optional[str]) -> str:
        if not cv_text or not jd_text:
            print(f"[mock/start] Missing text. cv_len={len(cv_text or '')}, jd_len={len(jd_text or '')}")
            raise HTTPException(status_code=400, detail="cv_text and jd_text are required")
        self.sessions[session_id] = MockSession(session_id=session_id, cv_text=cv_text, jd_text=jd_text, role=role)

        role_name = self._role_from_jd(jd_text, role)
        sys = "You are an adaptive interviewer. Ask one clear opening question ending with '?'."
        usr = f"Role: {role_name}\nCV:\n{cv_text[:4000]}\nJD:\n{jd_text[:4000]}"
        first_q = llm_chat(sys, usr).strip()
        if not first_q.endswith("?"):
            first_q = first_q.rstrip(".") + "?"
        self.sessions[session_id].turns.append(MockTurn(question=first_q, answer=None))
        return first_q

    def process_turn(self, session_id: str, user_answer: str) -> Dict:
        if session_id not in self.sessions:
            raise HTTPException(status_code=400, detail="Invalid session_id. Call /mock/start first.")
        s = self.sessions[session_id]

        if s.turns and s.turns[-1].answer is None:
            s.turns[-1].answer = user_answer
        else:
            s.turns.append(MockTurn(question=None, answer=user_answer))

        sys_r = "Analyze the answer; return concise summary linked to JD/CV. Max 120 words."
        usr_r = f"JD:\n{s.jd_text[:3000]}\nCV:\n{s.cv_text[:3000]}\nAnswer:\n{user_answer}"
        reasoning = llm_chat(sys_r, usr_r).strip()
        s.turns[-1].summary = reasoning

        role_name = self._role_from_jd(s.jd_text, s.role)
        sys_q = "Ask exactly one concise follow-up question ending with '?'."
        usr_q = f"Role: {role_name}\nJD:\n{s.jd_text[:2500]}\nCV:\n{s.cv_text[:2500]}\nLast answer:\n{user_answer}"
        next_q = llm_chat(sys_q, usr_q).strip()
        if not next_q.endswith("?"):
            next_q = next_q.rstrip(".") + "?"
        s.turns.append(MockTurn(question=next_q, answer=None))
        return {"reasoning_summary": reasoning, "next_question": next_q, "followups": []}
    def export_transcript_txt(self, session_id: str, out_dir: str = "exports") -> str:
        if session_id not in self.sessions:
            raise HTTPException(status_code=404, detail="Session not found")

        s = self.sessions[session_id]
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        # Tên file an toàn (tránh ký tự lạ)
        safe_sid = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_"))
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = Path(out_dir) / f"mock_{safe_sid}_{ts}.txt"

        lines = []
        lines.append("=== MOCK INTERVIEW TRANSCRIPT ===")
        lines.append(f"Session: {s.session_id}")
        lines.append(f"Role: {s.role or self._role_from_jd(s.jd_text, None)}")
        lines.append(f"Exported (UTC): {datetime.utcnow().isoformat()}Z")
        lines.append("")

        q_idx = 0
        for t in s.turns:
            # mỗi turn của bạn thường là: (question, answer, summary)
            if t.question:
                q_idx += 1
                lines.append(f"[Q{q_idx}] ({t.time.isoformat()}Z)")
                lines.append(t.question)
                lines.append("")

            if t.answer:
                lines.append(f"[A{q_idx}] ({t.time.isoformat()}Z)")
                lines.append(t.answer)
                lines.append("")

            if t.summary:
                lines.append(f"[Summary Q{q_idx}]")
                lines.append(t.summary)
                lines.append("")

            lines.append("-" * 60)

        content = "\n".join(lines)

        # Ghi UTF-8 để không lỗi tiếng Việt
        file_path.write_text(content, encoding="utf-8")

        return str(file_path)