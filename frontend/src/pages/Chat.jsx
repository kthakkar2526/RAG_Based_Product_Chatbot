import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { FaHome, FaPaperPlane, FaRobot, FaUser, FaMicrophone } from "react-icons/fa";
import { useNavigate } from "react-router-dom";

export default function ChatPage({ token }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [machines, setMachines] = useState([]);
  const [selectedMachine, setSelectedMachine] = useState(null);
  const messagesEndRef = useRef(null);
  const navigate = useNavigate();

  const getAuthHeaders = () => ({
    Authorization: `Bearer ${token || localStorage.getItem('access_token')}`,
  });

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    const fetchMachines = async () => {
      try {
        const res = await axios.get(
          `${import.meta.env.VITE_BACKEND_URL}/api/machines/`,
          { headers: getAuthHeaders() }
        );
        const machineList = res.data.machines || [];
        setMachines(machineList);

        // Show welcome message with machine selection
        if (machineList.length > 0) {
          setMessages([{
            sender: "bot",
            text: "Welcome! Which machine are you working with today?",
            type: "machine_select",
            machines: machineList,
          }]);
        }
      } catch (err) {
        console.error("Failed to fetch machines:", err);
      }
    };
    fetchMachines();
  }, []);

  const handleMachineSelect = (machine) => {
    setSelectedMachine(machine);
    // Add user's selection as a message
    setMessages((prev) => [
      ...prev,
      { sender: "user", text: machine.name },
      { sender: "bot", text: `Got it! I'm ready to help with the **${machine.name}**. Ask me anything about its operation, maintenance, or troubleshooting.` },
    ]);
  };

  const handleChangeMachine = () => {
    setSelectedMachine(null);
    setMessages([{
      sender: "bot",
      text: "Which machine would you like to switch to?",
      type: "machine_select",
      machines: machines,
    }]);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      let mimeType = "";
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        mimeType = "audio/webm;codecs=opus";
      } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        mimeType = "audio/webm";
      } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
        mimeType = "audio/mp4";
      } else {
        alert("No supported audio format found for recording.");
        return;
      }

      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.push(e.data);
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: mimeType });
        const filename = mimeType.includes("webm") ? "recording.webm" : "recording.mp4";
        const formData = new FormData();
        formData.append("file", blob, filename);

        try {
          const res = await axios.post(
            `${import.meta.env.VITE_BACKEND_URL}/api/transcribe/`,
            formData,
            { headers: {
              "Content-Type": "multipart/form-data",
              ...getAuthHeaders(),
            },
            timeout: 30000
          }
        );

        if (res.data.text){
          setInput(res.data.text);
        } else {
          alert("No text returned from transcription");
        }
    } catch(err) {
      console.error("Transcription error:", err);
      if (err.response?.status === 401) {
        localStorage.removeItem('access_token');
        window.location.reload();
        alert("Session expired. Please log in again.");
      } else {
        alert("Failed to transcribe audio");
      }
    } finally {
      stream.getTracks().forEach(track => track.stop())
    }
  };

    recorder.start();
    setMediaRecorder(recorder);
    setIsRecording(true);
  } catch (err) {
    console.error("Microphone error:", err);
    alert("Unable to access microphone");
  }
};

  const stopRecording = () => {
    if (mediaRecorder) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const handleAsk = async () => {
    if (!input.trim()) return;
    if (!selectedMachine) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    const queryText = input;
    setInput("");

    // Show typing indicator
    setMessages((prev) => [...prev, { sender: "bot", text: "...", type: "typing" }]);

    const formData = new FormData();
    formData.append("query", queryText);
    formData.append("machine_id", selectedMachine.id);

    try {
      const res = await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/chat/`,
        formData,
        { headers: getAuthHeaders() });

      // Build source citations
      let answerText = res.data.answer;
      const sources = res.data.sources || [];
      if (sources.length > 0) {
        answerText += "\n\n---\n**Sources:**\n";
        sources.forEach((s) => {
          if (s.source_type === "manual") {
            answerText += `- ${s.manual_title}, Page ${s.page_number || "?"}\n`;
          } else {
            answerText += `- Worker Note #${s.note_id} (${s.created_at || "N/A"})\n`;
          }
        });
      }

      // Remove typing indicator and add real response
      setMessages((prev) => [
        ...prev.filter((m) => m.type !== "typing"),
        { sender: "bot", text: answerText },
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => prev.filter((m) => m.type !== "typing"));
      if (err.response?.status === 401) {
        localStorage.removeItem('access_token');
        window.location.reload();
        alert("Session expired. Please log in again.");
      } else {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", text: "Sorry, I couldn't process that request. Please try again." },
        ]);
      }
    }
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
    <div className="fixed top-16 right-4 flex flex-col gap-2 z-50">
      <button onClick={() => navigate('/')}
        className="flex items-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white px-4 py-2 rounded-xl shadow-lg transition-all">
        <FaHome /> Home
      </button>
      {selectedMachine && (
        <button onClick={handleChangeMachine}
          className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-xl shadow-lg transition-all text-sm">
          Switch Machine
        </button>
      )}
    </div>
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-6 w-full max-w-md"
      >
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-pink-500">
          AI Assistant
        </h1>
        {selectedMachine && (
          <p className="text-blue-400 text-sm font-medium">
            Working with: {selectedMachine.name}
          </p>
        )}
        <p className="text-gray-400 text-sm sm:text-base mt-1">
          Ask questions or troubleshoot based on manuals and shop notes.
        </p>
      </motion.div>

      {/* Chat Card */}
      <motion.div
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.5 }}
  className="flex flex-col w-full max-w-md flex-grow backdrop-blur-xl bg-white/10 p-4 sm:p-6 rounded-3xl shadow-2xl border border-white/20 h-[75vh] sm:h-[70vh]"
>
  {/* Messages Area */}
  <div className="flex-1 overflow-y-auto pr-1 space-y-3 scrollbar-thin scrollbar-thumb-gray-700 min-h-0">
    {messages.map((msg, idx) => (
      <div key={idx}>
        {/* Machine selection buttons */}
        {msg.type === "machine_select" ? (
          <div className="flex justify-start">
            <div className="flex items-start gap-2 max-w-[85%]">
              <div className="flex-shrink-0 p-2 rounded-full bg-purple-500">
                <FaRobot className="text-white" />
              </div>
              <div className="space-y-2">
                <div className="p-3 rounded-2xl text-sm sm:text-base leading-relaxed shadow-md bg-gray-100 text-gray-900 rounded-bl-none">
                  {msg.text}
                </div>
                <div className="flex flex-wrap gap-2">
                  {msg.machines.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => handleMachineSelect(m)}
                      className="px-3 py-2 rounded-xl text-sm font-medium bg-gradient-to-r from-blue-500 to-indigo-600
                                 hover:from-blue-600 hover:to-indigo-700 text-white shadow-md transition-all
                                 hover:shadow-blue-500/30 active:scale-95"
                    >
                      {m.name}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : msg.type === "typing" ? (
          /* Typing indicator */
          <div className="flex justify-start">
            <div className="flex items-start gap-2 max-w-[85%]">
              <div className="flex-shrink-0 p-2 rounded-full bg-purple-500">
                <FaRobot className="text-white" />
              </div>
              <div className="p-3 rounded-2xl text-sm shadow-md bg-gray-100 text-gray-900 rounded-bl-none">
                <span className="animate-pulse">Thinking...</span>
              </div>
            </div>
          </div>
        ) : (
          /* Regular messages */
          <div className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`flex items-start gap-2 max-w-[85%] ${
                msg.sender === "user" ? "flex-row-reverse text-right" : ""
              }`}
            >
              <div
                className={`flex-shrink-0 p-2 rounded-full ${
                  msg.sender === "user" ? "bg-blue-500" : "bg-purple-500"
                }`}
              >
                {msg.sender === "user" ? (
                  <FaUser className="text-white" />
                ) : (
                  <FaRobot className="text-white" />
                )}
              </div>
              <div
                className={`p-3 rounded-2xl text-sm sm:text-base leading-relaxed shadow-md ${
                  msg.sender === "user"
                    ? "bg-blue-600 text-white rounded-br-none"
                    : "bg-gray-100 text-gray-900 rounded-bl-none"
                }`}
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
              </div>
            </div>
          </div>
        )}
      </div>
    ))}
    <div ref={messagesEndRef} />
  </div>

  {/* Input Section */}
  <div className="mt-3 flex items-center gap-2">
    <input
      className="flex-1 p-3 rounded-xl bg-gray-900/40 border border-gray-600
                 text-gray-100 placeholder-gray-400 focus:outline-none
                 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all
                 disabled:opacity-50"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      placeholder={selectedMachine ? `Ask about ${selectedMachine.name}...` : "Select a machine first..."}
      disabled={!selectedMachine}
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleAsk();
        }
      }}
    />
    <button
      onClick={isRecording ? stopRecording : startRecording}
      disabled={!selectedMachine}
      className={`p-3 rounded-xl transition-all flex items-center justify-center ${
        isRecording
          ? "bg-red-500 hover:bg-red-600 shadow-red-500/30 animate-pulse"
          : "bg-green-500 hover:bg-green-600 shadow-green-500/30"
      } text-white disabled:opacity-50 disabled:cursor-not-allowed`}
    >
      <FaMicrophone className="text-lg" />
    </button>
    <button
      onClick={handleAsk}
      disabled={!selectedMachine}
      className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-3 rounded-xl
                 hover:shadow-blue-500/30 transition-all flex items-center justify-center
                 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      <FaPaperPlane className="text-lg" />
    </button>
  </div>
</motion.div>
      {/* Footer */}
      <p className="text-gray-500 text-xs mt-8 text-center">
        Powered by your notes and AI
      </p>
    </div>
  );
}
