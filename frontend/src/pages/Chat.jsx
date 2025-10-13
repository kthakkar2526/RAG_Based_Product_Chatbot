import { useNavigate } from "react-router-dom";

export default function ChatPage() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h1>💬 Chat with Notes</h1>
      <p>Chatbot integration coming soon...</p>
      <button onClick={() => navigate("/")}>⬅️ Back to Home</button>
    </div>
  );
}