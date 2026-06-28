"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { StatusBadge } from "@/components/StatusBadge";
import { deleteJob, getJob, type ContentJob } from "@/lib/api";

const TABS = [
  { id: "final" as const, label: "Final", icon: "✨" },
  { id: "draft" as const, label: "Draft", icon: "📝" },
  { id: "research" as const, label: "Research", icon: "🔍" },
  { id: "logs" as const, label: "Agent Logs", icon: "📋" },
];

export default function JobDetail() {
  const params = useParams();
  const jobId = params.id as string;

  const [job, setJob] = useState<ContentJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"final" | "draft" | "research" | "logs">("final");

  const fetchJob = useCallback(async () => {
    try {
      const data = await getJob(jobId);
      setJob(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load job");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJob();
    const interval = setInterval(() => {
      if (job?.status !== "completed" && job?.status !== "failed") {
        fetchJob();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [fetchJob, job?.status]);

  async function handleDelete() {
    if (!confirm("Delete this job?")) return;
    try {
      await deleteJob(jobId);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  }

  if (loading) {
    return (
      <div className="page-bg">
        <Navbar />
        <main className="relative mx-auto max-w-4xl px-4 py-20 text-center">
          <span className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
          <p className="mt-4 text-slate-500">Loading job...</p>
        </main>
      </div>
    );
  }

  if (error && !job) {
    return (
      <div className="page-bg">
        <Navbar />
        <main className="relative mx-auto max-w-4xl px-4 py-20 text-center">
          <p className="text-red-400">{error}</p>
          <Link href="/" className="btn-primary mt-4">Back to Dashboard</Link>
        </main>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="page-bg">
        <Navbar />
        <main className="relative mx-auto max-w-4xl px-4 py-20 text-center">
          <p className="text-slate-500">Job not found</p>
        </main>
      </div>
    );
  }

  const isProcessing = !["completed", "failed"].includes(job.status);

  return (
    <div className="page-bg">
      <Navbar />

      <main className="relative mx-auto max-w-4xl px-4 py-10 sm:px-6">
        <Link href="/" className="text-sm text-slate-500 hover:text-brand-400">
          ← Back to Dashboard
        </Link>

        <header className="mt-4 animate-fade-in">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-display text-2xl font-bold text-white sm:text-3xl">
                {job.topic}
              </h1>
              <p className="mt-2 text-sm text-slate-500">
                {job.content_type.replace("_", " ")} · {job.tone} tone
                {job.target_audience && ` · ${job.target_audience}`}
              </p>
            </div>
            <StatusBadge status={job.status} pulse={isProcessing} />
          </div>
        </header>

        {isProcessing && (
          <div className="mt-6 flex items-center gap-3 rounded-xl border border-brand-500/20 bg-brand-500/5 px-5 py-4 animate-slide-up">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            <p className="text-sm text-brand-300">
              Agents are working on your content ({job.status.replace("_", " ")})...
            </p>
          </div>
        )}

        {job.error_message && (
          <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-400">
            {job.error_message}
          </div>
        )}

        {/* Tabs */}
        <div className="mt-8 flex gap-1 overflow-x-auto rounded-xl bg-surface-800/50 p-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2.5 text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-brand-500/20 text-white shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              <span>{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        <div className="glass-card mt-4 min-h-[300px] p-6 sm:p-8 animate-slide-up">
          {activeTab === "final" && (
            job.final_content ? (
              <div className="prose prose-invert max-w-none text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
                {job.final_content}
              </div>
            ) : (
              <EmptyTab message="Final content not ready yet" />
            )
          )}
          {activeTab === "draft" && (
            job.draft_content ? (
              <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
                {job.draft_content}
              </div>
            ) : (
              <EmptyTab message="Draft not ready yet" />
            )
          )}
          {activeTab === "research" && (
            job.research_notes ? (
              <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
                {job.research_notes}
              </div>
            ) : (
              <EmptyTab message="Research not ready yet" />
            )
          )}
          {activeTab === "logs" && (
            job.agent_logs && job.agent_logs.length > 0 ? (
              <div className="space-y-3">
                {job.agent_logs.map((log, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-white/5 bg-surface-700/30 px-4 py-3"
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded-md bg-brand-500/20 px-2 py-0.5 text-xs font-semibold uppercase text-brand-300">
                        {log.agent}
                      </span>
                      <span className="text-xs text-slate-500">{log.action}</span>
                    </div>
                    <p className="mt-1.5 text-sm text-slate-400">{log.summary}</p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyTab message="No agent logs yet" />
            )
          )}
        </div>

        <button
          onClick={handleDelete}
          className="mt-6 rounded-xl border border-red-500/30 px-5 py-2 text-sm text-red-400 transition-colors hover:bg-red-500/10"
        >
          Delete Job
        </button>
      </main>
    </div>
  );
}

function EmptyTab({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <span className="text-4xl opacity-50">⏳</span>
      <p className="mt-3 text-slate-500">{message}</p>
    </div>
  );
}
