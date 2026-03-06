import { useState } from "react";
import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000/api"
});

export default function App() {
  const [token, setToken] = useState("");
  const [me, setMe] = useState(null);
  const [error, setError] = useState("");

  const fetchMe = async () => {
    setError("");
    try {
      const response = await api.get("/auth/me/", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMe(response.data);
    } catch (err) {
      setError("Не удалось получить пользователя. Проверьте токен.");
      setMe(null);
    }
  };

  return (
    <main className="container">
      <h1>Digital Installer</h1>
      <p>Этап 1: инфраструктура, JWT, RBAC.</p>

      <label htmlFor="token">JWT access token</label>
      <textarea
        id="token"
        value={token}
        onChange={(e) => setToken(e.target.value)}
        placeholder="Вставьте access токен"
      />
      <button onClick={fetchMe} type="button">
        Запросить /api/auth/me/
      </button>

      {error && <p className="error">{error}</p>}
      {me && <pre>{JSON.stringify(me, null, 2)}</pre>}
    </main>
  );
}
