import clsx from "clsx";

export function Skeleton({ className }) {
  return <div className={clsx("animate-pulse rounded-lg bg-slate-800/80", className)} />;
}
