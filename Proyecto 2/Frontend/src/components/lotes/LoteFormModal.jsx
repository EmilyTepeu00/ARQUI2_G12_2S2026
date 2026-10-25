import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Modal, Field } from "../ui/Modal";

const ESTADOS = ["incubando", "eclosionado", "descartado"];
const CODIGO_REGEX = /^[A-Za-z0-9-]+$/;
const MAX_HUEVOS = 500;
const EMPTY = {
  codigo: "",
  nombre_lote: "",
  cantidad_huevos: "",
  raza: "",
  responsable: "",
  observaciones: "",
  estado: "incubando",
};

export function LoteFormModal({ open, onClose, onSubmit, initialData }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const isEdit = Boolean(initialData);

  useEffect(() => {
    if (open) {
      setForm(
        initialData
          ? {
              codigo: initialData.codigo ?? "",
              nombre_lote: initialData.nombre_lote ?? "",
              cantidad_huevos: initialData.cantidad_huevos ?? "",
              raza: initialData.raza ?? "",
              responsable: initialData.responsable ?? "",
              observaciones: initialData.observaciones ?? "",
              estado: initialData.estado ?? "incubando",
            }
          : EMPTY
      );
      setError(null);
    }
  }, [open, initialData]);

  if (!open) return null;

  const handleChange = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }));

  const validar = () => {
    const codigo = form.codigo.trim();
    const nombre = form.nombre_lote.trim();
    const cantidad = Number(form.cantidad_huevos);

    if (!isEdit) {
      if (!codigo) return "El código del lote es obligatorio";
      if (!CODIGO_REGEX.test(codigo)) {
        return "El código solo puede tener letras, números y guiones.";
      }
    }

    if (!nombre) return "El nombre del lote es obligatorio";
    if (nombre.length > 80) return "El nombre del lote es demasiado largo (máximo 80 caracteres).";

    if (form.cantidad_huevos === "") return "Indica la cantidad de huevos del lote";
    if (!Number.isInteger(cantidad) || cantidad < 1) {
      return "La cantidad de huevos debe ser un número entero mayor a 0";
    }
    if (cantidad > MAX_HUEVOS) {
      return `La cantidad de huevos parece demasiado alta (máximo ${MAX_HUEVOS}). Revise el dato.`;
    }

    if (form.observaciones.length > 500) {
      return "Las observaciones son demasiado largas (máximo 500 caracteres).";
    }

    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const mensajeError = validar();
    if (mensajeError) {
      setError(mensajeError);
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        ...form,
        codigo: form.codigo.trim(),
        nombre_lote: form.nombre_lote.trim(),
        responsable: form.responsable.trim(),
        observaciones: form.observaciones.trim(),
        cantidad_huevos: Number(form.cantidad_huevos),
      });
      onClose();
    } catch (err) {
      setError(err.message || "No se pudo guardar el lote.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={isEdit ? "Editar lote" : "Nuevo lote"}
      onClose={onClose}
      onSubmit={handleSubmit}
      error={error}
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={saving}>{saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear lote"}</Button>
        </>
      }
    >
      <Field label="Código" required>
        <input required disabled={isEdit} value={form.codigo} onChange={handleChange("codigo")} className="input" placeholder="LOTE-001" maxLength={30} />
      </Field>
      <Field label="Nombre del lote" required>
        <input required value={form.nombre_lote} onChange={handleChange("nombre_lote")} className="input" placeholder="Incubación agosto" maxLength={80} />
      </Field>
      <Field label="Cantidad de huevos" required>
        <input required type="number" min="1" max={MAX_HUEVOS} step="1" value={form.cantidad_huevos} onChange={handleChange("cantidad_huevos")} className="input" placeholder="24" />
      </Field>
      <Field label="Raza">
        <input value={form.raza} onChange={handleChange("raza")} className="input" placeholder="Leghorn" maxLength={50} />
      </Field>
      <Field label="Responsable">
        <input value={form.responsable} onChange={handleChange("responsable")} className="input" placeholder="Nombre del responsable" maxLength={80} />
      </Field>
      <Field label="Estado">
        <select value={form.estado} onChange={handleChange("estado")} className="input">
          {ESTADOS.map((e) => (<option key={e} value={e}>{e}</option>))}
        </select>
      </Field>
      <Field label="Observaciones" full>
        <textarea value={form.observaciones} onChange={handleChange("observaciones")} className="input min-h-20 resize-none" placeholder="Notas adicionales..." maxLength={500} />
        <span className="mt-1 self-end text-[11px] text-muted">{form.observaciones.length}/500</span>
      </Field>
    </Modal>
  );
}
