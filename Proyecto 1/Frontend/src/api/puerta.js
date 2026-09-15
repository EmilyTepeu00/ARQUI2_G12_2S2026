import { api } from "./client";

export const puertaApi = {
  eventos: (params = {}) => api.get(`/api/puerta/eventos?${new URLSearchParams(params)}`),
  resumen: (params = {}) => api.get(`/api/puerta/resumen?${new URLSearchParams(params)}`),
  registrarEvento: (data) => api.post("/api/puerta/eventos", data),
};