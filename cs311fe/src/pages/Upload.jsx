import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Upload,
  FileText,
  CheckCircle,
  XCircle,
  ArrowRight,
  File,
} from "lucide-react";
import { v4 as uuidv4 } from "uuid";

const API_URL = "http://localhost:3005";

const UploadPage = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const mode = params.get("mode") == "mock" ? "mock" : "practice"; // 'practice' or 'mock'
  const [cvFile, setCvFile] = useState(null);
  const [jdText, setJdText] = useState("");
  const [sessionId, setSessionId] = useState(() => uuidv4());
  const [cvUploading, setCvUploading] = useState(false);
  const [jdUploading, setJdUploading] = useState(false);
  const [cvStatus, setCvStatus] = useState(null); // 'success' | 'error' | null
  const [jdStatus, setJdStatus] = useState(null);
  const [cvError, setCvError] = useState("");
  const [jdError, setJdError] = useState("");
  const [cvData, setCvData] = useState(null);
  const [jdData, setJdData] = useState(null);

  const handleCvFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const allowedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      ];
      if (!allowedTypes.includes(file.type)) {
        setCvError("Please upload a PDF or DOCX file");
        setCvFile(null);
        setCvStatus("error");
        return;
      }
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setCvError("File size must be less than 10MB");
        setCvFile(null);
        setCvStatus("error");
        return;
      }
      setCvFile(file);
      setCvError("");
      setCvStatus(null);
    }
  };

  const handleCvUpload = async () => {
    if (!cvFile) {
      setCvError("Please select a file first");
      setCvStatus("error");
      return;
    }

    setCvUploading(true);
    setCvError("");
    setCvStatus(null);

    try {
      const formData = new FormData();
      formData.append("file", cvFile);
      formData.append("session_id", sessionId);

      const response = await fetch(`${API_URL}/chat/extract-cv/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to upload CV");
      }

      const data = await response.json();
      setCvData(data.resume_data);
      setCvStatus("success");
    } catch (error) {
      console.error("CV upload error:", error);
      setCvError(error.message || "Failed to upload CV. Please try again.");
      setCvStatus("error");
    } finally {
      setCvUploading(false);
    }
  };

  const handleJdUpload = async () => {
    if (!jdText.trim()) {
      setJdError("Please enter a job description");
      setJdStatus("error");
      return;
    }

    setJdUploading(true);
    setJdError("");
    setJdStatus(null);

    try {
      const formData = new FormData();
      formData.append("job_description", jdText);
      console.log("jdText:", jdText);
      formData.append("session_id", sessionId);

      const response = await fetch(`${API_URL}/chat/extract-job/`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || "Failed to extract job description"
        );
      }

      const data = await response.json();
      setJdData(data.job_data);
      setJdStatus("success");
    } catch (error) {
      console.error("JD upload error:", error);
      setJdError(
        error.message || "Failed to extract job description. Please try again."
      );
      setJdStatus("error");
    } finally {
      setJdUploading(false);
    }
  };

  async function startMockSession(sessionId, cvData, jdData) {
    const payload = {
      session_id: sessionId,
      cv_text: cvData && cvData.text ? cvData.text : String(cvData || ""),
      jd_text: (jdText && jdText.trim()) ? jdText : (jdData?.text ?? JSON.stringify(jdData ?? "")),
    };
    const res = await fetch(`${API_URL}/mock/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `mock/start failed: ${res.status}`);
    }
    return res.json();
  }
  const canProceed = cvStatus === "success" && jdStatus === "success";

  const handleStartInterview = async () => {
    if (!canProceed) return;
    localStorage.setItem("interview_session_id", sessionId);
    if (mode === "mock") {
      try {
        const resp = await startMockSession(sessionId, cvData, jdData);
        localStorage.setItem("mock_first_question", resp?.first_question || "");
      } catch (e) {
        console.error(e);
      }
      navigate("/mock", { state: { sessionId } });
    } else {
      navigate("/interview", { state: { sessionId } });
    }
  };

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
              <a
                href="/"
                style={{
                  color: "#374151",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Home
              </a>
              <a
                href="/upload"
                style={{
                  color: "#3b82f6",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Upload
              </a>
              <a
                href="/interview"
                style={{
                  color: "#374151",
                  fontWeight: "500",
                  textDecoration: "none",
                }}
              >
                Interview
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div
        style={{ maxWidth: "900px", margin: "0 auto", padding: "40px 20px" }}
      >
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h1
            style={{
              fontSize: "2.5rem",
              fontWeight: "800",
              marginBottom: "16px",
              color: "#111827",
            }}
          >
            Upload Your CV & Job Description
          </h1>
          <p
            style={{
              fontSize: "1.125rem",
              color: "#6b7280",
              maxWidth: "600px",
              margin: "0 auto",
            }}
          >
            Upload your resume and job description to get personalized interview
            questions
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
            gap: "32px",
            marginBottom: "40px",
          }}
        >
          {/* CV Upload Section */}
          <div className="card" style={{ padding: "32px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "24px",
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <FileText size={24} color="white" />
              </div>
              <h2
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  color: "#111827",
                }}
              >
                Upload CV
              </h2>
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "12px",
                  fontWeight: "600",
                  color: "#374151",
                }}
              >
                Select File (PDF or DOCX)
              </label>
              <div
                style={{
                  border: "2px dashed #d1d5db",
                  borderRadius: "12px",
                  padding: "32px",
                  textAlign: "center",
                  cursor: "pointer",
                  transition: "all 0.2s",
                  background: cvFile ? "#f0f9ff" : "white",
                  borderColor: cvFile ? "#3b82f6" : "#d1d5db",
                }}
              >
                <input
                  type="file"
                  accept=".pdf,.docx"
                  onChange={handleCvFileChange}
                  style={{ display: "none" }}
                  id="cv-upload"
                />
                <label htmlFor="cv-upload" style={{ cursor: "pointer" }}>
                  {cvFile ? (
                    <div>
                      <File
                        size={48}
                        color="#3b82f6"
                        style={{ marginBottom: "12px" }}
                      />
                      <p style={{ color: "#3b82f6", fontWeight: "600" }}>
                        {cvFile.name}
                      </p>
                      <p
                        style={{
                          color: "#6b7280",
                          fontSize: "0.875rem",
                          marginTop: "8px",
                        }}
                      >
                        {(cvFile.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <Upload
                        size={48}
                        color="#9ca3af"
                        style={{ marginBottom: "12px" }}
                      />
                      <p style={{ color: "#6b7280", fontWeight: "500" }}>
                        Click to select or drag and drop
                      </p>
                      <p
                        style={{
                          color: "#9ca3af",
                          fontSize: "0.875rem",
                          marginTop: "8px",
                        }}
                      >
                        PDF or DOCX (max 10MB)
                      </p>
                    </div>
                  )}
                </label>
              </div>
            </div>

            {cvError && (
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <XCircle size={20} color="#dc2626" />
                <p
                  style={{ color: "#dc2626", fontSize: "0.875rem", margin: 0 }}
                >
                  {cvError}
                </p>
              </div>
            )}

            {cvStatus === "success" && (
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #86efac",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <CheckCircle size={20} color="#16a34a" />
                <p
                  style={{ color: "#16a34a", fontSize: "0.875rem", margin: 0 }}
                >
                  CV uploaded and extracted successfully!
                </p>
              </div>
            )}

            <button
              onClick={handleCvUpload}
              disabled={!cvFile || cvUploading}
              style={{
                width: "100%",
                background:
                  cvFile && !cvUploading
                    ? "linear-gradient(135deg, #3b82f6, #8b5cf6)"
                    : "#e5e7eb",
                color: cvFile && !cvUploading ? "white" : "#9ca3af",
                border: "none",
                padding: "14px 24px",
                borderRadius: "8px",
                fontWeight: "600",
                cursor: cvFile && !cvUploading ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                transition: "all 0.2s",
              }}
            >
              {cvUploading ? (
                <>Uploading...</>
              ) : (
                <>
                  <Upload size={18} />
                  Upload CV
                </>
              )}
            </button>
          </div>

          {/* JD Upload Section */}
          <div className="card" style={{ padding: "32px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                marginBottom: "24px",
              }}
            >
              <div
                style={{
                  width: "48px",
                  height: "48px",
                  background: "linear-gradient(135deg, #10b981, #059669)",
                  borderRadius: "12px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <FileText size={24} color="white" />
              </div>
              <h2
                style={{
                  fontSize: "1.5rem",
                  fontWeight: "700",
                  color: "#111827",
                }}
              >
                Job Description
              </h2>
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "12px",
                  fontWeight: "600",
                  color: "#374151",
                }}
              >
                Paste Job Description
              </label>
              <textarea
                value={jdText}
                onChange={(e) => {
                  setJdText(e.target.value);
                  setJdError("");
                  setJdStatus(null);
                }}
                placeholder="Paste the job description here..."
                style={{
                  width: "100%",
                  minHeight: "200px",
                  padding: "16px",
                  border: "2px solid #e5e7eb",
                  borderRadius: "12px",
                  fontSize: "1rem",
                  fontFamily: "inherit",
                  resize: "vertical",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => (e.target.style.borderColor = "#3b82f6")}
                onBlur={(e) => (e.target.style.borderColor = "#e5e7eb")}
              />
            </div>

            {jdError && (
              <div
                style={{
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <XCircle size={20} color="#dc2626" />
                <p
                  style={{ color: "#dc2626", fontSize: "0.875rem", margin: 0 }}
                >
                  {jdError}
                </p>
              </div>
            )}

            {jdStatus === "success" && (
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #86efac",
                  borderRadius: "8px",
                  padding: "12px",
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <CheckCircle size={20} color="#16a34a" />
                <p
                  style={{ color: "#16a34a", fontSize: "0.875rem", margin: 0 }}
                >
                  Job description extracted successfully!
                </p>
              </div>
            )}

            <button
              onClick={handleJdUpload}
              disabled={!jdText.trim() || jdUploading}
              style={{
                width: "100%",
                background:
                  jdText.trim() && !jdUploading
                    ? "linear-gradient(135deg, #10b981, #059669)"
                    : "#e5e7eb",
                color: jdText.trim() && !jdUploading ? "white" : "#9ca3af",
                border: "none",
                padding: "14px 24px",
                borderRadius: "8px",
                fontWeight: "600",
                cursor:
                  jdText.trim() && !jdUploading ? "pointer" : "not-allowed",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                transition: "all 0.2s",
              }}
            >
              {jdUploading ? (
                <>Extracting...</>
              ) : (
                <>
                  <Upload size={18} />
                  Extract Job Description
                </>
              )}
            </button>
          </div>
        </div>

        {/* Start Interview Button */}
        <div style={{ textAlign: "center", marginTop: "48px" }}>
          <button
            onClick={handleStartInterview}
            disabled={!canProceed}
            style={{
              background:
                cvStatus === "success" && jdStatus === "success"
                  ? "linear-gradient(135deg, #3b82f6, #8b5cf6)"
                  : "#e5e7eb",
              color:
                cvStatus === "success" && jdStatus === "success"
                  ? "white"
                  : "#9ca3af",
              border: "none",
              padding: "18px 48px",
              borderRadius: "12px",
              fontWeight: "700",
              fontSize: "1.125rem",
              cursor:
                cvStatus === "success" && jdStatus === "success"
                  ? "pointer"
                  : "not-allowed",
              display: "inline-flex",
              alignItems: "center",
              gap: "12px",
              transition: "all 0.2s",
              boxShadow:
                cvStatus === "success" && jdStatus === "success"
                  ? "0 4px 15px 0 rgba(59, 130, 246, 0.35)"
                  : "none",
            }}
          >
            {mode === "mock" ? "Mock Interview" : "Start Interview"}
            <ArrowRight size={20} />
          </button>
          {!canProceed && (
            <p
              style={{
                color: "#6b7280",
                fontSize: "0.875rem",
                marginTop: "16px",
              }}
            >
              Please upload both CV and Job Description to continue
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
