import React, { useState } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { FaMicrophoneAlt, FaSave, FaRedoAlt } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

export default function RecordPage() {
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState("");
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [noteId, setNoteId] = useState(1);
  const navigate = useNavigate();

  const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // ✅ Step 1: Dynamically pick MIME type
    let mimeType = "";
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      mimeType = "audio/webm;codecs=opus"; // Chrome, Edge, Firefox
    } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
      mimeType = "audio/mp4"; // Safari / iPhone fallback
    } else if (MediaRecorder.isTypeSupported("audio/mpeg")) {
      mimeType = "audio/mpeg"; // Some Android browsers
    } else {
      alert("Your browser does not support audio recording.");
      return;
    }

    const recorder = new MediaRecorder(stream, { mimeType });
    const chunks = [];

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunks.push(e.data);
    };

    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: mimeType });
      if (blob.size === 0) {
        alert("⚠️ No audio captured. Try recording again.");
        return;
      }

      // ✅ Pick correct filename extension for backend
      const filename = mimeType.includes("mp4")
        ? "recording.mp4"
        : mimeType.includes("mpeg")
        ? "recording.mp3"
        : "recording.webm";

      const formData = new FormData();
      formData.append("file", blob, filename);

      try {
        const res = await axios.post(
          `${import.meta.env.VITE_BACKEND_URL}/api/transcribe/`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        );
        setTranscribedText(res.data.text);
      } catch (err) {
        console.error("Transcription error:", err);
        alert("❌ Failed to transcribe audio");
      }
    };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  } catch (err) {
    alert("🎤 Microphone access denied or not supported.");
    console.error(err);
  }
};

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleSave = async () => {
    if (!transcribedText.trim()) {
      alert("⚠️ No text to save");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("note_id", noteId);
      formData.append("text", transcribedText);

      await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/save_note/`, formData);
      alert("✅ Note saved successfully!");
    } catch (error) {
      console.error("Error saving note:", error);
      alert("❌ Failed to save note");
    }
  };

  const handleRecordMore = async () => {
    if (transcribedText.trim()) await handleSave();
    setNoteId((prev) => prev + 1);
    setTranscribedText("");
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br 
                 from-gray-900 via-gray-800 to-gray-900 text-white px-4 py-8 sm:px-6"
      style={{
        backgroundImage:
          "radial-gradient(circle at 10% 20%, rgba(0,150,255,0.15) 0%, transparent 50%), radial-gradient(circle at 90% 80%, rgba(255,255,255,0.05) 0%, transparent 50%)",
      }}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-6"
      >
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-pink-500">
          🎙️ Record Your Note
        </h1>
        <p className="text-gray-400 text-sm sm:text-base">
          Speak naturally — your note will be transcribed and saved automatically.
        </p>
      </motion.div>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="backdrop-blur-xl bg-white/10 p-6 sm:p-8 rounded-3xl shadow-2xl w-full max-w-md border border-white/20"
      >
        {/* Record Button */}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={`w-full py-3 rounded-xl font-medium text-lg flex items-center justify-center gap-2 shadow-md transition-all 
            ${isRecording
              ? "bg-red-500 hover:bg-red-600 shadow-red-500/30"
              : "bg-blue-500 hover:bg-blue-600 shadow-blue-500/30"}`}
        >
          <FaMicrophoneAlt className="text-xl" />
          {isRecording ? "⏹ Stop Recording" : "Start Recording"}
        </button>

        {/* Textbox */}
        <textarea
          rows="7"
          value={transcribedText}
          onChange={(e) => setTranscribedText(e.target.value)}
          placeholder="Type or record your note here..."
          className="w-full mt-5 p-3 rounded-xl border border-gray-500/30 bg-gray-900/40 
                     text-gray-100 placeholder-gray-400 resize-none focus:outline-none 
                     focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all"
        ></textarea>

        <div className="flex flex-col sm:flex-row justify-between gap-3 mt-5">
  <button
    onClick={handleSave}
    className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white py-2.5 rounded-xl shadow-md transition-all shadow-green-500/30"
  >
    <FaSave className="text-lg" /> Save Note
  </button>

  <button
    onClick={handleRecordMore}
    className="flex-1 flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white py-2.5 rounded-xl shadow-md transition-all shadow-orange-500/30"
  >
    <FaRedoAlt className="text-lg" /> Record More
  </button>

  <button
    onClick={() => navigate("/")}
    className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white py-2.5 rounded-xl shadow-md transition-all shadow-blue-500/30"
  >
    🏠 Home
  </button>
</div>
      </motion.div>

      {/* Footer */}
      <p className="text-gray-500 text-xs mt-10 text-center">
        Built for machinists, powered by AI ⚙️
      </p>
    </div>
  );
}