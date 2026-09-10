import { api } from "./client";

export const sensorsApi = {
  actual: () => api.get("/api/sensores/actual"),
  historial: (limit = 100) => api.get(`/api/sensores/historial?limit=${limit}`),
  estado: () => api.get("/api/sensores/estado"),
  alarmas: (limit = 50) => api.get(`/api/sensores/alarmas?limit=${limit}`),
};
