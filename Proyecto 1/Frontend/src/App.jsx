import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";
import { Layout } from "./components/layout/Layout";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Historial } from "./pages/Historial";
import { Alarmas } from "./pages/Alarmas";
import { Lotes } from "./pages/Lotes";
import { Reportes } from "./pages/Reportes";
import { Perfil } from "./pages/Perfil";
import { Operadores } from "./pages/Operadores";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            style: { background: "rgba(18,25,51,0.85)", color: "#f2f4fb", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "999px", fontSize: "13px", backdropFilter: "blur(16px)" },
            success: { iconTheme: { primary: "#3ddc97", secondary: "#121933" } },
            error: { iconTheme: { primary: "#ff6b6b", secondary: "#121933" } },
          }}
        />
        <Routes>
          <Route path="/login" element={<Login />} />

          {/* Todo lo que sigue requiere sesión iniciada */}
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/historial" element={<Historial />} />
              <Route path="/alarmas" element={<Alarmas />} />
              <Route path="/lotes" element={<Lotes />} />
              <Route path="/reportes" element={<Reportes />} />
              <Route path="/perfil" element={<Perfil />} />
            </Route>
          </Route>

          {/* Solo administrador. */}
          <Route element={<ProtectedRoute rolesPermitidos={["administrador"]} />}>
            <Route element={<Layout />}>
              <Route path="/operadores" element={<Operadores />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
