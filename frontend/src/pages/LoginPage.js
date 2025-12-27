import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../Services/api";

const LoginPage = () => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError("");

    const payload = {
      username: username.trim(),
      password,
    };

    if (token.trim()) {
      payload.token = token.trim();
    }

    try {
      const { data } = await API.post("login/", payload);
      localStorage.setItem("access_token", data.access);
      if (data.refresh) {
        localStorage.setItem("refresh_token", data.refresh);
      }

      navigate("/dashboard");
    } catch (err) {
      const message = err.response?.data?.error || "Login failed. Check your credentials and 2FA token.";
      setError(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 360, margin: "80px auto", textAlign: "center" }}>
      <h1>Sign in</h1>
      {error && (
        <p style={{ color: "#b00020", marginTop: 8 }} role="alert">
          {error}
        </p>
      )}
      <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 24 }}>
        <input
          autoComplete="username"
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="password"
          autoComplete="current-password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <input
          placeholder="2FA token (if enabled)"
          value={token}
          onChange={(e) => setToken(e.target.value)}
        />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Login"}
        </button>
      </form>
      <p style={{ marginTop: 24 }}>
        Need an account? <span role="link" style={{ color: "#0f5a44", cursor: "pointer" }} onClick={() => navigate("/register")}>
          Create one now
        </span>
      </p>
      <p style={{ marginTop: 8 }}>
        <span role="link" style={{ color: "#0f5a44", cursor: "pointer" }} onClick={() => navigate("/forgot-password")}>
          Forgot your password?
        </span>
      </p>
    </div>
  );
};

export default LoginPage;

