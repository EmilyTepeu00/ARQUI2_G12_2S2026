import { API_BASE_URL, fetchBlob, descargarBlob } from "./client";

export async function descargarReportePdf(tecnico) {
  const params = new URLSearchParams();
  if (tecnico) params.set("tecnico", tecnico);

  const res = await fetch(`${API_BASE_URL}/api/reportes/pdf?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`No se pudo generar el reporte (${res.status})`);
  }
  await descargarBlob(res, "smartegg_reporte.pdf");
}

// Reporte PDF de un operador específico. Un operador solo puede pedir el suyo (el backend responde 403 si pide el de otro)
// admin puede pedir el de cualquiera
export async function descargarReportePorOperador(idOperador, { tecnico } = {}) {
  const params = new URLSearchParams();
  if (tecnico) params.set("tecnico", tecnico);

  const res = await fetchBlob(`/api/reportes/pdf/operador/${idOperador}?${params.toString()}`);
  await descargarBlob(res, `smartegg_reporte_${idOperador}.pdf`);
}