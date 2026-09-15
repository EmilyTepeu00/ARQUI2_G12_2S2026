import clsx from "clsx";
import { Wifi, WifiOff } from "lucide-react";

export function ConnectionPill({ connected, label }) {
  return (
    <div
      className={clsx(
        "flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
        connected
          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
          : "border-red-500/30 bg-red-500/10 text-red-400"
      )}
    >
      <span className="relative flex h-2 w-2">
        {connected && (
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        )}
        <span
          className={clsx(
            "relative inline-flex h-2 w-2 rounded-full",
            connected ? "bg-emerald-400" : "bg-red-400"
          )}
        />
      </span>
      {connected ? <Wifi size={14} /> : <WifiOff size={14} />}
      <span>{label}</span>
    </div>
  );
}
