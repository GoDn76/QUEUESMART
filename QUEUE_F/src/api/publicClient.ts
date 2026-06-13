import axios from "axios";

// This function forces the URL to be ONLY the domain/port (strips /api/v1 automatically)
const getBaseOrigin = () => {
  const envUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
  try {
    const url = new URL(envUrl);
    return url.origin; // Returns "http://localhost:8000" no matter what
  } catch (e) {
    return "http://localhost:8000";
  }
};

const publicApiClient = axios.create({
  baseURL: getBaseOrigin(),
  headers: {
    "Content-Type": "application/json",
  },
});

export default publicApiClient;