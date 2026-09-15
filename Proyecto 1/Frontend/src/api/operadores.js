import { api } from "./client";

export const operadoresApi = {
  listar: () => api.get("/api/operadores"),
  obtener: (id) => api.get(`/api/operadores/${id}`),
  crear: (data) => api.post("/api/operadores", data),
  actualizar: (id, data) => api.put(`/api/operadores/${id}`, data),
  eliminar: (id) => api.delete(`/api/operadores/${id}`),
};