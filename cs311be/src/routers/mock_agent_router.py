from pathlib import Path
from fastapi import APIRouter, HTTPException
from typing import Any
from datetime import datetime
import json  # NEW

from src.schemas.mock_agent import StartMockRequest, StartMockResponse, MockTurnRequest, MockTurnResponse
from src.services.mock_agent_service import MockAgentService

# NEW: import evaluation
from src.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/mock", tags=["mock-agent"])
_service = MockAgentService()

# NEW: singleton eval service
_eval_service = EvaluationService(base_dir="exports")
def _print_agent_evidence(explanation: dict):
    """
    Print K1..K5 + A1..A5 evidence nicely.
    explanation = report["agent"]["explanation"]
    """
    if not isinstance(explanation, dict):
        print("[agent] no explanation dict")
        return

    scores = explanation.get("scores") or {}
    knowledge = (scores.get("knowledge") or {})
    attitude = (scores.get("attitude") or {})

    def _print_block(title: str, block: dict, keys: list[str]):
        print(f"\n--- {title} ---")
        print("score:", block.get("score"))
        subs = block.get("subscores") or {}
        for k in keys:
            item = subs.get(k) or {}
            sc = item.get("score")
            reason = (item.get("reason") or "").strip()
            print(f"  {k}: {sc} | {reason}")

            evs = item.get("evidence") or []
            for ev in evs[:3]:  # in tối đa 3 quote/tiêu chí cho gọn
                qi = ev.get("q_index")
                qt = (ev.get("quote") or "").strip()
                print(f"     - Q{qi}: {qt}")

    # (Optional) role inference
    ri = explanation.get("role_inference")
    if isinstance(ri, dict):
        print("\n--- ROLE INFERENCE ---")
        print("primary_role:", ri.get("primary_role"))
        print("confidence:", ri.get("confidence"))
        evs = ri.get("evidence") or []
        for ev in evs[:3]:
            print(f"  - Q{ev.get('q_index')}: {(ev.get('quote') or '').strip()}")

    _print_block("KNOWLEDGE (K1..K5)", knowledge, ["K1", "K2", "K3", "K4", "K5"])
    _print_block("ATTITUDE (A1..A5)", attitude, ["A1", "A2", "A3", "A4", "A5"])

    # (Optional) summaries
    ks = (knowledge.get("summary") or {})
    if ks:
        print("\n[knowledge.summary] strengths:", ks.get("strengths"))
        print("[knowledge.summary] gaps:", ks.get("gaps"))
        print("[knowledge.summary] improvements:", ks.get("improvements"))

    ats = (attitude.get("summary") or {})
    if ats:
        print("\n[attitude.summary] strengths:", ats.get("strengths"))
        print("[attitude.summary] risks:", ats.get("risks"))
        print("[attitude.summary] improvements:", ats.get("improvements"))

def _extract_agent_details(explanation: dict) -> dict:
    """
    Convert agent explanation schema -> UI-friendly fields:
      role_inference, knowledge_detail, attitude_detail, knowledge_summary, attitude_summary
    """
    if not isinstance(explanation, dict):
        return {}

    scores = explanation.get("scores") or {}
    knowledge = (scores.get("knowledge") or {})
    attitude = (scores.get("attitude") or {})

    def _to_evidence_strings(evs, limit=5):
        out = []
        for ev in (evs or [])[:limit]:
            if not isinstance(ev, dict):
                continue
            qi = ev.get("q_index")
            qt = (ev.get("quote") or "").strip()
            if not qt:
                continue
            out.append(f"Q{qi}: {qt}" if qi is not None else qt)
        return out

    def _subscores_to_detail(block: dict, keys: list[str]) -> dict:
        subs = block.get("subscores") or {}
        detail = {}
        for k in keys:
            item = subs.get(k) or {}
            detail[k] = {
                "score": float(item.get("score") or 0.0),
                "description": (item.get("reason") or "").strip(),
                "evidence": _to_evidence_strings(item.get("evidence")),
            }
        return detail

    # role inference (optional)
    ri = explanation.get("role_inference") or {}
    role_inference = None
    if isinstance(ri, dict) and (ri.get("primary_role") or ri.get("confidence") is not None):
        role_inference = {
            "primary_role": ri.get("primary_role"),
            "confidence": ri.get("confidence"),
            "evidence": _to_evidence_strings(ri.get("evidence"), limit=3),
        }

    out = {
        "role_inference": role_inference,
        "knowledge_detail": _subscores_to_detail(knowledge, ["K1", "K2", "K3", "K4", "K5"]),
        "attitude_detail": _subscores_to_detail(attitude, ["A1", "A2", "A3", "A4", "A5"]),
        "knowledge_summary": knowledge.get("summary") or {},
        "attitude_summary": attitude.get("summary") or {},
        # (optional) keep raw explanation for debugging in FE if needed:
        # "agent_explanation_raw": explanation,
    }
    return out

def _safe_sid(session_id: str) -> str:
    return "".join(ch for ch in (session_id or "") if ch.isalnum() or ch in ("-", "_"))


def _normalize_role_text(jd_text: Any) -> str:
    # 1) nếu đã là string
    if isinstance(jd_text, str):
        return jd_text.strip()

    # 2) nếu là dict: ưu tiên các key thường gặp
    if isinstance(jd_text, dict):
        for k in ("text", "content", "role", "job_description", "jd_text", "description", "prompt"):
            v = jd_text.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # fallback: dump json pretty
        return json.dumps(jd_text, ensure_ascii=False, indent=2)

    # 3) list/other: dump json
    try:
        return json.dumps(jd_text, ensure_ascii=False, indent=2)
    except Exception:
        return str(jd_text)
def _load_role_text(session_id: str) -> str:
    sid = _safe_sid(session_id)
    fp = Path("exports") / f"role_{sid}.txt"
    if fp.exists():
        return fp.read_text(encoding="utf-8").strip()
    return ""
def _save_role_text(session_id: str, jd_text: Any) -> str:
    Path("exports").mkdir(exist_ok=True)
    sid = _safe_sid(session_id)
    fp = Path("exports") / f"role_{sid}.txt"

    role_text = _normalize_role_text(jd_text)
    fp.write_text(role_text, encoding="utf-8")
    return str(fp)


@router.post("/start", response_model=StartMockResponse)
def start_mock(payload: StartMockRequest):
    try:
        # NEW: lưu job_description (jd_text) như là role user miêu tả
        # vì FE startMockSession chỉ gửi jd_text chứ không gửi role :contentReference[oaicite:1]{index=1}
        print(payload.jd_text)
        _save_role_text(payload.session_id, payload.jd_text)

        # NEW: nếu payload.role rỗng -> dùng luôn jd_text làm role
        role_text = (payload.role or "").strip() or _normalize_role_text(payload.jd_text)
        first_q = _service.start_session(payload.session_id, payload.cv_text, payload.jd_text, role_text)
        return StartMockResponse(session_id=payload.session_id, first_question=first_q)
    except HTTPException as he:
        raise he
    except Exception as e:
        print("start_mock error:", e)
        raise HTTPException(status_code=500, detail=f"start_mock failed: {e}")


@router.post("/turn", response_model=MockTurnResponse)
def mock_turn(payload: MockTurnRequest):
    try:
        data = _service.process_turn(payload.session_id, payload.user_answer)
        return MockTurnResponse(
            session_id=payload.session_id,
            timestamp=datetime.utcnow(),
            reasoning_summary=data["reasoning_summary"],
            next_question=data["next_question"],
            followups=data.get("followups", []),
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        print("mock_turn error:", e)
        raise HTTPException(status_code=500, detail=f"mock_turn failed: {e}")


@router.post("/export")
def export_mock(session_id: str):
    try:
        path = _service.export_transcript_txt(session_id)

        role_text = _load_role_text(session_id)

        report = _eval_service.evaluate(
            session_id=session_id,
            role=role_text or None,
            base_dir="exports",
            w_knowledge=0.7,
            w_attitude=0.3,
            w_agent_final=0.65,
            w_emotion=0.35,
        )
        overall = report.get("overall", {})
        auto_eval = dict(overall)

        explanation = report.get("agent", {}).get("explanation")
        if explanation:
            auto_eval.update(_extract_agent_details(explanation))

        return {"ok": True, "path": path, "auto_eval": auto_eval}


    except Exception as e:
        print("export_mock error:", e)
        raise HTTPException(status_code=500, detail=f"export_mock failed: {type(e).__name__}: {e}")
