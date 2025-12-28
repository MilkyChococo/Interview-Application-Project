import { useMemo, useState } from "react";

function clamp01(x) {
  if (typeof x !== "number") return 0;
  return Math.max(0, Math.min(1, x));
}

function colorByScore10(score) {
  // score 0..10
  if (score >= 8) return { a: "#10B981", b: "#22C55E" }; // emerald->green
  if (score >= 6) return { a: "#3B82F6", b: "#06B6D4" }; // blue->cyan
  if (score >= 4) return { a: "#F59E0B", b: "#F97316" }; // amber->orange
  return { a: "#EF4444", b: "#EC4899" }; // red->pink
}

function colorByScore2(score) {
  // score 0..2 (K1..K5, A1..A5)
  if (score >= 1.6) return "#34D399"; // emerald
  if (score >= 1.2) return "#60A5FA"; // blue
  if (score >= 0.8) return "#FBBF24"; // amber
  return "#F87171"; // red
}

function Progress({ value, max = 10 }) {
  const v = typeof value === "number" ? value : 0;
  const pct = Math.round(clamp01(v / max) * 100);

  return (
    <div
      style={{
        height: 10,
        width: "100%",
        borderRadius: 999,
        background: "rgba(255,255,255,0.18)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          height: 10,
          width: `${pct}%`,
          borderRadius: 999,
          background: "rgba(255,255,255,0.95)",
          transition: "width 300ms ease",
        }}
      />
    </div>
  );
}

function MetricCard({ label, value, icon }) {
  const score = typeof value === "number" ? value : 0;
  const display = typeof value === "number" ? value.toFixed(2) : "—";
  const c = colorByScore10(score);

  return (
    <div
      style={{
        borderRadius: 18,
        padding: 16,
        border: `2px solid rgba(255,255,255,0.12)`,
        background: `linear-gradient(135deg, ${c.a}22, ${c.b}22)`,
        color: "white",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div style={{ fontSize: 13, opacity: 0.9 }}>
          <span style={{ marginRight: 6 }}>{icon}</span>
          {label}
        </div>
      </div>

      <div style={{ marginTop: 10, fontSize: 34, fontWeight: 800 }}>
        {display}
      </div>

      <div style={{ marginTop: 10 }}>
        <Progress value={score} max={10} />
      </div>
    </div>
  );
}
const KNOWLEDGE_LABELS = {
  K1: "Relevance & Correctness",
  K2: "Completeness",
  K3: "Specificity & Evidence",
  K4: "Depth & Reasoning",
  K5: "Consistency & Coherence",
};

const ATTITUDE_LABELS = {
  A1: "Professional Tone",
  A2: "Clarity & Structure",
  A3: "Engagement & Responsiveness",
  A4: "Accountability & Honesty",
  A5: "Constructiveness",
};

function getCriteriaLabel(code, group) {
  const c = String(code || "").toUpperCase();
  if (group === "knowledge") return KNOWLEDGE_LABELS[c] || "";
  if (group === "attitude") return ATTITUDE_LABELS[c] || "";
  return "";
}

function CriteriaDetail({ group, data }) {
  if (!data) return null;

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {Object.entries(data).map(([key, item]) => {
        const code = String(key).toUpperCase();
        const label = getCriteriaLabel(code, group);

        const score = typeof item?.score === "number" ? item.score : 0;

        return (
          <div
            key={code}
            style={{
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.10)",
              background: "rgba(0,0,0,0.25)",
              padding: 12,
            }}
          >
            {/* Header: code + label + score */}
            <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
              <div style={{ fontWeight: 800, color: "white" }}>
                {code}
                {label ? (
                  <span style={{ marginLeft: 10, fontWeight: 600, opacity: 0.8, fontSize: 13 }}>
                    — {label}
                  </span>
                ) : null}
              </div>

              <div style={{ fontWeight: 900, color: "#34D399", fontSize: 18 }}>
                {typeof item?.score === "number" ? item.score.toFixed(1) : "—"} / 2.0
              </div>
            </div>

            {/* ✅ Description (không hề bỏ) */}
            <div style={{ marginTop: 6, color: "rgba(255,255,255,0.80)", fontSize: 13 }}>
              {item?.description || "No description"}
            </div>

            {/* ✅ Progress (0..2) */}
            <div style={{ marginTop: 8 }}>
              <Progress value={score} max={2} />
            </div>

            {/* ✅ Evidence (không hề bỏ) */}
            {Array.isArray(item?.evidence) && item.evidence.length > 0 && (
              <div style={{ marginTop: 8, display: "grid", gap: 4 }}>
                {item.evidence.map((ev, i) => (
                  <div
                    key={i}
                    style={{
                      fontSize: 12,
                      color: "rgba(255,255,255,0.65)",
                      fontStyle: "italic",
                    }}
                  >
                    → “{ev}”
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}


function SummarySection({ title, items, tone = "neutral" }) {
  if (!items || items.length === 0) return null;

  const toneColor =
    tone === "good"
      ? "rgba(52, 211, 153, 0.18)"
      : tone === "warn"
      ? "rgba(251, 191, 36, 0.18)"
      : tone === "bad"
      ? "rgba(248, 113, 113, 0.18)"
      : "rgba(255,255,255,0.06)";

  const borderColor =
    tone === "good"
      ? "rgba(52, 211, 153, 0.25)"
      : tone === "warn"
      ? "rgba(251, 191, 36, 0.25)"
      : tone === "bad"
      ? "rgba(248, 113, 113, 0.25)"
      : "rgba(255,255,255,0.12)";

  return (
    <div
      style={{
        borderRadius: 16,
        padding: 14,
        border: `1px solid ${borderColor}`,
        background: toneColor,
      }}
    >
      <div style={{ fontWeight: 900, marginBottom: 8 }}>{title}</div>
      <ul style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 6 }}>
        {items.map((x, i) => (
          <li key={i} style={{ color: "rgba(255,255,255,0.85)", fontSize: 13 }}>
            {x}
          </li>
        ))}
      </ul>
    </div>
  );
}

function ScoreSummaryBlock({ knowledgeSummary, attitudeSummary }) {
  const ks = knowledgeSummary || {};
  const as = attitudeSummary || {};

  const strengths = [...(ks.strengths || []), ...(as.strengths || [])];
  const gaps = ks.gaps || [];
  const risks = as.risks || [];
  const improvements = Array.from(
    new Set([...(ks.improvements || []), ...(as.improvements || [])])
  );

  // Nếu không có gì thì khỏi render
  if (
    strengths.length === 0 &&
    gaps.length === 0 &&
    risks.length === 0 &&
    improvements.length === 0
  ) {
    return null;
  }

  return (
    <div
      style={{
        marginTop: 16,
        borderRadius: 18,
        padding: 16,
        border: "1px solid rgba(255,255,255,0.12)",
        background: "rgba(255,255,255,0.06)",
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 900, marginBottom: 12 }}>
        📝 Summary
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: 12,
        }}
      >
        <SummarySection title="✅ Strengths" items={strengths} tone="good" />
        <SummarySection title="⚠️ Gaps" items={gaps} tone="warn" />
        <SummarySection title="🚩 Risks" items={risks} tone="bad" />
        <SummarySection title="🎯 Improvements" items={improvements} tone="neutral" />
      </div>
    </div>
  );
}
function PenaltyInfo({ data }) {
  if (!data) return null;

  const n = data.n_valid_answers ?? data.n_valid ?? 0;
  const minReq = data.min_required ?? 10;
  const factor = data.coverage_factor ?? data.coverage ?? null;
  const bonus = data.bonus ?? 0;

  const factorText =
    typeof factor === "number" ? `${(factor * 100).toFixed(1)}%` : "—";

  // lý do (ưu tiên note từ backend, nếu không có thì tự sinh)
  const reason =
    data.note ||
    (n < minReq
      ? `Only ${n}/${minReq} valid answers → score is downweighted for fairness (insufficient data).`
      : n > minReq
      ? `More than ${minReq} valid answers → small bonus applied (capped).`
      : `Meets minimum ${minReq} valid answers → no penalty.`);

  const boxColor =
    n < minReq ? "rgba(248,113,113,0.15)" : "rgba(52,211,153,0.12)";
  const borderColor =
    n < minReq ? "rgba(248,113,113,0.25)" : "rgba(52,211,153,0.22)";

  return (
    <div
      style={{
        marginTop: 14,
        borderRadius: 18,
        padding: 14,
        border: `1px solid ${borderColor}`,
        background: boxColor,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
        <div style={{ fontWeight: 900 }}>📉 Data sufficiency adjustment</div>
        <div style={{ fontWeight: 900 }}>
          Penalty factor: <span style={{ color: "white" }}>{factorText}</span>
        </div>
      </div>

      <div style={{ marginTop: 6, color: "rgba(255,255,255,0.85)", fontSize: 13 }}>
        {reason}
      </div>

      <div style={{ marginTop: 8, fontSize: 12, color: "rgba(255,255,255,0.70)" }}>
        Valid answers: <b>{n}</b> / {minReq}
        {"  "}• Bonus: <b>{typeof bonus === "number" ? bonus.toFixed(2) : bonus}</b>
      </div>
    </div>
  );
}

export default function InterviewResultCard({ autoEval, onClose }) {
  const [open, setOpen] = useState(false);

  const s = useMemo(() => {
    const a = autoEval || {};
    return {
      total: a.total_score,
      knowledge: a.knowledge_score,
      attitude: a.attitude_score,
      emotion: a.emotion_face_score,
      agentFinal: a.agent_final_score,
      weights: a.detail?.weights,
      formula: a.detail?.formula,
      comps: a.detail?.components,

      roleInference: a.role_inference,
      knowledgeDetail: a.knowledge_detail,
      attitudeDetail: a.attitude_detail,
      knowledgeSummary: a.knowledge_summary,
      attitudeSummary: a.attitude_summary,
      dataSufficiency: a.data_sufficiency || a.detail?.data_sufficiency || null,
    };
  }, [autoEval]);

  const totalScore = typeof s.total === "number" ? s.total : 0;
  const g = colorByScore10(totalScore);

  return (
    <div
      style={{
        borderRadius: 24,
        overflow: "hidden",
        boxShadow: "0 30px 80px rgba(0,0,0,0.55)",
        background: "#0b1020",
        color: "white",
      }}
    >
      {/* Header */}
      <div
        style={{
          position: "relative",
          padding: 24,
          background: `linear-gradient(90deg, ${g.a}, ${g.b})`,
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "rgba(0,0,0,0.18)",
          }}
        />
        <div style={{ position: "relative" }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <div>
              <div style={{ fontSize: 13, opacity: 0.9, fontWeight: 600 }}>
                ✨ Auto Evaluation
              </div>
              <div style={{ marginTop: 4, fontSize: 26, fontWeight: 900 }}>
                Interview Results
              </div>
            </div>

            <button
              onClick={onClose}
              style={{
                height: 34,
                padding: "0 12px",
                borderRadius: 999,
                border: "1px solid rgba(255,255,255,0.35)",
                background: "rgba(255,255,255,0.18)",
                color: "white",
                cursor: "pointer",
              }}
            >
              ✕ Close
            </button>
          </div>

          {s.roleInference && (
            <div
              style={{
                marginTop: 12,
                display: "inline-block",
                borderRadius: 14,
                padding: "8px 12px",
                background: "rgba(255,255,255,0.18)",
                border: "1px solid rgba(255,255,255,0.25)",
              }}
            >
              🎯 Detected Role:{" "}
              <b>{s.roleInference.primary_role || "Unknown"}</b>{" "}
              {s.roleInference.confidence != null
                ? `(${Math.round(s.roleInference.confidence * 100)}%)`
                : ""}
            </div>
          )}

          <div style={{ marginTop: 14, display: "flex", flexWrap: "wrap", gap: 8 }}>
            <span
              style={{
                borderRadius: 999,
                padding: "6px 10px",
                background: "rgba(255,255,255,0.18)",
                border: "1px solid rgba(255,255,255,0.22)",
                fontSize: 12,
              }}
            >
              🤖 Agent: {s.weights?.w_agent_final ?? "?"}
            </span>
            <span
              style={{
                borderRadius: 999,
                padding: "6px 10px",
                background: "rgba(255,255,255,0.18)",
                border: "1px solid rgba(255,255,255,0.22)",
                fontSize: 12,
              }}
            >
              😊 Emotion: {s.weights?.w_emotion ?? "?"}
            </span>
          </div>

          <div
            style={{
              marginTop: 16,
              borderRadius: 18,
              padding: 16,
              background: "rgba(255,255,255,0.16)",
              border: "1px solid rgba(255,255,255,0.22)",
            }}
          >
            <div style={{ fontSize: 13, opacity: 0.9, fontWeight: 700 }}>
              Total Score
            </div>
            <div style={{ marginTop: 6, display: "flex", alignItems: "baseline", gap: 10 }}>
              <div style={{ fontSize: 54, fontWeight: 950 }}>
                {typeof s.total === "number" ? s.total.toFixed(2) : "—"}
              </div>
              <div style={{ fontSize: 18, opacity: 0.8 }}>/ 10</div>
            </div>
            <div style={{ marginTop: 10 }}>
              <Progress value={totalScore} max={10} />
            </div>
          </div>
        </div>
      </div>

      {/* Body */}
      <div
        style={{
          padding: 20,
          background: "linear-gradient(#0f172a, #020617)",
        }}
      >
        <div style={{ marginBottom: 12, fontSize: 18, fontWeight: 900 }}>
          📊 Score Breakdown
        </div>
        
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            gap: 12,
          }}
        >
          <MetricCard label="Knowledge" value={s.knowledge} icon="🧠" />
          <MetricCard label="Attitude" value={s.attitude} icon="💼" />
          <MetricCard label="Emotion" value={s.emotion} icon="😊" />
          <MetricCard label="Agent Final" value={s.agentFinal} icon="🎯" />
        </div>
        {/* penalty factor + reason */}
        <PenaltyInfo data={s.dataSufficiency} />
        {/* Summary before detailed view */}
        <ScoreSummaryBlock
        knowledgeSummary={s.knowledgeSummary}
        attitudeSummary={s.attitudeSummary}
        />
        {/* Details toggle */}
        <div style={{ marginTop: 16 }}>
          <button
            onClick={() => setOpen((v) => !v)}
            style={{
              width: "100%",
              borderRadius: 18,
              padding: 14,
              textAlign: "left",
              border: "1px solid rgba(255,255,255,0.12)",
              background: "rgba(255,255,255,0.06)",
              color: "white",
              cursor: "pointer",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 800 }}>
                {open ? "📖 Hide Detailed Analysis" : "📋 View Detailed Analysis"}
              </div>
              <div style={{ opacity: 0.85 }}>{open ? "▲" : "▼"}</div>
            </div>
          </button>

          {open && (
            <div
              style={{
                marginTop: 12,
                borderRadius: 18,
                padding: 16,
                border: "1px solid rgba(255,255,255,0.12)",
                background: "rgba(255,255,255,0.06)",
              }}
            >
              {/* Knowledge */}
              {s.knowledgeDetail && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 10 }}>
                    🧠 Knowledge Criteria (K1–K5)
                    <span style={{ marginLeft: 10, color: "#34D399" }}>
                      Score: {typeof s.knowledge === "number" ? s.knowledge.toFixed(2) : "—"}
                    </span>
                  </div>
                  <CriteriaDetail group="knowledge" data={s.knowledgeDetail} />
                </div>
              )}

              {/* Attitude */}
              {s.attitudeDetail && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 16, fontWeight: 900, marginBottom: 10 }}>
                    💼 Attitude Criteria (A1–A5)
                    <span style={{ marginLeft: 10, color: "#60A5FA" }}>
                      Score: {typeof s.attitude === "number" ? s.attitude.toFixed(2) : "—"}
                    </span>
                  </div>
                  <CriteriaDetail group="attitude" data={s.attitudeDetail} />
                </div>
              )}

              {/* Raw / formula */}
              <div style={{ marginTop: 10, opacity: 0.9 }}>
                <div style={{ fontWeight: 900, marginBottom: 6 }}>Formula</div>
                <div style={{ fontFamily: "monospace", fontSize: 12, opacity: 0.8 }}>
                  {s.formula ?? "—"}
                </div>

                <div style={{ marginTop: 12, fontWeight: 900, marginBottom: 6 }}>
                  Raw JSON
                </div>
                <pre
                  style={{
                    maxHeight: 280,
                    overflow: "auto",
                    borderRadius: 14,
                    padding: 12,
                    background: "rgba(0,0,0,0.35)",
                    border: "1px solid rgba(255,255,255,0.10)",
                    fontSize: 12,
                    color: "rgba(255,255,255,0.85)",
                  }}
                >
                  {JSON.stringify(autoEval, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end", gap: 10 }}>
          <button
            onClick={onClose}
            style={{
              borderRadius: 14,
              padding: "10px 14px",
              background: "rgba(255,255,255,0.10)",
              border: "1px solid rgba(255,255,255,0.14)",
              color: "white",
              cursor: "pointer",
            }}
          >
            Back to chat
          </button>
          <button
            onClick={() => navigate("/")}
            style={{
              borderRadius: 14,
              padding: "10px 14px",
              background: "white",
              border: "1px solid rgba(255,255,255,0.2)",
              color: "black",
              fontWeight: 800,
              cursor: "pointer",
            }}
            
          >
            Home
          </button>
        </div>
      </div>
    </div>
  );
}
