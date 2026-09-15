import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { GlobalAlarmListener } from "./GlobalAlarmListener";
import { useConnectionStatus } from "../../hooks/useConnectionStatus";
import logoIcono from "../../assets/logo-icono.png";

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const estado = useConnectionStatus();

  return (
    <div className="flex min-h-screen bg-slate-950">
      <GlobalAlarmListener />
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-h-screen flex-1 flex-col">
        <Topbar onMenuClick={() => setSidebarOpen(true)} estado={estado} />
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-7xl">
            <Outlet context={{ estado }} />
          </div>
        </main>
      </div>

      <img
        src={logoIcono}
        alt=""
        className="pointer-events-none fixed bottom-4 right-4 h-auto w-16 opacity-10 select-none"
      />
    </div>
  );
}