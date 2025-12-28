import { useState, useEffect, useRef } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import CharacterPanel from "../components/CharacterPanel";
import ChatPanel from "../components/ChatPanel";
import Resizer from "../components/Resizer";
import useVoiceRecognition from "../hooks/useVoiceRecognition";
import { v4 as uuidv4 } from "uuid";
import InterviewResultCard from "../components/InterviewResult";

const API_URL = "http://localhost:3005";

const MockInterview = () => {
  const [autoEval, setAutoEval] = useState(null);
  const [showEval, setShowEval] = useState(false);
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [chatPanelWidth, setChatPanelWidth] = useState(480);
  const isResizing = useRef(false);
  const [sessionId, setSessionId] = useState(null);
  const location = useLocation();
  const [messages, setMessages] = useState([]);

  const [remainingSeconds, setRemainingSeconds] = useState(50 * 60);
  const [questionCount, setQuestionCount] = useState(0);
  const [isTimeUp, setIsTimeUp] = useState(false);
  const [hasAutoSaved, setHasAutoSaved] = useState(false);
  const [phase, setPhase] = useState("running"); 

  const emotionStartedRef = useRef(false);
  
  const handleHome = async () => {
    const sid = sessionId || localStorage.getItem("interview_session_id");
    try {
      if (isRecording) stopRecording();

      if (sid) {
        await fetch(`${API_URL}/emotion/stop`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sid }),
        });
      }
    } finally {
      navigate("/");
    }
  };

  useEffect(() => {
    const sid = sessionId || localStorage.getItem("interview_session_id");
    if (!sid || emotionStartedRef.current) return;

    emotionStartedRef.current = true;
    fetch(`${API_URL}/emotion/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid }),
    });

    return () => {
      if (import.meta.env.DEV) return;
      fetch(`${API_URL}/emotion/stop`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sid }),
      });
    };
  }, [sessionId]);

  useEffect(() => {
    if (remainingSeconds <= 0) return;
    const id = setInterval(
      () => setRemainingSeconds((s) => Math.max(0, s - 1)),
      1000
    );
    return () => clearInterval(id);
  }, [remainingSeconds]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/signin");
      return;
    }

    const stateSessionId = location.state?.sessionId;
    const storedSessionId = localStorage.getItem("interview_session_id");
    const finalSessionId = stateSessionId || storedSessionId || uuidv4();

    setSessionId(finalSessionId);
    console.log("Interview page sessionId:", finalSessionId);

    localStorage.setItem("interview_session_id", finalSessionId);

    const savedFirst = localStorage.getItem("mock_first_question");
    if (!savedFirst) {
      navigate("/upload?mode=mock");
      return;
    }
    const firstQ =
      savedFirst || "Hello! Let's start. Can you introduce yourself?";
    setMessages([
      { id: 1, type: "bot", message: firstQ, timestamp: new Date() },
    ]);
    setQuestionCount(1);
  }, [location.state, isAuthenticated, navigate]);

  const { isRecording, transcript, startRecording, stopRecording, speak } =
    useVoiceRecognition();

  useEffect(() => {
  const sid = sessionId || localStorage.getItem("interview_session_id");
  if (!sid) return;

  if (remainingSeconds === 0 && !hasAutoSaved) {
    (async () => {
      setHasAutoSaved(true);
      setIsTimeUp(true);

      // 1) KHÓA INPUT + STOP RECORD
      setPhase("saving");
      if (isRecording) stopRecording();

      // 2) THÔNG BÁO "ĐANG TỔNG KẾT"
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          type: "bot",
          message:
            "Time's up. I'm saving your transcript and generating the interview summary...",
          timestamp: new Date(),
        },
      ]);

      // ❌ BỎ SPEAK để không nói nữa
      // speak("Time's up! I'm saving your transcript now.");

      try {
        // stop emotion logging (không quan trọng nếu fail)
        await fetch(`${API_URL}/emotion/stop`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sid }),
        });
      } catch (e) {
        console.error("emotion stop error:", e);
      }

      try {
        // 3) ĐANG CHẤM ĐIỂM
        setPhase("evaluating");

        const res = await fetch(`${API_URL}/mock/export?session_id=${sid}`, {
          method: "POST",
        });

        if (!res.ok) {
          const text = await res.text().catch(() => "");
          throw new Error(`export failed: ${res.status} ${text}`);
        }

        const data = await res.json().catch(() => ({}));
        console.log("AUTO EVAL:", data?.auto_eval);

        // 4) THÔNG BÁO "XONG RỒI" TRƯỚC KHI BẬT BẢNG
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            type: "bot",
            message: "Summary complete. Here are your results.",
            timestamp: new Date(),
          },
        ]);

        setAutoEval(data?.auto_eval || null);

        // 5) CHỈ SHOW MODAL SAU KHI CÓ DATA
        setShowEval(true);
        setPhase("done");
      } catch (err) {
        console.error(err);
        setMessages((prev) => [
          ...prev,
          {
            id: prev.length + 1,
            type: "bot",
            message:
              "I couldn't generate the summary due to an error. Please try again.",
            timestamp: new Date(),
          },
        ]);
        setPhase("done");
      }
    })();
  }
}, [remainingSeconds, hasAutoSaved, sessionId, isRecording, stopRecording]);


  useEffect(() => {
    if (phase !== "running") return; // ✅
    if (transcript) {
      sendMessage(transcript);
    }
  }, [transcript]);

  useEffect(() => {
    if (messages.length === 1 && messages[0].type === "bot") {
      speak(messages[0].message);
    }
  }, [messages]);

  const sendMessage = async (messageText = inputMessage) => {
    if (phase !== "running") return;
    if (remainingSeconds <= 0 || isTimeUp) return;
    const text = messageText.trim();
    const sid = sessionId || localStorage.getItem("interview_session_id");
    if (!text || !sid) return;

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      message: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    try {
      const response = await fetch(`${API_URL}/mock/turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sid,
          user_answer: text,
        }),
      });

      if (!response.ok) {
        if (response.status === 400) {
          setMessages((prev) => [
            ...prev,
            {
              id: messages.length + 2,
              type: "bot",
              message: "Session not initialized. Redirecting to Upload...",
              timestamp: new Date(),
            },
          ]);
          setTimeout(() => navigate("/upload?mode=mock"), 800);
          return;
        }
        if (response.status === 401) {
          const errorMessage = {
            id: messages.length + 2,
            type: "bot",
            message: "Your session has expired. Please sign in again.",
            timestamp: new Date(),
          };
          setMessages((prev) => [...prev, errorMessage]);
          setTimeout(() => navigate("/signin"), 2000);
          return;
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Network response was not ok");
      }

      const data = await response.json();
      const metaMessage = {
        id: messages.length + 2,
        type: "meta",
        message: `Summary: ${data.reasoning_summary}`,
        timestamp: new Date(),
      };
      const botMessage = {
        id: messages.length + 3,
        type: "bot",
        message: data.next_question,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, metaMessage, botMessage]);

      if (/\?\s*$/.test(data?.next_question || "")) {
        setQuestionCount((q) => q + 1);
      }

      speak(data.next_question);
    } catch (error) {
      console.error("There was a problem with the fetch operation:", error);
      const errorMessage = {
        id: messages.length + 2,
        type: "bot",
        message:
          "Sorry, I'm having trouble connecting to my brain right now. Please try again later.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
      speak(
        "Sorry, I'm having trouble connecting to my brain right now. Please try again later."
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const toggleRecording = () => {
    if (phase !== "running") return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const handleMouseDown = (e) => {
    isResizing.current = true;
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
  };

  const handleMouseMove = (e) => {
    if (isResizing.current) {
      const newWidth = window.innerWidth - e.clientX;
      if (newWidth > 300 && newWidth < window.innerWidth * 0.7) {
        setChatPanelWidth(newWidth);
      }
    }
  };

  const handleMouseUp = () => {
    isResizing.current = false;
    document.removeEventListener("mousemove", handleMouseMove);
    document.removeEventListener("mouseup", handleMouseUp);
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", height: "100vh", position: "relative" }}>
      <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
        <CharacterPanel
          remainingSeconds={remainingSeconds}
          questionCount={questionCount}
          onHome={handleHome}
        />
      </div>
      <Resizer onMouseDown={handleMouseDown} />
      <div style={{ width: `${chatPanelWidth}px`, flexShrink: 0 }}>
        <ChatPanel
          messages={messages}
          inputMessage={inputMessage}
          setInputMessage={setInputMessage}
          isTyping={isTyping}
          isRecording={isRecording}
          handleKeyPress={handleKeyPress}
          sendMessage={sendMessage}
          toggleRecording={toggleRecording}
          formatTime={formatTime}
          disabled={phase !== "running"} 
        />
      </div>

      {/* Modal Overlay - Hiển thị toàn màn hình */}
      {showEval && autoEval && (
        <div 
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "1rem"
          }}
        >
          {/* Lớp nền mờ */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: "rgba(0, 0, 0, 0.75)",
              backdropFilter: "blur(8px)"
            }}
            onClick={() => setShowEval(false)}
          />

          {/* Card kết quả */}
          <div
            style={{
              position: "relative",
              width: "100%",
              maxWidth: "48rem",
              maxHeight: "90vh",
              overflowY: "auto"
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <InterviewResultCard 
              autoEval={autoEval} 
              onClose={() => setShowEval(false)} 
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default MockInterview;