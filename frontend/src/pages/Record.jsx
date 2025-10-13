import { useState } from "react";
import axios from "axios";

export default function RecordPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState("");
  const [recorder, setRecorder] = useState(null);
  const [chunks, setChunks] = useState([]);

  // ✅ Detect backend dynamically
  const backendURL = (() => {
  const { hostname, protocol } = window.location;
  const isLocal = hostname === "localhost" || hostname === "127.0.0.1";
  const isLan = /^192\.168\./.test(hostname) || /^10\./.test(hostname);

  if (isLocal || isLan) {
    return `https://${hostname}:8000`;   // ✅ use HTTPS now
  }
  return `${protocol}//${hostname}`;
})();

  // ✅ Start recording
  const startRecording = async () => {
    console.log("🎤 Start Recording clicked");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log("✅ Microphone permission granted");

      // choose mimeType supported by browser
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : "audio/mp4";

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      const localChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) localChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        console.log("🛑 Recording stopped, sending to backend...");
        const blob = new Blob(localChunks, { type: mimeType });
        const formData = new FormData();
        formData.append("file", blob, mimeType === "audio/mp4" ? "recording.mp4" : "recording.webm");

        try {
          const res = await axios.post(`${backendURL}/api/transcribe/`, formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          setTranscribedText(res.data.text || "(No speech detected)");
        } catch (err) {
          console.error("❌ Transcription error:", err);
          alert("Failed to reach backend — check console or CORS.");
        }
      };

      mediaRecorder.start();
      setRecorder(mediaRecorder);
      setChunks(localChunks);
      setIsRecording(true);
      console.log("🎙️ Recording started...");
    } catch (err) {
      console.error("🚫 Microphone error:", err);
      alert("Please allow microphone access or use HTTPS / localhost.");
    }
  };

  // ✅ Stop recording
  const stopRecording = () => {
    if (recorder) {
      recorder.stop();
      recorder.stream.getTracks().forEach((t) => t.stop());
      setIsRecording(false);
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "80px" }}>
      <h1>🎙️ Record Your Note</h1>

      <button onClick={isRecording ? stopRecording : startRecording}>
        {isRecording ? "⏹ Stop Recording" : "🎤 Start Recording"}
      </button>

      <div style={{ marginTop: "30px" }}>
        <textarea
          rows="8"
          cols="50"
          value={transcribedText}
          placeholder="Your transcribed note will appear here..."
          onChange={(e) => setTranscribedText(e.target.value)}
        />
      </div>
    </div>
  );
}