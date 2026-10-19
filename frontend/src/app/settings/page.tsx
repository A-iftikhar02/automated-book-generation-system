"use client";

import { useMemo, useState } from "react";
import { Bell, Bot, CircleCheck, CircleX, Cpu, Database, FileCheck, Search, SpellCheck, TriangleAlert } from "lucide-react";
import { api, errorMessage, type SystemStatus } from "@/lib/api";
import { useAction, useModels, useSystemStatus } from "@/lib/hooks";
import { ageMs, fmtAgo, fmtNumber } from "@/lib/format";
import { PageHeader } from "@/components/PageHeader";
import { filterModels, ModelPrice, PROVIDER_LABELS, ProviderBadge } from "@/components/ModelPicker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

type Health = "ok" | "warn" | "off";

function StatusCard({
  icon: Icon,
  title,
  health,
  summary,
  children,
  env,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  health: Health;
  summary: string;
  children?: React.ReactNode;
  env?: string;
}) {
  const badge = {
    ok: { variant: "success" as const, icon: CircleCheck },
    warn: { variant: "warning" as const, icon: TriangleAlert },
    off: { variant: "destructive" as const, icon: CircleX },
  }[health];
  return (
    <Card className="flex flex-col p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <Icon className="h-5 w-5 text-slate-400" />
          <h2 className="font-semibold text-slate-900">{title}</h2>
        </div>
        <Badge variant={badge.variant}>
          <badge.icon className="h-3 w-3" /> {summary}
        </Badge>
      </div>
      {children && <div className="mt-3 space-y-1.5 text-sm text-slate-600">{children}</div>}
      {env && (
        <pre className="mt-auto overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-slate-900 p-3 pt-3 font-mono text-xs leading-relaxed text-slate-100 [margin-top:1rem]">
          {env}
        </pre>
      )}
    </Card>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <p className="flex flex-wrap justify-between gap-x-3">
      <span className="text-slate-500">{k}</span>
      <span className="min-w-0 break-all text-right font-mono text-xs text-slate-800">{v}</span>
    </p>
  );
}

function SlackTest() {
  const { run, busy } = useAction();
  const [result, setResult] = useState<{ sent: boolean; reason: string | null } | null>(null);
  return (
    <div className="pt-2">
      <Button size="sm" variant="outline" loading={busy} onClick={async () => setResult((await run("test", api.testNotification)) ?? null)}>
        {!busy && <Bell className="h-3.5 w-3.5" />} Send test notification
      </Button>
      {result && (
        <p role="status" className={result.sent ? "mt-2 text-xs text-green-700" : "mt-2 text-xs text-amber-800"}>
          {result.sent ? "Sent. Check your Slack channel." : result.reason || "Not sent."}
        </p>
      )}
    </div>
  );
}

function StatusGrid({ s }: { s: SystemStatus }) {
  const heartbeatAge = ageMs(s.worker.last_heartbeat);
  const workerHealth: Health = s.worker.queued_jobs > 0 && (heartbeatAge === null || heartbeatAge > 5 * 60_000) ? "warn" : "ok";
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      <StatusCard icon={Database} title="Database" health={s.database ? "ok" : "off"} summary={s.database ? "Connected" : "Down"} env={s.database ? undefined : "DATABASE_URL=postgresql+psycopg://user:pass@host:5432/bookpilot\n# then: alembic upgrade head"}>
        <Row k="API version" v={s.version} />
      </StatusCard>

      <StatusCard
        icon={Bot}
        title="AI models"
        health={s.ai.configured ? (s.ai.image_configured ? "ok" : "warn") : "off"}
        summary={s.ai.configured ? (s.ai.image_configured ? "Ready" : "Text ready · no AI covers") : "No provider for the model chains"}
        env={s.ai.configured ? undefined : "WRITER_MODELS=groq:<model>, gemini:<model>, <openrouter-model>\nEDITOR_MODELS=gemini:<model>, mistral:<model>"}
      >
        <p>Each role tries its models in order and falls back when a provider is rate-limited or out of quota. The writer is pinned per book after its first chapter so the voice stays consistent.</p>
        <Row k="Writer" v={s.ai.writer_models.join(" → ")} />
        <Row k="Editor" v={s.ai.editor_models.join(" → ")} />
        <Row k="Cover art" v={`${s.ai.image_model}${s.ai.image_configured ? "" : " (needs OpenRouter key)"}`} />
      </StatusCard>

      <StatusCard
        icon={SpellCheck}
        title="LanguageTool"
        health={s.languagetool.available ? "ok" : "warn"}
        summary={s.languagetool.available ? "Available" : "Unavailable"}
        env={s.languagetool.available ? undefined : "LANGUAGETOOL_URL=http://localhost:8010\n# docker compose up -d languagetool"}
      >
        <Row k="URL" v={s.languagetool.url} />
        {!s.languagetool.available && <p>Spelling and grammar checks are skipped until it is reachable.</p>}
      </StatusCard>

      <StatusCard
        icon={Bell}
        title="Slack notifications"
        health={s.slack.active ? "ok" : "warn"}
        summary={s.slack.active ? "Active" : s.slack.enabled ? "Missing webhook" : "Disabled"}
        env={s.slack.active ? undefined : "SLACK_ENABLED=true\nSLACK_WEBHOOK_URL=https://hooks.slack.com/services/..."}
      >
        <Row k="Enabled" v={String(s.slack.enabled)} />
        <Row k="Webhook set" v={String(s.slack.configured)} />
        <p>Notifies you when outlines and parts are ready for review, books complete, or jobs fail.</p>
        <SlackTest />
      </StatusCard>

      <StatusCard
        icon={FileCheck}
        title="epubcheck"
        health={s.epubcheck.available ? "ok" : "warn"}
        summary={s.epubcheck.available ? "Available" : "Not installed"}
        env={s.epubcheck.available ? undefined : "EPUBCHECK_JAR=/opt/epubcheck/epubcheck.jar\n# requires Java on the API host"}
      >
        <p>Validates EPUB exports the same way Apple Books does. The Docker image includes it.</p>
      </StatusCard>

      <StatusCard icon={Cpu} title="Worker" health={workerHealth} summary={workerHealth === "ok" ? "Running" : "Not picking up jobs"} env={workerHealth === "ok" ? undefined : "python -m app.worker\n# or RUN_WORKER_IN_PROCESS=true"}>
        <Row k="Mode" v={s.worker.in_process ? "in-process" : "separate process"} />
        <Row k="Last heartbeat" v={fmtAgo(s.worker.last_heartbeat)} />
        <Row k="Queued jobs" v={s.worker.queued_jobs} />
      </StatusCard>
    </div>
  );
}

function ProvidersSection({ s }: { s: SystemStatus }) {
  return (
    <section className="mt-10">
      <h2 className="text-lg font-semibold text-slate-900">AI providers</h2>
      <p className="mb-4 text-sm text-slate-500">
        Add a key to <span className="font-mono">.env</span> for every provider you want to use, then restart (<span className="font-mono">docker compose up -d</span>).
        Use the models as <span className="font-mono">provider:model</span> in <span className="font-mono">WRITER_MODELS</span> /{" "}
        <span className="font-mono">EDITOR_MODELS</span> or pick them per book.
      </p>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {s.ai.providers.map((p) => (
          <Card key={p.name} className="p-4">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold text-slate-900">{p.label}</h3>
              <Badge variant={p.configured ? "success" : "secondary"}>
                {p.configured ? (p.name === "ollama" ? "Enabled" : "Key set") : p.name === "ollama" ? "Disabled" : "No key"}
              </Badge>
            </div>
            <p className="mt-2 text-sm text-slate-600">{p.free_tier}</p>
            <p className="mt-2 font-mono text-xs text-slate-500">{p.env_var}</p>
            <a
              href={p.key_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-block text-sm font-medium text-blue-600 underline-offset-2 hover:underline"
            >
              {p.link_label} ↗
            </a>
          </Card>
        ))}
      </div>
    </section>
  );
}

function ModelBrowser() {
  const { data, error, isLoading } = useModels();
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("text");
  const [provider, setProvider] = useState("all");
  const [sort, setSort] = useState("name");
  const models = useMemo(() => data?.models || [], [data]);
  const providers = useMemo(() => Array.from(new Set(models.map((m) => m.provider))), [models]);
  const list = useMemo(() => {
    let out = filterModels(models, q);
    if (provider !== "all") out = out.filter((m) => m.provider === provider);
    if (kind === "text") out = out.filter((m) => m.output_modalities?.includes("text"));
    if (kind === "image") out = out.filter((m) => m.output_modalities?.includes("image"));
    if (kind === "free") out = out.filter((m) => m.free);
    const price = (m: (typeof out)[number]) => (m.prompt_price_per_million ?? Infinity) + (m.completion_price_per_million ?? Infinity);
    return [...out].sort((a, b) =>
      sort === "price" ? price(a) - price(b) : sort === "context" ? (b.context_length ?? 0) - (a.context_length ?? 0) : a.name.localeCompare(b.name),
    );
  }, [models, q, kind, provider, sort]);

  return (
    <section className="mt-10">
      <h2 className="text-lg font-semibold text-slate-900">Models</h2>
      <p className="mb-4 text-sm text-slate-500">
        OpenRouter&apos;s catalogue plus the live model list of every provider with a key. Copy an id into .env or pick it per book. Prices are USD per
        million tokens.
      </p>
      {data && Object.keys(data.errors).length > 0 && (
        <p className="mb-3 text-xs text-amber-700">
          Couldn&apos;t list models for: {Object.entries(data.errors).map(([p, e]) => `${PROVIDER_LABELS[p] || p} (${e.slice(0, 120)})`).join("; ")}
        </p>
      )}
      <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_auto_auto_auto]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or id" className="pl-9" aria-label="Search models" />
        </div>
        <Select value={provider} onChange={(e) => setProvider(e.target.value)} aria-label="Provider" className="sm:w-40">
          <option value="all">All providers</option>
          {providers.map((p) => (
            <option key={p} value={p}>
              {PROVIDER_LABELS[p] || p}
            </option>
          ))}
        </Select>
        <Select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Model type" className="sm:w-40">
          <option value="text">Text output</option>
          <option value="image">Image output</option>
          <option value="free">Free</option>
          <option value="all">All models</option>
        </Select>
        <Select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort models" className="sm:w-40">
          <option value="name">Sort: name</option>
          <option value="price">Sort: cheapest</option>
          <option value="context">Sort: context</option>
        </Select>
      </div>
      {isLoading ? (
        <Skeleton className="h-64" />
      ) : error ? (
        <EmptyState title="Could not load models">{errorMessage(error)}</EmptyState>
      ) : (
        <Card className="overflow-hidden">
          <p className="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">
            {list.length} of {models.length} models{list.length > 200 ? " (showing first 200)" : ""}
          </p>
          <ul className="max-h-[32rem] divide-y divide-slate-100 overflow-y-auto">
            {list.slice(0, 200).map((m) => (
              <li key={m.id} className="flex flex-col gap-1 px-4 py-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{m.name}</p>
                  <p className="truncate font-mono text-xs text-slate-500">{m.id}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1">
                  {m.context_length ? <span className="text-xs text-slate-500">{fmtNumber(Math.round(m.context_length / 1000))}k ctx</span> : null}
                  <ProviderBadge provider={m.provider} />
                  {m.output_modalities?.includes("image") && <Badge variant="purple">image</Badge>}
                  <ModelPrice m={m} />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </section>
  );
}

export default function SettingsPage() {
  const { data, error, isLoading } = useSystemStatus(15_000);
  return (
    <div>
      <PageHeader title="Settings" description="Service status and configuration. Settings live in the backend's .env file; restart the API and worker after changes." />
      {error ? (
        <EmptyState icon={CircleX} title="API unreachable">
          {errorMessage(error)}
        </EmptyState>
      ) : isLoading || !data ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44" />
          ))}
        </div>
      ) : (
        <>
          <StatusGrid s={data} />
          <ProvidersSection s={data} />
        </>
      )}
      <ModelBrowser />
    </div>
  );
}
