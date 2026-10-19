import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";
import logoIcono from "../assets/logo-icono.png";

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!username.trim() || !password) {
      setError("Ingrese su usuario y contraseña");
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      if (err.status === 401) setError("Usuario o contraseña incorrectos");
      else if (err.status === 403) setError("Esta cuenta está desactivada. Contacta al administrador.");
      else setError(err.message || "No se pudo iniciar sesión. Intente de nuevo");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-12">
      {/* Halos de luz detrás del vidrio. */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[420px] w-[420px] -translate-x-[85%] -translate-y-[70%] rounded-full bg-accent/40 blur-[110px]" />
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[360px] w-[360px] -translate-x-[5%] -translate-y-[5%] rounded-full bg-[#8b5cf6]/30 blur-[120px]" />

      <form onSubmit={handleSubmit} className="glass relative w-full max-w-md space-y-5 rounded-[2rem] !bg-surface/40 p-8 sm:p-10">
        <div className="flex items-center gap-2.5">
          <img src={logoIcono} alt="" className="h-9 w-9 object-contain" />
          <span className="text-lg font-bold tracking-tight">SmartEgg</span>
        </div>

        <div className="pb-2 pt-4">
          <h1 className="text-gradient text-3xl font-semibold tracking-tight">Bienvenido de nuevo</h1>
          <p className="mt-2 text-sm text-ink-2">Ingrese con su usuario de administrador u operador.</p>
        </div>

        <label className="flex flex-col gap-1.5">
          <span className="label">Usuario</span>
          <input autoFocus value={username} onChange={(e) => setUsername(e.target.value)} className="input" placeholder="admin" autoComplete="username" />
        </label>

        <label className="flex flex-col gap-1.5">
          <span className="label">Contraseña</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input" placeholder="••••••••" autoComplete="current-password" />
        </label>

        {error && <p className="rounded-xl bg-bad-soft px-3 py-2 text-sm text-bad">{error}</p>}

        <Button type="submit" disabled={loading} className="w-full py-3">
          {loading ? (<><Loader2 size={16} className="animate-spin" /> Ingresando...</>) : "Ingresar"}
        </Button>

        <p className="pt-2 text-center text-xs text-muted">Incubadora inteligente · AYC2 Grupo 12</p>
      </form>
    </div>
  );
}
