import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import CharacterPanel from "../components/CharacterPanel";
import ChatPanel from "../components/ChatPanel";
import ChatSidebar from "../components/ChatSidebar";
import Resizer from "../components/Resizer";
import useVoiceRecognition from "../hooks/useVoiceRecognition";
import { v4 as uuidv4 } from "uuid";

const API_URL = "http://localhost:3005";

const DEFAULT_BOT_MESSAGE = {
  id: 1,
  type: "bot",
  message:
    "Hello! I'm your AI interviewer. I'll help you practice for your upcoming interview. Let's start with a simple question: Can you tell me about yourself?",
  timestamp: new Date(),
};

const Interview = () => {
  const { isAuthenticated, getAuthHeaders } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([DEFAULT_BOT_MESSAGE]);
  const [inputMessage, setInputMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [chatPanelWidth, setChatPanelWidth] = useState(480);
  const isResizing = useRef(false);
  const [sessionId, setSessionId] = useState(null);
  const location = useLocation();

  // Sidebar state
  const [chatSessions, setChatSessions] = useState([]);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Recording timer state
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const recordingTimerRef = useRef(null);

  // NEW: countdown + question counter
  const [remainingSeconds, setRemainingSeconds] = useState(45 * 60); // 45:00
  const [questionCount, setQuestionCount] = useState(1); // câu mở đầu đã là 1

  // NEW: timer đếm ngược mỗi giây
  useEffect(() => {
    if (remainingSeconds <= 0) return;
    const id = setInterval(
      () => setRemainingSeconds((s) => Math.max(0, s - 1)),
      1000
    );
    return () => clearInterval(id);
  }, [remainingSeconds]);

  useEffect(() => {
    // Check authentication
    if (!isAuthenticated) {
      navigate("/signin");
      return;
    }

    // Try to get sessionId from navigation state first
    const stateSessionId = location.state?.sessionId;

    // If not in state, try localStorage (from Upload page)
    const storedSessionId = localStorage.getItem("interview_session_id");

    // Use state sessionId first, then stored, then create new
    const finalSessionId = stateSessionId || storedSessionId || uuidv4();

    setSessionId(finalSessionId);
    console.log("Interview page sessionId:", finalSessionId);
    console.log("State sessionId:", stateSessionId);
    console.log("Stored sessionId:", storedSessionId);

    // Always save to localStorage for consistency
    localStorage.setItem("interview_session_id", finalSessionId);
  }, [location.state, isAuthenticated, navigate]);

  const { isRecording, transcript, startRecording, stopRecording, speak } =
    useVoiceRecognition();

  useEffect(() => {
    if (transcript) {
      sendMessage(transcript);
    }
  }, [transcript]);

  useEffect(() => {
    if (messages.length === 1 && messages[0].type === "bot") {
      speak(messages[0].message);
    }
  }, []);

  // Load chat sessions from localStorage on mount
  useEffect(() => {
    const savedSessions = localStorage.getItem("interview_chat_sessions");
    if (savedSessions) {
      try {
        const parsed = JSON.parse(savedSessions);
        setChatSessions(parsed);
      } catch (e) {
        console.error("Failed to parse saved sessions:", e);
      }
    }
  }, []);

  // Save current session to localStorage whenever messages change
  useEffect(() => {
    if (!sessionId || messages.length <= 1) return;

    setChatSessions((prevSessions) => {
      const existingIndex = prevSessions.findIndex((s) => s.id === sessionId);
      const updatedSession = {
        id: sessionId,
        messages: messages.map((m) => ({
          ...m,
          timestamp: m.timestamp instanceof Date ? m.timestamp.toISOString() : m.timestamp,
        })),
        createdAt: existingIndex >= 0 ? prevSessions[existingIndex].createdAt : new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      let newSessions;
      if (existingIndex >= 0) {
        newSessions = [...prevSessions];
        newSessions[existingIndex] = updatedSession;
      } else {
        newSessions = [updatedSession, ...prevSessions];
      }

      // Save to localStorage
      localStorage.setItem("interview_chat_sessions", JSON.stringify(newSessions));
      return newSessions;
    });
  }, [messages, sessionId]);

  // Handle creating a new chat
  const handleNewChat = useCallback(() => {
    const newSessionId = uuidv4();
    setSessionId(newSessionId);
    setMessages([{ ...DEFAULT_BOT_MESSAGE, timestamp: new Date() }]);
    setRemainingSeconds(45 * 60);
    setQuestionCount(1);
    localStorage.setItem("interview_session_id", newSessionId);
  }, []);

  // Handle selecting an existing chat
  const handleSelectChat = useCallback((selectedSessionId) => {
    const session = chatSessions.find((s) => s.id === selectedSessionId);
    if (session) {
      setSessionId(selectedSessionId);
      setMessages(
        session.messages.map((m) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }))
      );
      localStorage.setItem("interview_session_id", selectedSessionId);
    }
  }, [chatSessions]);

  // Handle deleting a chat
  const handleDeleteChat = useCallback((deleteSessionId) => {
    setChatSessions((prevSessions) => {
      const newSessions = prevSessions.filter((s) => s.id !== deleteSessionId);
      localStorage.setItem("interview_chat_sessions", JSON.stringify(newSessions));
      return newSessions;
    });

    // If deleting current session, create a new one
    if (deleteSessionId === sessionId) {
      handleNewChat();
    }
  }, [sessionId, handleNewChat]);

  const sendMessage = async (messageText = inputMessage) => {
    if (!messageText.trim() || !sessionId) return;

    const userMessage = {
      id: messages.length + 1,
      type: "user",
      message: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage("");
    setIsTyping(true);

    try {
      // Get auth headers
      const authHeaders = getAuthHeaders();

      const response = await fetch(`${API_URL}/chat/chatDomain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
        },
        body: JSON.stringify({
          room_id: sessionId,
          query: messageText,
        }),
      });

      if (!response.ok) {
        // Handle 401 Unauthorized
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
      const botMessage = {
        id: messages.length + 2,
        type: "bot",
        message: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botMessage]);

      // Tăng số câu hỏi nếu bot kết thúc bằng dấu hỏi
      if (/\?\s*$/.test(data?.response || "")) {
        setQuestionCount((q) => q + 1);
      }

      speak(data.response);
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
    if (isRecording) {
      stopRecording();
      // Stop recording timer
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      setRecordingSeconds(0);
    } else {
      startRecording();
      // Start recording timer
      setRecordingSeconds(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    }
  };

  // Cleanup recording timer on unmount
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, []);

  // Handle start interview button click
  const handleStartInterview = () => {
    sendMessage("Start");
  };

  // Handle view report button click
  const handleViewReport = () => {
    // Save session data to localStorage for EvaluationReport
    localStorage.setItem("evaluation_session_id", sessionId);
    // Navigate to evaluation report page
    navigate(`/evaluation-report?sessionId=${encodeURIComponent(sessionId)}`);
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
        // Min and Max width constraints
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
    <div style={{ minHeight: "100vh", display: "flex", height: "100vh" }}>
      {/* Chat History Sidebar */}
      <ChatSidebar
        chatSessions={chatSessions}
        currentSessionId={sessionId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      
      <div style={{ flex: 1, minWidth: 0, position: "relative" }}>
        <CharacterPanel showInfoBar={false} />
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
          recordingSeconds={recordingSeconds}
          onStartInterview={handleStartInterview}
          onViewReport={handleViewReport}
        />
      </div>
    </div>
  );
};

export default Interview;
