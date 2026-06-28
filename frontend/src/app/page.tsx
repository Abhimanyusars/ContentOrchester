"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { StatusBadge } from "@/components/StatusBadge";
import { createJob, listJobs, type ContentJob } from "@/lib/api";

const AGENTS = [
  { icon: "🔍", name: "Researcher", desc: "Web search & fact gathering" },
  { icon: "✍️", name: "Writer", desc: "Draft compelling content" },
  { icon: "📈", name: "SEO Agent", desc: "Optimize for search" },
  { icon: "✅", name: "Editor", desc: "Polish & publish" },
];

const CONTENT_TYPES = [
  { value: "blog_post", label: "Blog Post" },
  { value: "article", label: "Article" },
  { value: "newsletter", label: "Newsletter" },
  { value: "social_post", label: "Social Post" },
  { value: "product_description", label: "Product Description" },
];

const TONES = [
  { value: "professional", label: "Professional" },
  { value: "casual", label: "Casual" },
  { value: "academic", label: "Academic" },
  { value: "persuasive", label: "Persuasive" },
  { value: "humorous", label: "Humorous" },
];

export default function Dashboard() {
  const [jobs, setJobs] = useState<ContentJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [topic, setTopic] = useState("");
  const [contentType, setContentType] = useState("blog_post");
  const [tone, setTone] = useState("professional");
  const [audience, setAudience] = useState("");

  const fetchJobs = useCallback(async () => {
    try {
      const data = await listJobs();
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await createJob({
        topic: topic.trim(),
        content_type: contentType,
        tone,
        target_audience: audience || undefined,
      });
      setTopic("");
      setAudience("");
      await fetchJobs();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
    } finally {
      setSubmitting(false);
    }
  }

  const completedCount = jobs.filter((j) => j.status === "completed").length;
  const activeCount = jobs.filter(
    (j) => !["completed", "failed"].includes(j.status),
  ).length;

  return (
    <div className="page-bg">
      <Navbar active="home" />

      <main className="relative mx-auto max-w-6xl px-4 py-10 sm:px-6">
        {/* Hero */}
        <section className="animate-fade-in mb-12 text-center">
          <p className="mb-3 inline-flex items-center gap-2 rounded-full border border-brand-500/30 bg-brand-500/10 px-4 py-1.5 text-xs font-medium text-brand-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-400" />
            Multi-agent AI pipeline
          </p>
          <h1 className="font-display text-4xl font-bold tracking-tight sm:text-5xl">
            <span className="text-gradient">Create content</span>
            <br />
            <span className="text-white">that ranks &amp; converts</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-slate-400">
            Research, write, optimize, and publish — powered by a team of AI agents
            working together.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href="/briefs/new" className="btn-primary">
              Start a Content Brief
            </Link>
            <a href="#quick-create" className="btn-secondary">
              Quick Create
            </a>
          </div>
        </section>

        {/* Stats */}
        <div className="mb-10 grid grid-cols-3 gap-4 animate-slide-up">
          {[
            { label: "Total Jobs", value: jobs.length, icon: "📄" },
            { label: "In Progress", value: activeCount, icon: "⚡" },
            { label: "Completed", value: completedCount, icon: "🎉" },
          ].map((stat) => (
            <div key={stat.label} className="glass-card p-5 text-center">
              <span className="text-2xl">{stat.icon}</span>
              <p className="mt-2 font-display text-2xl font-bold text-white">{stat.value}</p>
              <p className="text-xs text-slate-500">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Agents */}
        <div className="mb-10 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {AGENTS.map((agent) => (
            <div
              key={agent.name}
              className="glass-card-hover p-4 text-center"
            >
              <span className="text-2xl">{agent.icon}</span>
              <p className="mt-2 text-sm font-semibold text-white">{agent.name}</p>
              <p className="mt-0.5 text-xs text-slate-500">{agent.desc}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-8 lg:grid-cols-5">
          {/* Quick create form */}
          <section id="quick-create" className="lg:col-span-2">
            <div className="glass-card p-6">
              <h2 className="font-display text-lg font-semibold text-white">
                Quick Create
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Simple one-step content generation
              </p>

              <form onSubmit={handleSubmit} className="mt-5 space-y-4">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">
                    Topic
                  </label>
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="e.g. The future of renewable energy"
                    className="input-field"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">
                      Type
                    </label>
                    <select
                      value={contentType}
                      onChange={(e) => setContentType(e.target.value)}
                      className="input-field"
                    >
                      {CONTENT_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-400">
                      Tone
                    </label>
                    <select
                      value={tone}
                      onChange={(e) => setTone(e.target.value)}
                      className="input-field"
                    >
                      {TONES.map((t) => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-400">
                    Audience <span className="text-slate-600">(optional)</span>
                  </label>
                  <input
                    type="text"
                    value={audience}
                    onChange={(e) => setAudience(e.target.value)}
                    placeholder="e.g. startup founders"
                    className="input-field"
                  />
                </div>

                <button type="submit" disabled={submitting} className="btn-primary w-full">
                  {submitting ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      Creating...
                    </>
                  ) : (
                    "Generate Content"
                  )}
                </button>

                {error && (
                  <p className="rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">
                    {error}
                  </p>
                )}
              </form>
            </div>
          </section>

          {/* Job list */}
          <section className="lg:col-span-3">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-display text-lg font-semibold text-white">
                Recent Jobs
              </h2>
              <span className="text-xs text-slate-500">Auto-refreshes every 5s</span>
            </div>

            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass-card h-24 animate-pulse bg-surface-700/30" />
                ))}
              </div>
            ) : jobs.length === 0 ? (
              <div className="glass-card flex flex-col items-center justify-center py-16 text-center">
                <span className="text-5xl">📝</span>
                <p className="mt-4 font-medium text-white">No content yet</p>
                <p className="mt-1 text-sm text-slate-500">
                  Create your first piece using Quick Create or a full Brief
                </p>
                <Link href="/briefs/new" className="btn-primary mt-6">
                  Create Your First Brief
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {jobs.map((job, i) => (
                  <Link
                    key={job.id}
                    href={`/jobs/${job.id}`}
                    className="glass-card-hover group block p-5 animate-slide-up"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <h3 className="truncate font-medium text-white group-hover:text-brand-300 transition-colors">
                          {job.topic}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                          {job.content_type.replace("_", " ")} · {job.tone} tone
                        </p>
                        <p className="mt-2 text-xs text-slate-600">
                          {new Date(job.created_at).toLocaleString()}
                        </p>
                      </div>
                      <StatusBadge
                        status={job.status}
                        pulse={!["completed", "failed"].includes(job.status)}
                      />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
