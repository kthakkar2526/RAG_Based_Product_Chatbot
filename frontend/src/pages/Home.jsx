import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h1>🤖 Digital Assistant</h1>
      <button onClick={() => navigate("/record")}>🎤 Record a Note</button>
      <br /><br />
      <button onClick={() => navigate("/chat")}>💬 Chat with Notes</button>
    </div>
  );
}