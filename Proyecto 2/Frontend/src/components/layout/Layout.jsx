import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { GlobalAlarmListener } from "./GlobalAlarmListener";
import { useConnectionStatus } from "../../hooks/useConnectionStatus";

export function Layout() {
  const estado = useConnectionStatus();

  return (
    <div className="min-h-screen lg:p-6">
      <GlobalAlarmListener />
      <div className="glass mx-auto flex min-h-screen max-w-[1500px] flex-col overflow-hidden !bg-[#0b1024]/70 lg:min-h-[calc(100vh-3rem)] lg:flex-row lg:rounded-[2rem]">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar estado={estado} />
          <main className="flex-1 px-4 pb-12 pt-4 sm:px-6 lg:px-8">
            <Outlet context={{ estado }} />
          </main>
        </div>
      </div>
    </div>
  );
}
