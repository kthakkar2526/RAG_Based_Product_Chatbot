import React from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { FaMicrophoneAlt, FaComments, FaRobot } from "react-icons/fa";

export default function Home() {
  const navigate = useNavigate();

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 text-white px-6"
      style={{
        backgroundImage:
          "radial-gradient(circle at 10% 20%, rgba(0,150,255,0.15) 0%, transparent 50%), radial-gradient(circle at 90% 80%, rgba(255,255,255,0.05) 0%, transparent 50%)",
      }}
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="flex flex-col items-center text-center mb-12"
      >
        <div className="flex flex-col items-center mb-6">
  <FaRobot className="text-6xl text-blue-400 drop-shadow-lg mb-3 animate-pulse" />
  <h1 className="text-4xl sm:text-5xl font-extrabold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400">
    Digital Assistant
  </h1>
</div>
        <p className="text-gray-300 max-w-xl text-base sm:text-lg">
          Your intelligent shop-floor companion — record and analyze machine
          notes or ask questions based on real data.
        </p>
      </motion.div>

      {/* Card with Buttons */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6 }}
        className="backdrop-blur-xl bg-white/10 p-8 sm:p-10 rounded-3xl shadow-2xl w-full max-w-md border border-white/20 text-center"
      >
        <div className="flex flex-col sm:flex-row justify-center gap-6">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/record")}
            className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-500 to-indigo-600 text-white px-6 py-3 rounded-xl font-medium text-base sm:text-lg shadow-lg hover:shadow-blue-500/30 transition-all w-full sm:w-auto"
          >
            <FaMicrophoneAlt className="text-lg sm:text-xl" />
            Record a Note
          </motion.button>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate("/chat")}
            className="flex items-center justify-center gap-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-3 rounded-xl font-medium text-base sm:text-lg shadow-lg hover:shadow-pink-500/30 transition-all w-full sm:w-auto"
          >
            <FaComments className="text-lg sm:text-xl" />
            Chat with Notes
          </motion.button>
        </div>
      </motion.div>

      {/* Footer */}
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 1, delay: 0.4 }}
        className="text-gray-500 text-sm mt-12 text-center"
      >
        Built for machinists, powered by AI ⚙️
      </motion.p>
    </div>
  );
}