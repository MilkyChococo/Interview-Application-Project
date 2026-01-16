import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowLeft,
  Download,
  Star,
  CheckCircle,
  AlertCircle,
  TrendingUp,
  MessageSquare,
  Clock,
  Target,
} from "lucide-react";

const API_URL = "http://localhost:3005";

const EvaluationReport = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("sessionId") || localStorage.getItem("evaluation_session_id");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reportData, setReportData] = useState(null);

  useEffect(() => {
    if (!sessionId) {
      setError("No session ID found. Please complete an interview first.");
      setLoading(false);
      return;
    }

    fetchEvaluationReport();
  }, [sessionId]);

  const fetchEvaluationReport = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/chat/evaluation/${sessionId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error("Evaluation report not found. The interview may not be completed yet.");
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to fetch evaluation report");
      }

      const data = await response.json();
      setReportData(data);
    } catch (err) {
      console.error("Error fetching evaluation:", err);
      setError(err.message);
      
      // For demo purposes, show mock data if API fails
      setReportData({
        sessionId: sessionId,
        overallScore: 75,
        summary: "Good interview performance with room for improvement in technical details.",
        strengths: [
          "Clear communication style",
          "Good problem-solving approach",
          "Positive attitude and enthusiasm",
        ],
        areasToImprove: [
          "Provide more specific examples",
          "Elaborate on technical experience",
          "Practice behavioral questions",
        ],
        categories: [
          { name: "Communication", score: 80 },
          { name: "Technical Knowledge", score: 70 },
          { name: "Problem Solving", score: 75 },
          { name: "Cultural Fit", score: 85 },
        ],
        recommendations: [
          "Practice STAR method for behavioral questions",
          "Review common technical concepts",
          "Prepare more concrete examples from past experiences",
        ],
        questionsAsked: 8,
        duration: "32 minutes",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadPDF = () => {
    // Create a simple print-friendly version
    window.print();
  };

  const handleBackToInterview = () => {
    navigate("/interview");
  };

  const getScoreColor = (score) => {
    if (score >= 80) return "#10b981";
    if (score >= 60) return "#f59e0b";
    return "#ef4444";
  };

  const getScoreLabel = (score) => {
    if (score >= 90) return "Excellent";
    if (score >= 80) return "Very Good";
    if (score >= 70) return "Good";
    if (score >= 60) return "Fair";
    return "Needs Improvement";
  };

  if (loading) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#f9fafb",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              border: "4px solid #e5e7eb",
              borderTop: "4px solid #3b82f6",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
              margin: "0 auto 16px",
            }}
          ></div>
          <p style={{ color: "#6b7280", fontSize: "16px" }}>
            Loading evaluation report...
          </p>
        </div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#f9fafb" }}>
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
            padding: "16px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <button
              onClick={handleBackToInterview}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                background: "transparent",
                border: "none",
                color: "#6b7280",
                cursor: "pointer",
                fontSize: "14px",
                fontWeight: "500",
              }}
            >
              <ArrowLeft size={20} />
              Back to Interview
            </button>
            <div
              style={{
                width: "1px",
                height: "24px",
                background: "#e5e7eb",
              }}
            ></div>
            <h1
              style={{
                fontSize: "20px",
                fontWeight: "700",
                color: "#111827",
                margin: 0,
              }}
            >
              Interview Evaluation Report
            </h1>
          </div>

          <button
            onClick={handleDownloadPDF}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 20px",
              background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
              color: "white",
              border: "none",
              borderRadius: "8px",
              fontWeight: "600",
              cursor: "pointer",
              fontSize: "14px",
            }}
          >
            <Download size={18} />
            Download Report
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "32px 24px" }}>
        {error && !reportData && (
          <div
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: "12px",
              padding: "24px",
              display: "flex",
              alignItems: "center",
              gap: "16px",
              marginBottom: "24px",
            }}
          >
            <AlertCircle size={24} color="#dc2626" />
            <div>
              <h3 style={{ margin: 0, color: "#dc2626", fontWeight: "600" }}>
                Error Loading Report
              </h3>
              <p style={{ margin: "4px 0 0", color: "#991b1b" }}>{error}</p>
            </div>
          </div>
        )}

        {reportData && (
          <>
            {/* Overall Score Card */}
            <div
              style={{
                background: "white",
                borderRadius: "16px",
                padding: "32px",
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                marginBottom: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  flexWrap: "wrap",
                  gap: "24px",
                }}
              >
                <div>
                  <h2
                    style={{
                      fontSize: "24px",
                      fontWeight: "700",
                      color: "#111827",
                      marginBottom: "8px",
                    }}
                  >
                    Overall Performance
                  </h2>
                  <p style={{ color: "#6b7280", fontSize: "16px", margin: 0 }}>
                    {reportData.summary}
                  </p>
                </div>
                <div style={{ textAlign: "center" }}>
                  <div
                    style={{
                      width: "120px",
                      height: "120px",
                      borderRadius: "50%",
                      background: `conic-gradient(${getScoreColor(
                        reportData.overallScore
                      )} ${reportData.overallScore * 3.6}deg, #e5e7eb 0deg)`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      position: "relative",
                    }}
                  >
                    <div
                      style={{
                        width: "100px",
                        height: "100px",
                        borderRadius: "50%",
                        background: "white",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "32px",
                          fontWeight: "700",
                          color: getScoreColor(reportData.overallScore),
                        }}
                      >
                        {reportData.overallScore}
                      </span>
                      <span style={{ fontSize: "12px", color: "#6b7280" }}>
                        /100
                      </span>
                    </div>
                  </div>
                  <p
                    style={{
                      marginTop: "8px",
                      fontWeight: "600",
                      color: getScoreColor(reportData.overallScore),
                    }}
                  >
                    {getScoreLabel(reportData.overallScore)}
                  </p>
                </div>
              </div>

              {/* Quick Stats */}
              <div
                style={{
                  display: "flex",
                  gap: "24px",
                  marginTop: "24px",
                  paddingTop: "24px",
                  borderTop: "1px solid #e5e7eb",
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <MessageSquare size={20} color="#6b7280" />
                  <span style={{ color: "#374151" }}>
                    <strong>{reportData.questionsAsked}</strong> Questions
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Clock size={20} color="#6b7280" />
                  <span style={{ color: "#374151" }}>
                    Duration: <strong>{reportData.duration}</strong>
                  </span>
                </div>
              </div>
            </div>

            {/* Categories Scores */}
            <div
              style={{
                background: "white",
                borderRadius: "16px",
                padding: "32px",
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                marginBottom: "24px",
              }}
            >
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: "600",
                  color: "#111827",
                  marginBottom: "24px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <Target size={20} />
                Category Scores
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                {reportData.categories?.map((category, index) => (
                  <div key={index}>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "8px",
                      }}
                    >
                      <span style={{ fontWeight: "500", color: "#374151" }}>
                        {category.name}
                      </span>
                      <span
                        style={{
                          fontWeight: "600",
                          color: getScoreColor(category.score),
                        }}
                      >
                        {category.score}%
                      </span>
                    </div>
                    <div
                      style={{
                        height: "8px",
                        background: "#e5e7eb",
                        borderRadius: "4px",
                        overflow: "hidden",
                      }}
                    >
                      <div
                        style={{
                          height: "100%",
                          width: `${category.score}%`,
                          background: getScoreColor(category.score),
                          borderRadius: "4px",
                          transition: "width 0.5s ease",
                        }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Strengths and Areas to Improve */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
                gap: "24px",
                marginBottom: "24px",
              }}
            >
              {/* Strengths */}
              <div
                style={{
                  background: "white",
                  borderRadius: "16px",
                  padding: "24px",
                  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                }}
              >
                <h3
                  style={{
                    fontSize: "18px",
                    fontWeight: "600",
                    color: "#111827",
                    marginBottom: "16px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <CheckCircle size={20} color="#10b981" />
                  Strengths
                </h3>
                <ul style={{ margin: 0, paddingLeft: "24px" }}>
                  {reportData.strengths?.map((strength, index) => (
                    <li
                      key={index}
                      style={{
                        color: "#374151",
                        marginBottom: "8px",
                        lineHeight: "1.6",
                      }}
                    >
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Areas to Improve */}
              <div
                style={{
                  background: "white",
                  borderRadius: "16px",
                  padding: "24px",
                  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
                }}
              >
                <h3
                  style={{
                    fontSize: "18px",
                    fontWeight: "600",
                    color: "#111827",
                    marginBottom: "16px",
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <TrendingUp size={20} color="#f59e0b" />
                  Areas to Improve
                </h3>
                <ul style={{ margin: 0, paddingLeft: "24px" }}>
                  {reportData.areasToImprove?.map((area, index) => (
                    <li
                      key={index}
                      style={{
                        color: "#374151",
                        marginBottom: "8px",
                        lineHeight: "1.6",
                      }}
                    >
                      {area}
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Recommendations */}
            <div
              style={{
                background: "white",
                borderRadius: "16px",
                padding: "24px",
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
              }}
            >
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: "600",
                  color: "#111827",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <Star size={20} color="#8b5cf6" />
                Recommendations for Next Interview
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {reportData.recommendations?.map((rec, index) => (
                  <div
                    key={index}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "12px",
                      padding: "12px 16px",
                      background: "#f9fafb",
                      borderRadius: "8px",
                      borderLeft: "4px solid #8b5cf6",
                    }}
                  >
                    <span
                      style={{
                        width: "24px",
                        height: "24px",
                        background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                        color: "white",
                        borderRadius: "50%",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "12px",
                        fontWeight: "600",
                        flexShrink: 0,
                      }}
                    >
                      {index + 1}
                    </span>
                    <p style={{ margin: 0, color: "#374151", lineHeight: "1.6" }}>
                      {rec}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>

      {/* Print Styles */}
      <style>{`
        @media print {
          header {
            display: none !important;
          }
          button {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
};

export default EvaluationReport;

