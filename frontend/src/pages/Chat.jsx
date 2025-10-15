import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { motion } from "framer-motion";
import { FaPaperPlane, FaRobot, FaUser } from "react-icons/fa";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    const formData = new FormData();
    formData.append("query", input);

    try {
      const res = await axios.post(`${import.meta.env.VITE_BACKEND_URL}/api/chat/`, formData);
      const botMessage = { sender: "bot", text: res.data.answer };
      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      alert("❌ Failed to reach backend");
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
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-6"
      >
        <h1 className="text-3xl sm:text-4xl font-bold mb-3 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-pink-500">
          🧠 AI Assistant
        </h1>
        <p className="text-gray-400 text-sm sm:text-base">
          Ask questions or troubleshoot based on your machine shop notes.
        </p>
      </motion.div>

      {/* Chat Card */}
      <motion.div
  initial={{ opacity: 0, scale: 0.95 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.5 }}
  className="flex flex-col w-full max-w-md flex-grow backdrop-blur-xl bg-white/10 p-4 sm:p-6 rounded-3xl shadow-2xl border border-white/20 h-[85vh] sm:h-[80vh]"
>
  {/* Messages Area */}
  <div className="flex-1 overflow-y-auto pr-1 space-y-3 scrollbar-thin scrollbar-thumb-gray-700 min-h-0">
    {messages.map((msg, idx) => (
      <div key={idx} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
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
    ))}
    <div ref={messagesEndRef} />
  </div>

  {/* Input Section */}
  <div className="mt-3 flex items-center gap-2">
    <input
      className="flex-1 p-3 rounded-xl bg-gray-900/40 border border-gray-600 
                 text-gray-100 placeholder-gray-400 focus:outline-none 
                 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all"
      value={input}
      onChange={(e) => setInput(e.target.value)}
      placeholder="Type your question..."
      onKeyDown={(e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          handleAsk();
        }
      }}
    />
    <button
      onClick={handleAsk}
      className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-3 rounded-xl 
                 hover:shadow-blue-500/30 transition-all flex items-center justify-center"
    >
      <FaPaperPlane className="text-lg" />
    </button>
  </div>
</motion.div>
      {/* Footer */}
      <p className="text-gray-500 text-xs mt-8 text-center">
        Powered by your notes and AI ⚙️
      </p>
    </div>
  );
}