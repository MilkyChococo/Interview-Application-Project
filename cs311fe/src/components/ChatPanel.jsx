import React, { useRef, useEffect } from 'react';
import { Send, Mic, MicOff, Bot, User, Play, FileText } from 'lucide-react';

const ChatPanel = ({
  messages,
  inputMessage,
  setInputMessage,
  isTyping,
  isRecording,
  handleKeyPress,
  sendMessage,
  toggleRecording,
  formatTime,
  disabled = false, 
  phase = "running",
  recordingSeconds = 0,
  onStartInterview,
  onViewReport
}) => {
  // Helper to check if message contains interview plan keywords
  const hasInterviewPlan = (message) => {
    const keywords = ['kế hoạch phỏng vấn', 'interview plan', 'let\'s begin', 'hãy bắt đầu', 'ready to start'];
    return keywords.some(keyword => message.toLowerCase().includes(keyword.toLowerCase()));
  };

  // Helper to check if message contains evaluation/final assessment keywords
  const hasEvaluation = (message) => {
    const keywords = ['ĐÁNH GIÁ', 'đánh giá cuối', 'final evaluation', 'final assessment', 'interview summary', 'overall score', 'tổng kết'];
    return keywords.some(keyword => message.toLowerCase().includes(keyword.toLowerCase()));
  };
  const messagesEndRef = useRef(null);
  const canSend = !disabled && inputMessage.trim();
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div style={{ 
      height: '100%',
      background: 'white',
      display: 'flex',
      flexDirection: 'column',
      boxShadow: '-4px 0 20px rgba(0, 0, 0, 0.1)' // Shadow on the left
    }}>
      {/* Chat Header */}
      <div style={{ 
        padding: '20px',
        borderBottom: '1px solid #e5e7eb',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        flexShrink: 0
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          background: 'rgba(255, 255, 255, 0.2)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}>
          <Bot size={24} color="white" />
        </div>
        <div>
          <div style={{ color: 'white', fontWeight: '600', fontSize: '16px' }}>
            AI Interviewer
          </div>
          <div style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '12px' }}>
            Online
          </div>
        </div>
      </div>
      {(phase === "saving" || phase === "evaluating") && (
    <div style={{
    margin: '16px 24px 0',
    padding: '10px 12px',
    borderRadius: '12px',
    background: '#fff7ed',
    border: '1px solid #fed7aa',
    color: '#9a3412',
    fontSize: '13px'
    }}>
    Generating your interview summary… Please wait.
    </div>
)}
      {/* Messages */}
      <div style={{ 
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        background: '#f9fafb'
      }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: msg.type === 'user' ? 'row-reverse' : 'row',
              marginBottom: '20px',
              animation: 'slideUp 0.3s ease-out'
            }}
          >
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: msg.type === 'user' 
                ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)'
                : 'linear-gradient(135deg, #10b981, #059669)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              {msg.type === 'user' ? (
                <User size={20} color="white" />
              ) : (
                <Bot size={20} color="white" />
              )}
            </div>
            <div style={{
              marginLeft: msg.type === 'user' ? 0 : '12px',
              marginRight: msg.type === 'user' ? '12px' : 0,
              maxWidth: 'calc(100% - 60px)'
            }}>
              <div style={{
                background: msg.type === 'user' 
                  ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)'
                  : 'white',
                color: msg.type === 'user' ? 'white' : '#111827',
                padding: '12px 16px',
                borderRadius: '12px',
                fontSize: '14px',
                lineHeight: '1.6',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)'
              }}>
                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.message}</div>
                
                {/* Start Interview Button */}
                {msg.type === 'bot' && hasInterviewPlan(msg.message) && onStartInterview && (
                  <button
                    onClick={onStartInterview}
                    style={{
                      marginTop: '12px',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      border: 'none',
                      cursor: 'pointer',
                      background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                      color: 'white',
                      fontWeight: '600',
                      fontSize: '13px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)',
                      transition: 'all 0.2s'
                    }}
                  >
                    <Play size={14} />
                    Start Interview
                  </button>
                )}
                
                {/* View Report Button */}
                {msg.type === 'bot' && hasEvaluation(msg.message) && onViewReport && (
                  <button
                    onClick={onViewReport}
                    style={{
                      marginTop: '12px',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      border: 'none',
                      cursor: 'pointer',
                      background: 'linear-gradient(135deg, #10b981, #059669)',
                      color: 'white',
                      fontWeight: '600',
                      fontSize: '13px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px',
                      boxShadow: '0 2px 8px rgba(16, 185, 129, 0.3)',
                      transition: 'all 0.2s'
                    }}
                  >
                    <FileText size={14} />
                    View Report
                  </button>
                )}
              </div>
              <div style={{
                fontSize: '11px',
                color: '#9ca3af',
                marginTop: '4px',
                textAlign: msg.type === 'user' ? 'right' : 'left'
              }}>
                {formatTime(msg.timestamp)}
              </div>
            </div>
          </div>
        ))}
        
        {isTyping && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #10b981, #059669)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Bot size={20} color="white" />
            </div>
            <div style={{
              background: 'white',
              padding: '12px 16px',
              borderRadius: '12px',
              display: 'flex',
              gap: '4px'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#9ca3af',
                animation: 'bounce 1.4s infinite'
              }}></div>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#9ca3af',
                animation: 'bounce 1.4s infinite 0.2s'
              }}></div>
              <div style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#9ca3af',
                animation: 'bounce 1.4s infinite 0.4s'
              }}></div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef}></div>
      </div>

      {/* Input Area */}
      <div style={{ 
        padding: '20px',
        borderTop: '1px solid #e5e7eb',
        background: 'white',
        flexShrink: 0
      }}>
        <div style={{
          display: 'flex',
          gap: '8px',
          alignItems: 'flex-end'
        }}>
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => { if (!disabled) toggleRecording(); }}
              disabled={disabled}
              style={{
                width: '44px',
                height: '44px',
                borderRadius: '50%',
                border: 'none',
                background: disabled
                  ? '#e5e7eb'
                  : (isRecording ? '#ef4444' : '#f3f4f6'),
                color: disabled
                  ? '#9ca3af'
                  : (isRecording ? 'white' : '#6b7280'),
                cursor: disabled ? 'not-allowed' : 'pointer',
                opacity: disabled ? 0.6 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                flexShrink: 0
              }}
              title={isRecording ? 'Stop recording' : 'Start voice recording'}
            >
              {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            {/* Recording Timer Badge */}
            {isRecording && recordingSeconds > 0 && (
              <span style={{
                position: 'absolute',
                top: '-8px',
                right: '-8px',
                background: '#ef4444',
                color: 'white',
                borderRadius: '999px',
                padding: '2px 6px',
                fontSize: '10px',
                fontWeight: '600',
                boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                minWidth: '20px',
                textAlign: 'center'
              }}>
                {recordingSeconds}s
              </span>
            )}
          </div>
          <div style={{
            flex: 1,
            position: 'relative'
          }}>
            <textarea
  value={inputMessage}
  onChange={(e) => { if (!disabled) setInputMessage(e.target.value); }}
  onKeyPress={(e) => { if (!disabled) handleKeyPress(e); }}
  disabled={disabled}
  placeholder={disabled ? "Interview finished. Generating summary..." : "Type your message..."}
  style={{
    width: '100%',
    minHeight: '44px',
    maxHeight: '120px',
    padding: '12px 16px',
    border: '1px solid #e5e7eb',
    borderRadius: '22px',
    fontSize: '14px',
    resize: 'none',
    fontFamily: 'inherit',
    lineHeight: '1.5',
    outline: 'none',
    transition: 'border-color 0.2s',
    background: disabled ? '#f9fafb' : 'white',
    color: disabled ? '#9ca3af' : '#111827',
    cursor: disabled ? 'not-allowed' : 'text',
    opacity: disabled ? 0.85 : 1,
  }}
/>

          </div>
          <button
  onClick={() => { if (canSend) sendMessage(); }}
  disabled={!canSend}
  style={{
    width: '44px',
    height: '44px',
    borderRadius: '50%',
    border: 'none',
    background: canSend
      ? 'linear-gradient(135deg, #3b82f6, #8b5cf6)'
      : '#e5e7eb',
    color: canSend ? 'white' : '#9ca3af',
    cursor: canSend ? 'pointer' : 'not-allowed',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s',
    flexShrink: 0,
    boxShadow: canSend ? '0 4px 12px rgba(59, 130, 246, 0.4)' : 'none',
    opacity: disabled ? 0.7 : 1,
  }}
>
  <Send size={20} />
</button>
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-10px); }
        }
      `}</style>
    </div>
  );
};

export default ChatPanel;
