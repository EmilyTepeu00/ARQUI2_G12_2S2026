export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  let payload = null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await res.json().catch(() => null);
  }

  if (!res.ok) {
    const message = payload?.mensaje || payload?.errores?.join(", ") || `Error ${res.status}`;
    throw new ApiError(message, res.status, payload);
  }

  return payload;
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body: JSON.stringify(body) }),
  put: (path, body) => request(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: (path) => request(path, { method: "DELETE" }),
};

export { ApiError };
