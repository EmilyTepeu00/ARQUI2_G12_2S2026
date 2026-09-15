import { api, fetchBlob, descargarBlob } from "./client";

export const perfilApi = {
  obtener: () => api.get("/api/perfil"),
  diagnosticos: (params = {}) => api.get(`/api/perfil/diagnosticos?${new URLSearchParams(params)}`),
  informe: (params = {}) => api.get(`/api/perfil/informes?${new URLSearchParams(params)}`),
};

// Descarga el reporte PDF del operador dueño de la sesión
export async function descargarReportePropio(params = {}) {
  const res = await fetchBlob(`/api/perfil/reporte.pdf?${new URLSearchParams(params)}`);
  await descargarBlob(res, "smartegg_reporte.pdf");
}