import axios from "axios";

// Runtime-resolved backend origin — avoids CORS when the frontend is served
// from a custom domain (e.g. altiaro.com) different from the build-time
// REACT_APP_BACKEND_URL baked by Webpack.
export const BACKEND_URL =
  (typeof window !== "undefined" &&
   window.location &&
   window.location.origin &&
   !window.location.origin.startsWith("http://localhost"))
    ? window.location.origin
    : (process.env.REACT_APP_BACKEND_URL || "");

export const api = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

export const formatError = (detail) => {
  if (detail == null) return "Une erreur est survenue.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
};

export const apiCall = async (fn) => {
  try {
    const { data } = await fn();
    return { data, error: null };
  } catch (e) {
    return { data: null, error: formatError(e.response?.data?.detail) || e.message };
  }
};
