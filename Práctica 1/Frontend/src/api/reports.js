import { API_BASE_URL } from "./client";

export async function descargarReportePdf(tecnico) {
  const params = new URLSearchParams();
  if (tecnico) params.set("tecnico", tecnico);

  const res = await fetch(`${API_BASE_URL}/api/reportes/pdf?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`No se pudo generar el reporte (${res.status})`);
  }

  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match?.[1] || `smartegg_reporte.pdf`;

  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
