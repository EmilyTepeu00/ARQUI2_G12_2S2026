import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { Layout } from "./components/layout/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Historial } from "./pages/Historial";
import { Alarmas } from "./pages/Alarmas";
import { Lotes } from "./pages/Lotes";
import { Reportes } from "./pages/Reportes";

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#0f172a",
            color: "#e2e8f0",
            border: "1px solid #1e293b",
            fontSize: "13px",
          },
          success: { iconTheme: { primary: "#34d399", secondary: "#0f172a" } },
          error: { iconTheme: { primary: "#f87171", secondary: "#0f172a" } },
        }}
      />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/historial" element={<Historial />} />
          <Route path="/alarmas" element={<Alarmas />} />
          <Route path="/lotes" element={<Lotes />} />
          <Route path="/reportes" element={<Reportes />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
