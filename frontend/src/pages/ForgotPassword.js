import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import API from "../Services/api";

const useQuery = () => {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search), [search]);
};

const ForgotPassword = () => {
  const navigate = useNavigate();
  const query = useQuery();

  const initUid = query.get("uid") || "";
  const initToken = query.get("token") || "";

  const [email, setEmail] = useState("");
  const [requestStatus, setRequestStatus] = useState("");
  const [requestError, setRequestError] = useState("");
  const [isRequesting, setIsRequesting] = useState(false);

  const [uid, setUid] = useState(initUid);
  const [token, setToken] = useState(initToken);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [confirmStatus, setConfirmStatus] = useState("");
  const [confirmError, setConfirmError] = useState("");
  const [isConfirming, setIsConfirming] = useState(false);

  const showConfirm = Boolean(initUid && initToken);

  useEffect(() => {
    if (showConfirm) {
      setRequestStatus("");
      setRequestError("");
    }
  }, [showConfirm]);

  const submitRequest = async (e) => {
    e.preventDefault();
    setIsRequesting(true);
    setRequestError("");
    setRequestStatus("");
    try {
      const { data } = await API.post("password-reset-request/", { email: email.trim() });
      setRequestStatus(
        data?.message ||
          "If an account exists for that email, a reset link will be sent."
      );
      // For dev environments, backend may include uid/token/reset_url
      if (data?.uid) setUid(data.uid);
      if (data?.token) setToken(data.token);
    } catch (err) {
      const message = err.response?.data?.error || "Unable to submit request.";
      setRequestError(message);
    } finally {
      setIsRequesting(false);
    }
  };

  const submitConfirm = async (e) => {
    e.preventDefault();
    setIsConfirming(true);
    setConfirmError("");
    setConfirmStatus("");
    if (password !== confirm) {
      setConfirmError("Passwords do not match.");
      setIsConfirming(false);
      return;
    }
    try {
      await API.post("password-reset-confirm/", {
        uid: uid.trim(),
        token: token.trim(),
        new_password: password,
      });
      setConfirmStatus("Password updated. You can now sign in.");
      setTimeout(() => navigate("/"), 1200);
    } catch (err) {
      const message = err.response?.data?.error || "Unable to reset password.";
      setConfirmError(message);
    } finally {
      setIsConfirming(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "60px auto", textAlign: "center" }}>
      <h1>Password reset</h1>

      {!showConfirm && (
        <form onSubmit={submitRequest} style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 24 }}>
          <input
            type="email"
            placeholder="Your account email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <button type="submit" disabled={isRequesting}>
            {isRequesting ? "Submitting..." : "Send reset link"}
          </button>
          {requestStatus && <p style={{ color: "#0f5a44", marginTop: 8 }}>{requestStatus}</p>}
          {requestError && <p style={{ color: "#b00020", marginTop: 8 }}>{requestError}</p>}
        </form>
      )}

      <div style={{ marginTop: 32 }}>
        <h2 style={{ fontSize: 18 }}>Set new password</h2>
        <form onSubmit={submitConfirm} style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 12 }}>
          <input
            placeholder="UID"
            value={uid}
            onChange={(e) => setUid(e.target.value)}
            required
          />
          <input
            placeholder="Token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="New password (min 8 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Confirm new password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
          <button type="submit" disabled={isConfirming}>
            {isConfirming ? "Updating..." : "Update password"}
          </button>
          {confirmStatus && <p style={{ color: "#0f5a44", marginTop: 8 }}>{confirmStatus}</p>}
          {confirmError && <p style={{ color: "#b00020", marginTop: 8 }}>{confirmError}</p>}
        </form>
      </div>
    </div>
  );
};

export default ForgotPassword;

