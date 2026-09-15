import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "../ui/Button";

const GENEROS = ["no_especificado", "masculino", "femenino", "otro"];
const ROLES = ["operador_1", "operador_2"];
const METODOS = ["rfid", "huella", "llave", "manual"];

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={onClose} />
      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl"
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-base font-semibold text-slate-100">
            {isEdit ? "Editar operador" : "Nuevo operador"}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-800 hover:text-slate-300"
          >
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-1 gap-4 px-6 py-5 sm:grid-cols-2">
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
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={form.activo} onChange={handleChange("activo")} />
              Operador activo (puede abrir la incubadora)
            </label>
          </Field>
        </div>

        {error && <p className="px-6 pb-2 text-sm text-red-400">{error}</p>}

        <div className="flex items-center justify-end gap-2 border-t border-slate-800 px-6 py-4">
          <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={saving}>{saving ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear operador"}</Button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, required, full, children }) {
  return (
    <label className={`flex flex-col gap-1.5 ${full ? "sm:col-span-2" : ""}`}>
      <span className="text-xs font-medium text-slate-400">
        {label} {required && <span className="text-amber-500">*</span>}
      </span>
      {children}
    </label>
  );
}