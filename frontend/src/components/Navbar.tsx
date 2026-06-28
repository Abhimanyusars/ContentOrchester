import Link from "next/link";

interface NavbarProps {
  active?: "home" | "briefs";
}

export function Navbar({ active = "home" }: NavbarProps) {
  return (
    <nav className="sticky top-0 z-50 border-b border-white/[0.06] bg-surface-900/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link href="/" className="group flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 shadow-lg shadow-brand-500/30 transition-transform group-hover:scale-105">
            <span className="text-sm font-bold text-white">CF</span>
          </div>
          <span className="font-display text-lg font-bold tracking-tight text-white">
            ContentForge
          </span>
        </Link>

        <div className="flex items-center gap-2 sm:gap-4">
          <Link
            href="/"
            className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
              active === "home"
                ? "bg-white/10 text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Dashboard
          </Link>
          <Link href="/briefs/new" className="btn-primary !py-2 !px-4 text-sm">
            <span className="text-base leading-none">+</span>
            New Brief
          </Link>
        </div>
      </div>
    </nav>
  );
}
