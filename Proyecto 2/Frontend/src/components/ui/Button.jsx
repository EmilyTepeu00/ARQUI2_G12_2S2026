import clsx from "clsx";

const VARIANTS = {
  primary:
    "bg-gradient-to-b from-[#5b78ff] to-[#3a55e6] text-white shadow-[0_8px_24px_-8px_rgb(76_107_255/0.8),inset_0_1px_0_rgb(255_255_255/0.25)] hover:brightness-110",
  secondary: "border border-line bg-white/[0.04] text-ink hover:bg-white/[0.08]",
  ghost: "text-ink-2 hover:bg-white/[0.06] hover:text-ink",
  danger: "border border-bad/30 bg-bad-soft text-bad hover:bg-bad/25",
};

export function Button({ variant = "primary", className, children, ...props }) {
  return (
    <button
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-50",
        VARIANTS[variant],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
