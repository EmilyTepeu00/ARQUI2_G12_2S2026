import { api } from "./client";

export const authApi = {
  login: (username, password) => api.post("/api/auth/login", { username, password }),
  yo: () => api.get("/api/auth/yo"),
  cambiarPassword: (password_actual, password_nueva) =>
    api.post("/api/auth/cambiar-password", { password_actual, password_nueva }),
  listarUsuarios: () => api.get("/api/auth/usuarios"),
  crearUsuario: (data) => api.post("/api/auth/usuarios", data),
  eliminarUsuario: (username) => api.delete(`/api/auth/usuarios/${username}`),
};