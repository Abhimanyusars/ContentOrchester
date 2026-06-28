"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { createBrief, type ContentBrief } from "@/lib/brief-api";

const STEPS = [
  { num: 1, title: "Content Basics", desc: "Topic, type & length" },
  { num: 2, title: "SEO & Audience", desc: "Keywords & targeting" },
  { num: 3, title: "Review", desc: "Confirm & launch" },
];

const CONTENT_TYPES = [
  { value: "blog", label: "Blog Post", icon: "📝" },
  { value: "linkedin", label: "LinkedIn Post", icon: "💼" },
  { value: "email", label: "Email Newsletter", icon: "📧" },
  { value: "product_description", label: "Product Description", icon: "🛍️" },
];

const TONES = [
  { value: "professional", label: "Professional" },
  { value: "conversational", label: "Conversational" },
  { value: "authoritative", label: "Authoritative" },
  { value: "friendly", label: "Friendly" },
];

export default function NewBriefPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [topic, setTopic] = useState("");
  const [contentType, setContentType] = useState("blog");
  const [targetLength, setTargetLength] = useState(800);
  const [keywords, setKeywords] = useState<string[]>([]);
  const [keywordInput, setKeywordInput] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [brandVoice, setBrandVoice] = useState("professional");

  function addKeyword() {
    const kw = keywordInput.trim();
    if (kw && !keywords.includes(kw)) {
      setKeywords([...keywords, kw]);
      setKeywordInput("");
    }
  }

  function handleKeywordKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      addKeyword();
    }
  }

  function validateStep(s: number): string | null {
    if (s === 1 && !topic.trim()) return "Topic is required";
    if (s === 2 && !targetAudience.trim()) return "Target audience is required";
    return null;
  }

  function nextStep() {
    const err = validateStep(step);
    if (err) { setError(err); return; }
    setError(null);
    setStep((s) => Math.min(3, s + 1));
  }

  function prevStep() {
    setError(null);
    setStep((s) => Math.max(1, s - 1));
  }

  async function handleSubmit() {
    const err = validateStep(2);
    if (err) { setError(err); return; }
    setSubmitting(true);
    setError(null);
    try {
      const brief: ContentBrief = {
        topic: topic.trim(),
        keywords,
        target_audience: targetAudience.trim(),
        brand_voice: brandVoice,
        content_type: contentType,
        target_length: targetLength,
      };
      const result = await createBrief(brief);
      router.push(`/briefs/${result.task_id}/status`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit brief");
      setSubmitting(false);
    }
  }

  return (
    <div className="page-bg">
      <Navbar active="briefs" />

      <main className="relative mx-auto max-w-2xl px-4 py-10 sm:px-6">
        <div className="animate-fade-in text-center">
          <h1 className="font-display text-3xl font-bold text-white">
            Create Content Brief
          </h1>
          <p className="mt-2 text-slate-400">
            Tell our AI agents what to create — they handle the rest
          </p>
        </div>

        {/* Step indicator */}
        <div className="mt-10 flex items-center justify-between">
          {STEPS.map((s, i) => (
            <div key={s.num} className="flex flex-1 items-center">
              <div className="flex flex-col items-center">
                <div
                  className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold transition-all ${
                    step > s.num
                      ? "bg-emerald-500 text-white"
                      : step === s.num
                      ? "bg-brand-500 text-white shadow-lg shadow-brand-500/40"
                      : "bg-surface-700 text-slate-500"
                  }`}
                >
                  {step > s.num ? "✓" : s.num}
                </div>
                <p className={`mt-2 hidden text-xs font-medium sm:block ${
                  step >= s.num ? "text-white" : "text-slate-600"
                }`}>
                  {s.title}
                </p>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={`mx-2 h-0.5 flex-1 rounded transition-colors ${
                    step > s.num ? "bg-emerald-500" : "bg-surface-700"
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <div className="glass-card mt-8 animate-slide-up p-6 sm:p-8">
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="font-display text-xl font-semibold text-white">
                  Content Basics
                </h2>
                <p className="mt-1 text-sm text-slate-500">{STEPS[0].desc}</p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-400">
                  Topic *
                </label>
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. The future of renewable energy"
                  className="input-field"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-400">
                  Content Type
                </label>
                <div className="grid grid-cols-2 gap-3">
                  {CONTENT_TYPES.map((t) => (
                    <button
                      key={t.value}
                      type="button"
                      onClick={() => setContentType(t.value)}
                      className={`flex items-center gap-3 rounded-xl border p-3 text-left text-sm transition-all ${
                        contentType === t.value
                          ? "border-brand-500/50 bg-brand-500/10 text-white"
                          : "border-white/10 bg-surface-700/30 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      <span className="text-xl">{t.icon}</span>
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center justify-between">
                  <label className="text-sm font-medium text-slate-400">
                    Target Length
                  </label>
                  <span className="rounded-lg bg-brand-500/20 px-3 py-1 text-sm font-semibold text-brand-300">
                    {targetLength} words
                  </span>
                </div>
                <input
                  type="range"
                  min={300}
                  max={3000}
                  step={100}
                  value={targetLength}
                  onChange={(e) => setTargetLength(Number(e.target.value))}
                  className="w-full accent-brand-500"
                />
                <div className="mt-1 flex justify-between text-xs text-slate-600">
                  <span>300</span>
                  <span>3000</span>
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-6">
              <div>
                <h2 className="font-display text-xl font-semibold text-white">
                  SEO &amp; Audience
                </h2>
                <p className="mt-1 text-sm text-slate-500">{STEPS[1].desc}</p>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-400">
                  Keywords <span className="text-slate-600">(press Enter)</span>
                </label>
                <input
                  type="text"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={handleKeywordKeyDown}
                  placeholder="e.g. solar energy, sustainability"
                  className="input-field"
                />
                {keywords.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {keywords.map((kw) => (
                      <span
                        key={kw}
                        className="inline-flex items-center gap-1.5 rounded-full bg-brand-500/15 px-3 py-1 text-sm text-brand-300"
                      >
                        {kw}
                        <button
                          type="button"
                          onClick={() => setKeywords(keywords.filter((k) => k !== kw))}
                          className="text-brand-400 hover:text-white"
                        >
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-slate-400">
                  Target Audience *
                </label>
                <textarea
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. Startup founders interested in sustainability and clean tech"
                  rows={3}
                  className="input-field resize-none"
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-400">
                  Brand Voice
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {TONES.map((t) => (
                    <button
                      key={t.value}
                      type="button"
                      onClick={() => setBrandVoice(t.value)}
                      className={`rounded-xl border px-4 py-2.5 text-sm font-medium transition-all ${
                        brandVoice === t.value
                          ? "border-brand-500/50 bg-brand-500/10 text-white"
                          : "border-white/10 text-slate-400 hover:border-white/20"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-6">
              <div>
                <h2 className="font-display text-xl font-semibold text-white">
                  Review &amp; Launch
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Confirm your brief before our agents get to work
                </p>
              </div>

              <div className="space-y-3 rounded-xl bg-surface-700/30 p-5">
                {[
                  { label: "Topic", value: topic },
                  { label: "Type", value: contentType.replace("_", " ") },
                  { label: "Length", value: `${targetLength} words` },
                  { label: "Keywords", value: keywords.join(", ") || "None" },
                  { label: "Audience", value: targetAudience },
                  { label: "Voice", value: brandVoice },
                ].map((row) => (
                  <div
                    key={row.label}
                    className="flex justify-between gap-4 border-b border-white/5 pb-3 last:border-0 last:pb-0"
                  >
                    <span className="shrink-0 text-sm text-slate-500">{row.label}</span>
                    <span className="text-right text-sm font-medium capitalize text-white">
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>

              <div className="rounded-xl border border-brand-500/20 bg-brand-500/5 p-4">
                <p className="text-sm text-brand-200">
                  🚀 Your content will go through Research → Write → SEO → Human Review → Publish
                </p>
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 rounded-lg bg-red-500/10 px-3 py-2 text-sm text-red-400">
              {error}
            </p>
          )}

          <div className="mt-8 flex justify-between">
            {step > 1 ? (
              <button type="button" onClick={prevStep} className="btn-secondary">
                ← Back
              </button>
            ) : (
              <Link href="/" className="btn-secondary">Cancel</Link>
            )}

            {step < 3 ? (
              <button type="button" onClick={nextStep} className="btn-primary">
                Continue →
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary"
              >
                {submitting ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Launching...
                  </>
                ) : (
                  "🚀 Generate Content"
                )}
              </button>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
