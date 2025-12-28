import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useState } from "react";
import {
  Mic,
  Briefcase,
  TrendingUp,
  Users,
  Award,
  ArrowRight,
  Zap,
  LogOut,
  User,
  BookOpen
} from "lucide-react";

const Home = () => {
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();
  const [showMockIntro, setShowMockIntro] = useState(false);

  const openMockIntro = () => setShowMockIntro(true);
  const closeMockIntro = () => setShowMockIntro(false);

  const continueMock = () => {
    setShowMockIntro(false);
    navigate("/upload?mode=mock"); // hoặc route bạn muốn vào mock
  };
  return (
    <div style={{ minHeight: "100vh" }}>
      {/* Header */}
      <header
        style={{
          background: "white",
          borderBottom: "1px solid #e5e7eb",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "0 20px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              height: "64px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
              }}
            >
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <span style={{ color: "white", fontWeight: "bold" }}>AI</span>
              </div>
              <span
                style={{
                  fontSize: "24px",
                  fontWeight: "bold",
                  color: "#111827",
                }}
              >
                InterviewAI
              </span>
            </div>

            <nav
              style={{
                display: "flex",
                alignItems: "center",
                gap: "32px",
              }}
            >
              <Link
                to="/"
                style={{
                  color: "#3b82f6",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Home
              </Link>
              <Link
                to="/upload"
                style={{
                  color: "#374151",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Upload
              </Link>
              <Link
                to="/interview"
                style={{
                  color: "#374151",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Interview
              </Link>
            </nav>

            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "16px",
              }}
            >
              {isAuthenticated ? (
                <>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      padding: "8px 16px",
                      borderRadius: "8px",
                      background: "#f3f4f6",
                    }}
                  >
                    <User size={18} color="#6b7280" />
                    <span
                      style={{
                        color: "#374151",
                        fontWeight: "500",
                        fontSize: "0.875rem",
                      }}
                    >
                      {user?.full_name || user?.email}
                    </span>
                  </div>
                  <button
                    onClick={logout}
                    style={{
                      background: "transparent",
                      color: "#374151",
                      border: "1px solid #e5e7eb",
                      padding: "12px 24px",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = "#f9fafb";
                      e.target.style.borderColor = "#d1d5db";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "transparent";
                      e.target.style.borderColor = "#e5e7eb";
                    }}
                  >
                    <LogOut size={18} />
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => navigate("/signin")}
                    style={{
                      background: "transparent",
                      color: "#374151",
                      border: "1px solid #e5e7eb",
                      padding: "12px 24px",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.background = "#f9fafb";
                      e.target.style.borderColor = "#d1d5db";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.background = "transparent";
                      e.target.style.borderColor = "#e5e7eb";
                    }}
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => navigate("/signup")}
                    style={{
                      background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                      color: "white",
                      border: "none",
                      padding: "12px 24px",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.transform = "translateY(-1px)";
                      e.target.style.boxShadow =
                        "0 4px 12px rgba(59, 130, 246, 0.3)";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.transform = "translateY(0)";
                      e.target.style.boxShadow = "none";
                    }}
                  >
                    Sign Up
                  </button>
                </>
              )}
              <button
                onClick={() => navigate("/interview")}
                style={{
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  color: "white",
                  border: "none",
                  padding: "12px 24px",
                  borderRadius: "8px",
                  fontWeight: "600",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  transition: "all 0.2s",
                }}
                onMouseEnter={(e) => {
                  e.target.style.transform = "translateY(-1px)";
                  e.target.style.boxShadow =
                    "0 4px 12px rgba(59, 130, 246, 0.3)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.transform = "translateY(0)";
                  e.target.style.boxShadow = "none";
                }}
              >
                Start Interview
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section
        style={{
          background: "linear-gradient(135deg, #1e40af, #7c3aed, #4338ca)",
          color: "white",
          padding: "80px 20px",
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: "800px", margin: "0 auto" }}>
          <h1
            style={{
              fontSize: "3.5rem",
              fontWeight: "800",
              marginBottom: "24px",
              lineHeight: "1.2",
            }}
          >
            Practice Your Interview
            <br />
            with AI Interviewer
          </h1>
          <p
            style={{
              fontSize: "1.25rem",
              marginBottom: "40px",
              opacity: 0.9,
              lineHeight: "1.6",
            }}
          >
            Get real-time feedback and improve your interview skills with our
            AI-powered interview simulator
          </p>
          <div
            style={{ display: "flex", gap: "16px", justifyContent: "center" }}
          >
            <button
              onClick={() => navigate("/upload?mode=practice")}
              style={{
                background: "white",
                color: "#3b82f6",
                border: "none",
                padding: "16px 32px",
                borderRadius: "8px",
                fontWeight: "700",
                cursor: "pointer",
                fontSize: "1.1rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              Start Interview
              <Mic size={20} />
            </button>
            {/* Nút mới Mock Interview */}
            <button
              onClick={openMockIntro}
              style={{
                background: "white",
                color: "#3b82f6",
                border: "none",
                padding: "16px 32px",
                borderRadius: "8px",
                fontWeight: "700",
                cursor: "pointer",
                fontSize: "1.1rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              Mock Interview
              <Briefcase size={20} />
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section style={{ padding: "80px 20px", background: "#f9fafb" }}>
        <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
          <h2
            style={{
              textAlign: "center",
              fontSize: "2.5rem",
              fontWeight: "700",
              marginBottom: "16px",
              color: "#111827",
            }}
          >
            Why Choose InterviewAI?
          </h2>
          <p
            style={{
              textAlign: "center",
              fontSize: "1.125rem",
              color: "#6b7280",
              marginBottom: "64px",
              maxWidth: "600px",
              margin: "0 auto 64px",
            }}
          >
            Experience the most realistic AI interview platform
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: "32px",
            }}
          >
            {/* Feature 1 */}
            <Link
              to="/upload?mode=practice"
              className="card"
              style={{
                textDecoration: "none", // không gạch chân
                color: "inherit",
                display: "block",
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <Mic size={32} color="white" />
              </div>
              <h3
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#111827",
                }}
              >
                Voice Interview (Practice)
              </h3>
              <p style={{ color: "#6b7280", lineHeight: "1.6" }}>
                Practice with natural voice conversations and get instant
                feedback on your responses
              </p>
            </Link>

            {/* Feature 2 */}
            <Link
              to="#"
              onClick={(e) => {
                e.preventDefault();
                openMockIntro();        
              }}
              className="card"
              style={{
                textDecoration: "none",
                color: "inherit",
                display: "block",
                cursor: "pointer",
              }}
            >
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <BookOpen size={32} color="white" />
              </div>

              <h3 style={{ fontSize: "1.5rem", fontWeight: 700, marginBottom: 12, color: "#111827" }}>
                Mock Interview
              </h3>

              <p style={{ color: "#6b7280", lineHeight: 1.6 }}>
                Practice with AI and get a score.
              </p>
            </Link>




            {/* Feature 3 */}
            <div className="card">
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #f59e0b, #d97706)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <TrendingUp size={32} color="white" />
              </div>
              <h3
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#111827",
                }}
              >
                Performance Analytics (comming soon)
              </h3>
              <p
                style={{
                  color: "#6b7280",
                  lineHeight: "1.6",
                }}
              >
                Track your progress with detailed analytics and insights on your
                interview performance
              </p>
            </div>

            {/* Feature 4 */}
            <div className="card">
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #8b5cf6, #6d28d9)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <Users size={32} color="white" />
              </div>
              <h3
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#111827",
                }}
              >
                24/7 Availability (comming soon)
              </h3>
              <p
                style={{
                  color: "#6b7280",
                  lineHeight: "1.6",
                }}
              >
                Practice anytime, anywhere with our AI interviewer available
                round the clock
              </p>
            </div>

            {/* Feature 5 */}
            <div className="card">
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #ef4444, #dc2626)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <Award size={32} color="white" />
              </div>
              <h3
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#111827",
                }}
              >
                Expert Feedback (comming soon)
              </h3>
              <p
                style={{
                  color: "#6b7280",
                  lineHeight: "1.6",
                }}
              >
                Receive constructive feedback to improve your communication and
                problem-solving skills
              </p>
            </div>

            {/* Feature 6 */}
            <div className="card">
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  background: "linear-gradient(135deg, #06b6d4, #0891b2)",
                  borderRadius: "16px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  marginBottom: "24px",
                }}
              >
                <Zap size={32} color="white" />
              </div>
              <h3
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  marginBottom: "12px",
                  color: "#111827",
                }}
              >
                Instant Results (comming soon)
              </h3>
              <p
                style={{
                  color: "#6b7280",
                  lineHeight: "1.6",
                }}
              >
                Get immediate feedback on your answers to help you improve in
                real-time
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        style={{
          background: "linear-gradient(135deg, #1e40af, #7c3aed)",
          padding: "80px 20px",
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: "800px", margin: "0 auto" }}>
          <h2
            style={{
              fontSize: "2.5rem",
              fontWeight: "800",
              marginBottom: "24px",
              color: "white",
            }}
          >
            Ready to Ace Your Interview?
          </h2>
          <p
            style={{
              fontSize: "1.25rem",
              marginBottom: "40px",
              opacity: 0.9,
              color: "white",
            }}
          >
            Start practicing now and boost your confidence for your next
            interview
          </p>
          <button
            onClick={() => navigate("/interview")}
            style={{
              background: "white",
              color: "#3b82f6",
              border: "none",
              padding: "16px 48px",
              borderRadius: "8px",
              fontWeight: "700",
              cursor: "pointer",
              fontSize: "1.125rem",
            }}
          >
            Get Started Now
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          background: "#111827",
          color: "white",
          padding: "48px 20px",
          textAlign: "center",
        }}
      >
        <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              marginBottom: "24px",
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                borderRadius: "12px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <span style={{ color: "white", fontWeight: "bold" }}>AI</span>
            </div>
            <span style={{ fontSize: "24px", fontWeight: "bold" }}>
              InterviewAI
            </span>
          </div>
          <p style={{ color: "#9ca3af", marginBottom: "24px" }}>
            © 2024 InterviewAI. All rights reserved.
          </p>
        </div>
      </footer>
    {showMockIntro && (
  <div
    style={{
      position: "fixed",
      inset: 0,
      zIndex: 9999,
    }}
  >
    {/* overlay mờ */}
    <div
      onClick={closeMockIntro}
      style={{
        position: "absolute",
        inset: 0,
        background: "rgba(0,0,0,0.45)",
        backdropFilter: "blur(6px)",
      }}
    />

    {/* modal */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 760,
          borderRadius: 20,
          overflow: "hidden",
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
          background: "white",
        }}
      >
        {/* header gradient */}
        <div
          style={{
            padding: "18px 20px",
            color: "white",
            background: "linear-gradient(135deg, #1e40af, #7c3aed, #4338ca)",
            display: "flex",
            alignItems: "flex-start",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div>
            <div style={{ fontSize: 18, fontWeight: 800 }}>
              Mock Interview Rules & Scoring
            </div>
            <div style={{ marginTop: 6, opacity: 0.9, fontSize: 13, lineHeight: 1.4 }}>
              Please read before starting to get the most accurate result.
            </div>
          </div>

          <button
            onClick={closeMockIntro}
            style={{
              background: "rgba(255,255,255,0.15)",
              color: "white",
              border: "1px solid rgba(255,255,255,0.25)",
              padding: "8px 10px",
              borderRadius: 10,
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            ✕
          </button>
        </div>

        {/* body */}
        <div style={{ padding: 20 }}>
          {/* key points */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: 12,
            }}
          >
            <div style={{ border: "1px solid #e5e7eb", borderRadius: 14, padding: 14, background: "#f9fafb" }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Time limit</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "#111827", marginTop: 4 }}>
                50 minutes
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>
                Try to answer calmly and clearly.
              </div>
            </div>

            <div style={{ border: "1px solid #e5e7eb", borderRadius: 14, padding: 14, background: "#f9fafb" }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Minimum answers</div>
              <div style={{ fontSize: 20, fontWeight: 800, color: "#111827", marginTop: 4 }}>
                ≥ 10 answers
              </div>
              <div style={{ fontSize: 12, color: "#b45309", marginTop: 6 }}>
                Below 10 answers → penalty applies.
              </div>
            </div>

            <div style={{ border: "1px solid #e5e7eb", borderRadius: 14, padding: 14, background: "#f9fafb" }}>
              <div style={{ fontSize: 12, color: "#6b7280" }}>Scoring signals</div>
              <div style={{ fontSize: 14, fontWeight: 700, marginTop: 6, color: "#111827" }}>
                Knowledge • Attitude • Emotion
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 6 }}>
                Final score combines interview + face emotion.
              </div>
            </div>
          </div>

          {/* scoring explanation */}
          <div style={{ marginTop: 16, border: "1px solid #e5e7eb", borderRadius: 14, padding: 14 }}>
            <div style={{ fontWeight: 800, color: "#111827" }}>How the score is calculated</div>

            <ul style={{ marginTop: 10, paddingLeft: 18, color: "#374151", lineHeight: 1.6, fontSize: 14 }}>
              <li><b>Knowledge</b>: correctness + completeness + relevance to each question.</li>
              <li><b>Attitude</b>: professionalism, cooperation, calm tone, admits gaps honestly.</li>
              <li><b>Emotion</b>: face emotion stability during the session.</li>
              <li><b>Penalty</b>: if you answer <b>&lt; 10</b> questions, we down-weight fairness and reduce confidence.</li>
            </ul>

            <div
              style={{
                marginTop: 10,
                padding: 12,
                borderRadius: 12,
                background: "#f3f4f6",
                fontFamily: "monospace",
                fontSize: 12,
                color: "#111827",
                overflowX: "auto",
              }}
            >
              total = agent_final * w_agent_final + emotion_face * w_emotion
            </div>

            <div style={{ marginTop: 8, fontSize: 12, color: "#6b7280" }}>
              Tip: For the most reliable result, spend time answering fully and consistently.
            </div>
          </div>
        </div>

        {/* footer */}
        <div
          style={{
            padding: 16,
            borderTop: "1px solid #e5e7eb",
            display: "flex",
            justifyContent: "flex-end",
            gap: 10,
            background: "white",
          }}
        >
          <button
            onClick={closeMockIntro}
            style={{
              background: "transparent",
              color: "#374151",
              border: "1px solid #e5e7eb",
              padding: "12px 18px",
              borderRadius: 10,
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            Back
          </button>

          <button
            onClick={continueMock}
            style={{
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              color: "white",
              border: "none",
              padding: "12px 18px",
              borderRadius: 10,
              fontWeight: 800,
              cursor: "pointer",
            }}
          >
            Continue
          </button>
        </div>
      </div>
    </div>
  </div>
)}

    </div>
  );
};

export default Home;
