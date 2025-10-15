import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import HomePage from "./pages/Home";
import RecordPage from "./pages/Record";
import ChatPage from "./pages/Chat";


<div className="bg-red-500 text-white p-4 text-center">
  ✅ Tailwind is working
</div>

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/record" element={<RecordPage />} />
        <Route path="/chat" element={<ChatPage />} />
      </Routes>
    </Router>
  );
}

export default App;