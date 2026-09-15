import { api } from "./client";

export const lotesApi = {
  listar: () => api.get("/api/lotes"),
  obtener: (id) => api.get(`/api/lotes/${id}`),
  crear: (data) => api.post("/api/lotes", data),
  actualizar: (id, data) => api.put(`/api/lotes/${id}`, data),
  eliminar: (id) => api.delete(`/api/lotes/${id}`),
};
