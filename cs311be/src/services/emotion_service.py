import cv2
import numpy as np
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Set

from deepface import DeepFace

emotion_labels = ['angry','disgust','fear','happy','sad','surprise','neutral']


class EmotionService:
    def __init__(self, cam_index: int = 0, fps: float = 6.0, log_interval_sec: int = 10):
        emo = DeepFace.build_model("Emotion", "facial_attribute")
        inner_model = getattr(emo, "model", None)
        if inner_model is None:
            raise RuntimeError("Không tìm thấy inner Keras model")

        self.model = inner_model
        self.model_lock = threading.Lock()

        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        self.cam_index = cam_index
        self.fps = fps
        self.log_interval_sec = log_interval_sec

        self._stop_cam = threading.Event()
        self._cam_thread: Optional[threading.Thread] = None

        self.latest: Optional[Dict[str, Any]] = None

        self._logging_sessions: Set[str] = set()
        self._log_thread: Optional[threading.Thread] = None
        self._stop_log = threading.Event()

        self._lock = threading.Lock()

    # ---------- camera ----------
    def start_camera(self):
        if self._cam_thread is not None and self._cam_thread.is_alive():
            print("[emotion] camera thread already running")
            return
        print("[emotion] starting camera thread...")
        self._stop_cam.clear()
        self._cam_thread = threading.Thread(target=self._cam_loop, daemon=True)
        self._cam_thread.start()

    def stop_camera(self):
        print("[emotion] stopping camera thread...")
        self._stop_cam.set()

        t = self._cam_thread
        if t is None:
            return
        if not t.is_alive():
            return
        t.join(timeout=2)

    # ---------- logging ----------
    def start_logging(self, session_id: str):
        with self._lock:
            self._logging_sessions.add(session_id)

        print(f"[emotion] start_logging session={session_id} active={len(self._logging_sessions)}")

        # đảm bảo camera chạy
        self.start_camera()

        # ghi ngay 1 dòng để chắc chắn có file

        # đảm bảo log thread chạy
        if not (self._log_thread and self._log_thread.is_alive()):
            print("[emotion] starting log thread...")
            self._stop_log.clear()
            self._log_thread = threading.Thread(target=self._log_loop, daemon=True)
            self._log_thread.start()

    def stop_logging(self, session_id: str):
        with self._lock:
            self._logging_sessions.discard(session_id)
            empty = (len(self._logging_sessions) == 0)

        print(f"[emotion] stop_logging session={session_id} remaining={len(self._logging_sessions)}")

        # ghi 1 dòng cuối

        if empty:
            print("[emotion] no active sessions -> stopping log + camera")
            self._stop_log.set()
            self.stop_camera()
    def _append_line(self, session_id: str, note: str = ""):
        try:
            Path("exports").mkdir(exist_ok=True)

            safe_sid = "".join(ch for ch in session_id if ch.isalnum() or ch in ("-", "_"))
            fp = Path("exports") / f"emotion_{safe_sid}.txt"

            payload = self.latest or {"ok": False, "emotion": None, "ts": time.time()}
            emo = payload.get("emotion")
            ts = datetime.utcnow().isoformat() + "Z"

            line = f"{ts}\temotion={emo}\t{note}\n"
            with fp.open("a", encoding="utf-8") as f:
                f.write(line)

            # debug
            # print(f"[emotion] appended -> {fp} : {line.strip()}")
        except Exception as e:
            print("[emotion] append_line error:", e)

    def _log_loop(self):
        print("[emotion] log loop started")
        while not self._stop_log.is_set():
            time.sleep(self.log_interval_sec)

            with self._lock:
                session_ids = list(self._logging_sessions)

            if not session_ids:
                continue

            payload = self.latest or {"ok": False, "emotion": None, "ts": time.time()}
            emo = payload.get("emotion")
            ts = datetime.utcnow().isoformat() + "Z"

            for sid in session_ids:
                self._append_line(sid)

            print(f"[emotion] logged {len(session_ids)} session(s) @ {ts} emotion={emo}")

        print("[emotion] log loop stopped")

    # ---------- prediction ----------
    def _predict_emotion_from_bgr(self, face_bgr: np.ndarray):
        g = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2GRAY)
        g = cv2.resize(g, (48, 48), interpolation=cv2.INTER_AREA)
        g = g.astype("float32") / 255.0
        g = g.reshape(1, 48, 48, 1)

        with self.model_lock:
            probs = self.model.predict(g, verbose=0)[0]

        idx = int(np.argmax(probs))
        return emotion_labels[idx], probs.tolist()

    def _cam_loop(self):
        print(f"[emotion] _cam_loop entered, opening camera index={self.cam_index}")

        # Windows: dùng DirectShow cho ổn định
        cap = cv2.VideoCapture(self.cam_index, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            print("[emotion] FAILED to open camera")
            self.latest = {"ok": False, "error": "Cannot open camera", "ts": time.time()}
            return

        print("[emotion] camera opened OK")

        min_interval = 1.0 / max(self.fps, 1.0)
        last = 0.0

        fail_reads = 0

        while not self._stop_cam.is_set():
            ok, frame = cap.read()
            if not ok:
                fail_reads += 1
                if fail_reads % 30 == 0:
                    print("[emotion] WARN: failed to read frame", fail_reads)
                time.sleep(0.05)
                continue
            fail_reads = 0

            now = time.time()
            if now - last < min_interval:
                continue
            last = now

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))

            label = None
            probs = None

            if len(faces) > 0:
                x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
                if w >= 20 and h >= 20:
                    face_bgr = frame[y:y+h, x:x+w]
                    try:
                        label, probs = self._predict_emotion_from_bgr(face_bgr)
                    except Exception as e:
                        print("[emotion] predict error:", e)
                        label, probs = None, None

            self.latest = {"ok": True, "ts": now, "emotion": label, "probs": probs}

        cap.release()
        print("[emotion] camera released")
