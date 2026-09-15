// Por defecto se usan rutas relativas ("/api/..."), asi el navegador pega al
// mismo origen desde el que se sirvio la pagina y el proxy (Caddy) reparte.
// Eso evita CORS y hace que la app funcione igual en localhost que detras del
// tunel publico, sin recompilar. VITE_API_BASE_URL solo se define para apuntar
// a un backend en otro host.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || "";

// Mismo nombre de llave que usa AuthContext para guardar el token
export const TOKEN_STORAGE_KEY = "smartegg_token";

class ApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

async function request(path, options = {}) {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const res = await fetch(`${API_BASE_URL}${path}`, { headers, ...options });

  let payload = null;
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    payload = await res.json().catch(() => null);
  }

  if (res.status === 401 && token) {
    window.dispatchEvent(new CustomEvent("smartegg:unauthorized"));
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

// Descarga de reportes PDF
export async function fetchBlob(path) {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (res.status === 401 && token) {
    window.dispatchEvent(new CustomEvent("smartegg:unauthorized"));
  }

  if (!res.ok) {
    let mensaje = `No se pudo generar el archivo (${res.status})`;
    try {
      const payload = await res.json();
      mensaje = payload?.mensaje || mensaje;
    } catch {
      // Mensaje por defecto si no se puede parsear el JSON de error
    }
    throw new ApiError(mensaje, res.status);
  }

  return res;
}

export async function descargarBlob(res, defaultFilename) {
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || defaultFilename;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export { ApiError };