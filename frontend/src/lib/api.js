import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

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
