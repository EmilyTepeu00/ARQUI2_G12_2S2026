import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Egg, LogIn, Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/Button";

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
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-500/20">
            <Egg size={28} className="text-slate-950" strokeWidth={2.5} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-50">SmartEgg</h1>
            <p className="text-sm text-slate-500">Plataforma IoT de incubación</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 p-6 shadow-lg shadow-black/20 backdrop-blur-sm">
          <div className="text-center">
            <h2 className="text-xl font-bold text-slate-100">Iniciar sesión</h2>
            <p className="mt-1 text-xs text-slate-500">
              Ingrese con su usuario de administrador u operador
            </p>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Usuario</span>
            <input autoFocus value={username} onChange={(e) => setUsername(e.target.value)} className="input" placeholder="admin" autoComplete="username" />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-400">Contraseña</span>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="input" placeholder="••••••••" autoComplete="current-password" />
          </label>

          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">{error}</p>
          )}

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? (<><Loader2 size={16} className="animate-spin" /> Ingresando...</>) : (<><LogIn size={16} /> Ingresar</>)}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-slate-600">Grupo 12</p>
      </div>
    </div>
  );
}