
import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  message: string;
};

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function checkBackend() {
      try {
        const response = await fetch("/api/health");

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const data: HealthResponse = await response.json();
        setHealth(data);
      } catch {
        setError("Could not connect to the backend.");
      }
    }

    checkBackend();
  }, []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>Wind Forecast Analytics</h1>
      <p>UK national wind generation dashboard</p>

      <h2>Backend connection</h2>

      {error ? (
        <p>{error}</p>
      ) : health ? (
        <div>
          <p>Status: {health.status}</p>
          <p>{health.message}</p>
        </div>
      ) : (
        <p>Connecting to backend...</p>
      )}
    </main>
  );
}

export default App;
