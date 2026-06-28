"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[#0f0f14] px-4 text-center text-white">
      <h1 className="text-2xl font-bold">Something went wrong</h1>
      <p className="mt-3 max-w-md text-sm text-slate-400">
        {error.message || "The dashboard failed to load."}
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded-xl bg-violet-600 px-5 py-2.5 text-sm font-semibold hover:bg-violet-500"
      >
        Try again
      </button>
    </div>
  );
}
