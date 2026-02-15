import React, { useState, useEffect } from "react";
import axios from "axios";
import { motion } from "framer-motion";
import { FaMicrophoneAlt, FaSave, FaRedoAlt } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

export default function RecordPage( {token} ) {
  const [isRecording, setIsRecording] = useState(false);
  const [transcribedText, setTranscribedText] = useState("");
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [noteId, setNoteId] = useState(1);
  const [isProcessing, setIsProcessing] = useState(false);
  const [machines, setMachines] = useState([]);
  const [selectedMachine, setSelectedMachine] = useState("");
  const navigate = useNavigate();
  const getAuthHeaders = () => ({
    Authorization: `Bearer ${token || localStorage.getItem('access_token')}`,
  });

  useEffect(() => {
    const fetchMachines = async () => {
      try {
        const res = await axios.get(
          `${import.meta.env.VITE_BACKEND_URL}/api/machines/`,
          { headers: getAuthHeaders() }
        );
        setMachines(res.data.machines || []);
      } catch (err) {
        console.error("Failed to fetch machines:", err);
      }
    };
    fetchMachines();
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Pick MIME type based on browser support
      let mimeType = "";
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        mimeType = "audio/webm;codecs=opus";
      } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        mimeType = "audio/webm";
      } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
        mimeType = "audio/mp4";
      } else if (MediaRecorder.isTypeSupported("audio/mpeg")) {
        mimeType = "audio/mpeg";
      } else {
        alert("❌ Your browser does not support audio recording.");
        return;
      }

      console.log("🎙️ Using MIME type:", mimeType);

      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          console.log("📦 Chunk received:", e.data.size, "bytes");
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        console.log("⏹️ Recording stopped, total chunks:", chunks.length);
        
        const blob = new Blob(chunks, { type: mimeType });
        console.log("📁 Final blob size:", blob.size, "bytes");

        if (blob.size === 0) {
          alert("⚠️ No audio captured. Please try recording again.");
          return;
        }

        // Pick correct filename extension
        const filename = mimeType.includes("mp4")
          ? "recording.mp4"
          : mimeType.includes("mpeg")
          ? "recording.mp3"
          : "recording.webm";

        const formData = new FormData();
        formData.append("file", blob, filename);

        setIsProcessing(true);

        try {
          console.log("🚀 Sending to backend:", filename, blob.size, "bytes");
          
          const res = await axios.post(
            `${import.meta.env.VITE_BACKEND_URL}/api/transcribe/`,
            formData,
            { 
              headers: { "Content-Type": "multipart/form-data",
                          ...getAuthHeaders()
              },
              timeout: 30000 // 30 second timeout
            }
          );

          console.log("✅ Transcription response:", res.data);

          if (res.data.error) {
            alert(`⚠️ ${res.data.error}`);
          } else if (res.data.text) {
            setTranscribedText(res.data.text);
          } else {
            alert("⚠️ No text returned from transcription");
          }

        } catch (err) {
          console.error("❌ Transcription error:", err);
          
          let errorMsg = "Failed to transcribe audio";
          
          if (err.response?.staus === 401) {
            localStorage.removeItem('access_token');
            window.location.reload();
            alert("❌ Session expired. Please log in again.");
            return;
          }
          if (err.response) {
            // Server responded with error
            errorMsg = err.response.data?.detail || err.response.data?.error || errorMsg;
            console.error("Server error:", err.response.status, err.response.data);
          } else if (err.request) {
            // Request made but no response
            errorMsg = "No response from server. Check if backend is running.";
            console.error("No response:", err.request);
          } else {
            // Error setting up request
            errorMsg = err.message;
            console.error("Request error:", err.message);
          }
          
          alert(`❌ ${errorMsg}`);
        } finally {
          setIsProcessing(false);
          
          // Stop all tracks to release microphone
          stream.getTracks().forEach(track => track.stop());
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      
      console.log("🎙️ Recording started");
      
    } catch (err) {
      console.error("🎤 Microphone error:", err);
      alert("🎤 Microphone access denied or not supported. Please check your browser permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
      console.log("⏹️ Stopping recording...");
    }
  };

  const handleSave = async () => {
    if (!transcribedText.trim()) {
      alert("No text to save");
      return;
    }
    if (!selectedMachine) {
      alert("Please select a machine first");
      return;
    }

    try {
      const formData = new FormData();
      formData.append("text", String(transcribedText));
      formData.append("machine_id", selectedMachine);

      await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/save_note/`,
        formData,
        { headers: getAuthHeaders() });
      alert("Note saved successfully!");

      setTranscribedText("");
      setNoteId((prev) => prev + 1);
    } catch (error) {
      console.error("Error saving note:", error);
      if (error.response?.status === 401) {
        localStorage.removeItem('access_token');
        window.location.reload();
        alert("❌ Session expired. Please log in again.");
        return;
      }
      alert("❌ Failed to save note: " + (error.response?.data?.detail || error.message));
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

      {/* Machine Selector */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="w-full max-w-md mb-4"
      >
        <select
          value={selectedMachine}
          onChange={(e) => setSelectedMachine(e.target.value)}
          className="w-full p-3 rounded-xl bg-gray-900/60 border border-gray-600 text-gray-100
                     focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all"
        >
          <option value="">Select a machine...</option>
          {machines.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}{m.description ? ` — ${m.description}` : ""}
            </option>
          ))}
        </select>
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
          disabled={isProcessing}
          className={`w-full py-3 rounded-xl font-medium text-lg flex items-center justify-center gap-2 shadow-md transition-all 
            ${isProcessing
              ? "bg-gray-500 cursor-not-allowed"
              : isRecording
              ? "bg-red-500 hover:bg-red-600 shadow-red-500/30"
              : "bg-blue-500 hover:bg-blue-600 shadow-blue-500/30"
            }`}
        >
          <FaMicrophoneAlt className="text-xl" />
          {isProcessing ? "⏳ Processing..." : isRecording ? "⏹ Stop Recording" : "Start Recording"}
        </button>

        {/* Textbox */}
        <textarea
          rows="7"
          value={transcribedText}
          onChange={(e) => setTranscribedText(e.target.value)}
          placeholder="Type or record your note here..."
          disabled={isProcessing}
          className="w-full mt-5 p-3 rounded-xl border border-gray-500/30 bg-gray-900/40 
                     text-gray-100 placeholder-gray-400 resize-none focus:outline-none 
                     focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all
                     disabled:opacity-50"
        ></textarea>

        <div className="flex flex-col sm:flex-row justify-between gap-3 mt-5">
          <button
            onClick={handleSave}
            disabled={isProcessing}
            className="flex-1 flex items-center justify-center gap-2 bg-green-500 hover:bg-green-600 text-white py-2.5 rounded-xl shadow-md transition-all shadow-green-500/30 disabled:opacity-50"
          >
            <FaSave className="text-lg" /> Save Note
          </button>

          <button
            onClick={handleRecordMore}
            disabled={isProcessing}
            className="flex-1 flex items-center justify-center gap-2 bg-orange-500 hover:bg-orange-600 text-white py-2.5 rounded-xl shadow-md transition-all shadow-orange-500/30 disabled:opacity-50"
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