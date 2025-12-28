import React from "react";
import Character3D from "./Character3D";
import BackgroundImage from "../image/bg.jpg";
import { Home } from "lucide-react";
import { useNavigate } from "react-router-dom";

const CharacterPanel = ({ remainingSeconds = 45 * 60, questionCount = 1, onHome}) => {
  const navigate = useNavigate();
  const mm = String(Math.floor(remainingSeconds / 60)).padStart(2, "0");
  const ss = String(remainingSeconds % 60).padStart(2, "0");

  return (
    <div
      style={{
        flex: 1,
        backgroundImage: `url(${BackgroundImage})`,
        backgroundSize: "cover",
        backgroundPosition: "center",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
        height: "100%",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "24px",
          background: "rgba(255, 255, 255, 0.1)",
          backdropFilter: "blur(10px)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 10,
        }}
      >
        <div>
          <h1
            style={{
              color: "white",
              fontSize: "28px",
              fontWeight: "700",
              marginBottom: "4px",
            }}
          >
            AI Interview Session
          </h1>
          <p style={{ color: "rgba(255, 255, 255, 0.9)", fontSize: "14px" }}>
            Practice makes perfect
          </p>
        </div>
        <button
          onClick={() => (onHome ? onHome() : navigate("/"))}
          style={{
            background: "rgba(255, 255, 255, 0.2)",
            border: "1px solid rgba(255, 255, 255, 0.3)",
            color: "white",
            padding: "10px 20px",
            borderRadius: "8px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
        >
          <Home size={18} />
          Home
        </button>
      </div>

      {/* 3D Character Canvas */}
      <div
        style={{
          width: "100%",
          height: "100%",
          position: "absolute",
          top: 0,
          left: 0,
          zIndex: 1,
        }}
      >
        <Character3D />
      </div>

      {/* Info card */}
      <div
        style={{
          padding: "24px",
          background: "rgba(255, 255, 255, 0.1)",
          backdropFilter: "blur(10px)",
          borderTop: "1px solid rgba(255, 255, 255, 0.2)",
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: "24px",
            justifyContent: "center",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: "32px",
                fontWeight: "700",
                color: "white",
                marginBottom: "4px",
              }}
            >
              {mm}:{ss}
            </div>
            <div
              style={{ fontSize: "14px", color: "rgba(255, 255, 255, 0.8)" }}
            >
              Interview Time
            </div>
          </div>
          <div
            style={{
              width: "1px",
              background: "rgba(255, 255, 255, 0.2)",
            }}
          ></div>
          <div style={{ textAlign: "center" }}>
            <div
              style={{
                fontSize: "32px",
                fontWeight: "700",
                color: "white",
                marginBottom: "4px",
              }}
            >
              {questionCount}
            </div>
            <div
              style={{ fontSize: "14px", color: "rgba(255, 255, 255, 0.8)" }}
            >
              Questions
            </div>
          </div>
          {/* Đã xóa Performance */}
        </div>
      </div>
    </div>
  );
};

export default CharacterPanel;
