import { useEffect, useState } from "react";
import { Button } from "../ui/Button";
import { Modal, Field } from "../ui/Modal";

const GENEROS = ["no_especificado", "masculino", "femenino", "otro"];
const ROLES = ["operador_1", "operador_2"];
const METODOS = ["rfid", "bluetooth", "huella", "llave", "manual"];

const EMPTY = {
  id_operador: "",
  nombre: "",
  edad: "",
  genero: "no_especificado",
  rol: "operador_1",
  metodo_acceso: "rfid",
  activo: true,
};

export function OperadorFormModal({ open, onClose, onSubmit, initialData }) {
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const isEdit = Boolean(initialData);

  useEffect(() => {
    if (open) {
      setForm(
        initialData
          ? {
              id_operador: initialData.id_operador ?? "",
              nombre: initialData.nombre ?? "",
              edad: initialData.edad ?? "",
              genero: initialData.genero ?? "no_especificado",
              rol: initialData.rol ?? "operador_1",
              metodo_acceso: initialData.metodo_acceso ?? "rfid",
              activo: initialData.activo ?? true,
            }
          : EMPTY
      );
      setError(null);
    }
  }, [open, initialData]);

  if (!open) return null;

  const handleChange = (field) => (e) => {
    const value = e.target.type === "checkbox" ? e.target.checked : e.target.value;
    setForm((f) => ({ ...f, [field]: value }));
  };

  const validar = () => {
    if (!isEdit && !form.id_operador.trim()) {
      return "El ID de operador es obligatorio (OP1, OP2, OP3)";
    }
    if (!form.nombre.trim()) {
      return "El nombre es obligatorio";
    }
    if (form.edad !== "" && (Number(form.edad) < 0 || Number(form.edad) > 120)) {
      return "La edad debe estar entre 0 y 120";
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
      const payload = {
        ...form,
        id_operador: form.id_operador.trim().toUpperCase(),
        edad: form.edad === "" ? undefined : Number(form.edad),
      };
      if (isEdit) delete payload.id_operador;
      await onSubmit(payload);
      onClose();
    } catch (err) {
      setError(err.message || "No se pudo guardar el operador");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title={isEdit ? "Editar operador" : "Nuevo operador"}
      onClose={onClose}
      onSubmit={handleSubmit}
      error={error}
      footer={
        <>
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={saving}>{saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear operador"}</Button>
        </>
      }
    >
      <Field label="ID de operador" required>
        <input required disabled={isEdit} value={form.id_operador} onChange={handleChange("id_operador")} className="input" placeholder="OP1" />
      </Field>
      <Field label="Nombre" required>
        <input required value={form.nombre} onChange={handleChange("nombre")} className="input" placeholder="Ana López" />
      </Field>
      <Field label="Edad">
        <input type="number" min="0" max="120" value={form.edad} onChange={handleChange("edad")} className="input" placeholder="34" />
      </Field>
      <Field label="Género">
        <select value={form.genero} onChange={handleChange("genero")} className="input">
          {GENEROS.map((g) => (<option key={g} value={g}>{g.replace("_", " ")}</option>))}
        </select>
      </Field>
      <Field label="Rol operativo">
        <select value={form.rol} onChange={handleChange("rol")} className="input">
          {ROLES.map((r) => (<option key={r} value={r}>{r.replace("_", " ")}</option>))}
        </select>
      </Field>
      <Field label="Método de acceso">
        <select value={form.metodo_acceso} onChange={handleChange("metodo_acceso")} className="input">
          {METODOS.map((m) => (<option key={m} value={m}>{m}</option>))}
        </select>
      </Field>
      <Field label="Estado" full>
        <label className="flex items-center gap-2 text-sm text-ink-2">
          <input type="checkbox" className="accent-accent" checked={form.activo} onChange={handleChange("activo")} />
          Operador activo (puede abrir la incubadora)
        </label>
      </Field>
    </Modal>
  );
}
