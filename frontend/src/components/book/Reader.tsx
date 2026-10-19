import { Fragment } from "react";
import { cn } from "@/lib/utils";

const SCENE_BREAK_RE = /^\s*(\*\s*\*\s*\*|#|~+|\*{3,}|-{3,}|•\s*•\s*•)\s*$/;
const ITALIC_RE = /(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])/g;

/** Render `*italic*` markup as <em> without injecting HTML. */
export function Inline({ text }: { text: string }) {
  const out: React.ReactNode[] = [];
  let pos = 0;
  for (const m of text.matchAll(ITALIC_RE)) {
    const i = m.index ?? 0;
    if (i > pos) out.push(text.slice(pos, i));
    out.push(<em key={i}>{m[1]}</em>);
    pos = i + m[0].length;
  }
  if (pos < text.length) out.push(text.slice(pos));
  return <>{out}</>;
}

type Block = { kind: "para" | "verse" | "break"; text: string; first?: boolean };

export function toBlocks(content: string, verse: boolean): Block[] {
  const paras = content
    .replace(/\r\n/g, "\n")
    .trim()
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
  const blocks: Block[] = [];
  let first = true;
  for (const p of paras) {
    if (SCENE_BREAK_RE.test(p)) {
      if (blocks.length && blocks[blocks.length - 1].kind !== "break") blocks.push({ kind: "break", text: "" });
      first = true;
      continue;
    }
    const clean = p.replace(/^#{1,6}\s+/, "").replace(/\*\*([\s\S]+?)\*\*/g, "$1");
    blocks.push(verse ? { kind: "verse", text: clean, first } : { kind: "para", text: clean.replace(/\s*\n\s*/g, " "), first });
    first = false;
  }
  while (blocks.length && blocks[blocks.length - 1].kind === "break") blocks.pop();
  return blocks;
}

/** Book-style reader view for a part's plain-text content. */
export function Reader({ content, verse = false, className }: { content: string; verse?: boolean; className?: string }) {
  const blocks = toBlocks(content, verse);
  return (
    <div className={cn("mx-auto max-w-[65ch] font-serif text-[1.05rem] leading-8 text-slate-800", className)}>
      {blocks.map((b, i) => {
        if (b.kind === "break") {
          return (
            <p key={i} className="my-6 text-center tracking-[0.5em] text-slate-400" aria-label="Scene break">
              * * *
            </p>
          );
        }
        if (b.kind === "verse") {
          return (
            <p key={i} className="mb-5 whitespace-normal">
              {b.text.split("\n").map((line, j) => (
                <Fragment key={j}>
                  {j > 0 && <br />}
                  <Inline text={line} />
                </Fragment>
              ))}
            </p>
          );
        }
        return (
          <p key={i} className={cn("mb-2", !b.first && "indent-8")}>
            <Inline text={b.text} />
          </p>
        );
      })}
      {!blocks.length && <p className="text-center italic text-slate-400">This part is empty.</p>}
    </div>
  );
}
