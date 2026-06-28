const STATUS_STYLES: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  researching: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  writing: "bg-brand-500/15 text-brand-300 border-brand-500/30",
  seo: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  editing: "bg-brand-500/15 text-brand-300 border-brand-500/30",
  human_review: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  quality_check: "bg-indigo-500/15 text-indigo-400 border-indigo-500/30",
  publishing: "bg-violet-500/15 text-violet-400 border-violet-500/30",
  revision: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  completed: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
};

interface StatusBadgeProps {
  status: string;
  pulse?: boolean;
}

export function StatusBadge({ status, pulse = false }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? "bg-slate-500/15 text-slate-400 border-slate-500/30";
  const label = status.replace(/_/g, " ");

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${style} ${
        pulse ? "animate-pulse-soft" : ""
      }`}
    >
      {(status === "researching" || status === "writing" || status === "seo") && (
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
      )}
      {label}
    </span>
  );
}
