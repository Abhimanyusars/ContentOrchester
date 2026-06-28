"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { StatusBadge } from "@/components/StatusBadge";
import {
  approveContent,
  getBriefStatus,
  getContent,
  getWsUrl,
  type BriefStatus,
} from "@/lib/brief-api";

const PIPELINE_STEPS = [
  { key: "researcher", label: "Research", icon: "🔍", desc: "Gathering facts" },
  { key: "writer", label: "Write", icon: "✍️", desc: "Drafting content" },
  { key: "seo", label: "SEO", icon: "📈", desc: "Optimizing" },
  { key: "human_review", label: "Human Review", icon: "👤", desc: "Your approval" },
  { key: "editor", label: "Quality Check", icon: "✅", desc: "Final polish" },
  { key: "publish", label: "Publish", icon: "🚀", desc: "Going live" },
];

export default function BriefStatusPage() {
  const params = useParams();
  const taskId = params.taskId as string;

  const [status, setStatus] = useState<BriefStatus | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [feedback, setFeedback] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getBriefStatus(taskId);
      setStatus(data);
      if (data.status === "human_review" || data.status === "completed") {
        const content = await getContent(taskId);
        setDraft(content.draft_content || content.final_content);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load status");
    }
  }, [taskId]);

  useEffect(() => {
    fetchStatus();
    const ws = new WebSocket(getWsUrl(taskId));
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status) {
          setStatus((prev) =>
            prev ? { ...prev, status: data.status, current_node: data.current_node } : prev,
          );
          fetchStatus();
        }
      } catch {
        /* ping */
      }
    };
    const interval = setInterval(fetchStatus, 5000);
    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [taskId, fetchStatus]);

  async function handleApprove(approved: boolean) {
    setActionLoading(true);
    setError(null);
    try {
      await approveContent(taskId, approved, approved ? undefined : feedback);
      setShowFeedback(false);
      await fetchStatus();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setActionLoading(false);
    }
  }

  const currentNode = status?.current_node;
  const isDone = status?.status === "completed";
  const isFailed = status?.status === "failed";
  const isReview = status?.status === "human_review";
  const isRunning = status && !isDone && !isFailed && !isReview;

  function stepState(stepKey: string): "done" | "active" | "pending" {
    const order = PIPELINE_STEPS.map((s) => s.key);
    const currentIdx = currentNode ? order.indexOf(currentNode) : -1;
    const stepIdx = order.indexOf(stepKey);
    if (isDone) return "done";
    if (isFailed) return stepIdx <= currentIdx ? "done" : "pending";
    if (stepIdx < currentIdx) return "done";
    if (stepIdx === currentIdx) return "active";
    return "pending";
  }

  return (
    <div className="page-bg">
      <Navbar active="briefs" />

      <main className="relative mx-auto max-w-3xl px-4 py-10 sm:px-6">
        <div className="animate-fade-in">
          <Link href="/briefs/new" className="text-sm text-slate-500 hover:text-brand-400">
            ← New Brief
          </Link>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <h1 className="font-display text-2xl font-bold text-white">
              Pipeline Status
            </h1>
            {status && (
              <StatusBadge
                status={status.status}
                pulse={isRunning ?? false}
              />
            )}
          </div>
          <p className="mt-1 font-mono text-xs text-slate-600">{taskId}</p>
        </div>

        {/* Timeline */}
        <div className="glass-card mt-8 animate-slide-up p-6 sm:p-8">
          <h2 className="mb-6 text-sm font-medium uppercase tracking-wider text-slate-500">
            Agent Pipeline
          </h2>
          <div className="relative space-y-0">
            {PIPELINE_STEPS.map((step, i) => {
              const state = stepState(step.key);
              const isLast = i === PIPELINE_STEPS.length - 1;
              return (
                <div key={step.key} className="relative flex gap-4 pb-8 last:pb-0">
                  {!isLast && (
                    <div
                      className={`absolute left-5 top-10 h-full w-0.5 ${
                        state === "done" ? "bg-emerald-500/50" : "bg-surface-600"
                      }`}
                    />
                  )}
                  <div
                    className={`relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-lg transition-all ${
                      state === "done"
                        ? "bg-emerald-500/20 shadow-lg shadow-emerald-500/10"
                        : state === "active"
                        ? "bg-brand-500/20 shadow-lg shadow-brand-500/20 animate-pulse-soft"
                        : "bg-surface-700"
                    }`}
                  >
                    {state === "done" ? "✓" : step.icon}
                  </div>
                  <div className="flex-1 pt-1.5">
                    <div className="flex items-center gap-2">
                      <p
                        className={`font-medium ${
                          state === "active" ? "text-white" : state === "done" ? "text-emerald-400" : "text-slate-500"
                        }`}
                      >
                        {step.label}
                      </p>
                      {state === "active" && (
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
                      )}
                    </div>
                    <p className="text-xs text-slate-600">{step.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Human review */}
        {isReview && draft && (
          <div className="glass-card mt-6 animate-slide-up border-orange-500/20 p-6 sm:p-8">
            <div className="mb-4 flex items-center gap-2">
              <span className="text-xl">👤</span>
              <h2 className="font-display text-lg font-semibold text-white">
                Your Review Needed
              </h2>
            </div>
            <div className="max-h-80 overflow-y-auto rounded-xl bg-surface-700/50 p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
              {draft}
            </div>

            {showFeedback && (
              <textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Describe what needs to change..."
                rows={3}
                className="input-field mt-4 resize-none"
              />
            )}

            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => handleApprove(true)}
                disabled={actionLoading}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-50"
              >
                ✓ Approve &amp; Publish
              </button>
              <button
                onClick={() => {
                  if (showFeedback && feedback.trim()) {
                    handleApprove(false);
                  } else {
                    setShowFeedback(true);
                  }
                }}
                disabled={actionLoading}
                className="btn-secondary !py-2.5"
              >
                Request Revision
              </button>
            </div>
          </div>
        )}

        {/* Completed */}
        {isDone && draft && (
          <div className="glass-card mt-6 animate-slide-up border-emerald-500/20 p-6 sm:p-8">
            <div className="mb-4 flex items-center gap-2">
              <span className="text-2xl">🎉</span>
              <h2 className="font-display text-lg font-semibold text-emerald-400">
                Content Published
              </h2>
            </div>
            <div className="rounded-xl bg-surface-700/50 p-5 text-sm leading-relaxed text-slate-300 whitespace-pre-wrap">
              {draft}
            </div>
            <Link href="/briefs/new" className="btn-primary mt-6">
              Create Another Brief
            </Link>
          </div>
        )}

        {/* Running indicator */}
        {isRunning && (
          <div className="mt-6 flex items-center justify-center gap-3 rounded-xl border border-brand-500/20 bg-brand-500/5 py-4 text-sm text-brand-300">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
            Agents are working on your content...
          </div>
        )}

        {error && (
          <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</p>
        )}
        {status?.error_message && (
          <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {status.error_message}
          </p>
        )}
      </main>
    </div>
  );
}
