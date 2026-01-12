import { useState } from "react";
import {
  MessageSquarePlus,
  MessageSquare,
  Trash2,
  ChevronLeft,
  ChevronRight,
  MoreHorizontal,
} from "lucide-react";

const ChatSidebar = ({
  chatSessions,
  currentSessionId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  isCollapsed,
  onToggleCollapse,
}) => {
  const [hoveredSession, setHoveredSession] = useState(null);
  const [menuOpenSession, setMenuOpenSession] = useState(null);

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  const getSessionTitle = (session) => {
    if (session.title) return session.title;
    // Get first user message as title
    const firstUserMessage = session.messages?.find((m) => m.type === "user");
    if (firstUserMessage) {
      return firstUserMessage.message.slice(0, 30) + (firstUserMessage.message.length > 30 ? "..." : "");
    }
    return "New Interview";
  };

  if (isCollapsed) {
    return (
      <div
        style={{
          width: "48px",
          height: "100vh",
          background: "#1a1a2e",
          borderRight: "1px solid #2d2d44",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          paddingTop: "12px",
          gap: "8px",
        }}
      >
        <button
          onClick={onToggleCollapse}
          style={{
            width: "36px",
            height: "36px",
            background: "transparent",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#9ca3af",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.target.style.background = "#2d2d44";
            e.target.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            e.target.style.background = "transparent";
            e.target.style.color = "#9ca3af";
          }}
          title="Expand sidebar"
        >
          <ChevronRight size={20} />
        </button>
        <button
          onClick={onNewChat}
          style={{
            width: "36px",
            height: "36px",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            transition: "all 0.2s",
          }}
          title="New Chat"
        >
          <MessageSquarePlus size={18} />
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        width: "260px",
        height: "100vh",
        background: "#1a1a2e",
        borderRight: "1px solid #2d2d44",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "12px",
          borderBottom: "1px solid #2d2d44",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <button
          onClick={onNewChat}
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: "10px",
            padding: "10px 14px",
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            border: "none",
            borderRadius: "8px",
            color: "#fff",
            fontWeight: "600",
            fontSize: "0.875rem",
            cursor: "pointer",
            transition: "all 0.2s",
          }}
        >
          <MessageSquarePlus size={18} />
          New Interview
        </button>
        <button
          onClick={onToggleCollapse}
          style={{
            width: "36px",
            height: "36px",
            marginLeft: "8px",
            background: "transparent",
            border: "none",
            borderRadius: "8px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#9ca3af",
            transition: "all 0.2s",
          }}
          onMouseEnter={(e) => {
            e.target.style.background = "#2d2d44";
            e.target.style.color = "#fff";
          }}
          onMouseLeave={(e) => {
            e.target.style.background = "transparent";
            e.target.style.color = "#9ca3af";
          }}
          title="Collapse sidebar"
        >
          <ChevronLeft size={20} />
        </button>
      </div>

      {/* Chat List */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px",
        }}
      >
        {chatSessions.length === 0 ? (
          <div
            style={{
              padding: "20px",
              textAlign: "center",
              color: "#6b7280",
              fontSize: "0.875rem",
            }}
          >
            No chat history yet.
            <br />
            Start a new interview!
          </div>
        ) : (
          <>
            {/* Group by date */}
            {Object.entries(
              chatSessions.reduce((groups, session) => {
                const dateKey = formatDate(session.createdAt);
                if (!groups[dateKey]) groups[dateKey] = [];
                groups[dateKey].push(session);
                return groups;
              }, {})
            ).map(([dateGroup, sessions]) => (
              <div key={dateGroup} style={{ marginBottom: "16px" }}>
                <div
                  style={{
                    padding: "8px 12px",
                    fontSize: "0.75rem",
                    fontWeight: "600",
                    color: "#6b7280",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  {dateGroup}
                </div>
                {sessions.map((session) => (
                  <div
                    key={session.id}
                    style={{
                      position: "relative",
                      marginBottom: "2px",
                    }}
                    onMouseEnter={() => setHoveredSession(session.id)}
                    onMouseLeave={() => {
                      setHoveredSession(null);
                      if (menuOpenSession === session.id) {
                        setMenuOpenSession(null);
                      }
                    }}
                  >
                    <button
                      onClick={() => onSelectChat(session.id)}
                      style={{
                        width: "100%",
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        padding: "10px 12px",
                        background:
                          currentSessionId === session.id
                            ? "#2d2d44"
                            : hoveredSession === session.id
                            ? "#252538"
                            : "transparent",
                        border: "none",
                        borderRadius: "8px",
                        color:
                          currentSessionId === session.id ? "#fff" : "#d1d5db",
                        fontSize: "0.875rem",
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "all 0.15s",
                      }}
                    >
                      <MessageSquare
                        size={16}
                        style={{ flexShrink: 0, opacity: 0.7 }}
                      />
                      <span
                        style={{
                          flex: 1,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {getSessionTitle(session)}
                      </span>
                      {(hoveredSession === session.id ||
                        menuOpenSession === session.id) && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setMenuOpenSession(
                              menuOpenSession === session.id
                                ? null
                                : session.id
                            );
                          }}
                          style={{
                            background: "transparent",
                            border: "none",
                            padding: "4px",
                            cursor: "pointer",
                            color: "#9ca3af",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            borderRadius: "4px",
                          }}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                      )}
                    </button>

                    {/* Dropdown Menu */}
                    {menuOpenSession === session.id && (
                      <div
                        style={{
                          position: "absolute",
                          right: "8px",
                          top: "100%",
                          background: "#2d2d44",
                          borderRadius: "8px",
                          boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                          zIndex: 100,
                          overflow: "hidden",
                          minWidth: "140px",
                        }}
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteChat(session.id);
                            setMenuOpenSession(null);
                          }}
                          style={{
                            width: "100%",
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            padding: "10px 14px",
                            background: "transparent",
                            border: "none",
                            color: "#ef4444",
                            fontSize: "0.875rem",
                            cursor: "pointer",
                            textAlign: "left",
                            transition: "background 0.15s",
                          }}
                          onMouseEnter={(e) =>
                            (e.target.style.background = "#3d3d54")
                          }
                          onMouseLeave={(e) =>
                            (e.target.style.background = "transparent")
                          }
                        >
                          <Trash2 size={16} />
                          Delete
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </>
        )}
      </div>

      {/* Footer */}
      <div
        style={{
          padding: "12px",
          borderTop: "1px solid #2d2d44",
          fontSize: "0.75rem",
          color: "#6b7280",
          textAlign: "center",
        }}
      >
        {chatSessions.length} conversation{chatSessions.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
};

export default ChatSidebar;

