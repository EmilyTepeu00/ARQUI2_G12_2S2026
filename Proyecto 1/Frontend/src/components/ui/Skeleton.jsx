import clsx from "clsx";

export function Skeleton({ className }) {
  return <div className={clsx("animate-pulse rounded-2xl bg-white/[0.06]", className)} />;
}
