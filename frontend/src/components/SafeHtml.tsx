"use client";

import { Fragment } from "react";

const ALLOWED = new Set(["p", "b", "i", "em", "strong", "br", "ul", "ol", "li"]);

function convert(node: Node, key: number): React.ReactNode {
  if (node.nodeType === Node.TEXT_NODE) return node.textContent;
  if (node.nodeType !== Node.ELEMENT_NODE) return null;
  const tag = (node as Element).tagName.toLowerCase();
  const children = Array.from(node.childNodes).map((c, i) => convert(c, i));
  if (!ALLOWED.has(tag)) return <Fragment key={key}>{children}</Fragment>;
  if (tag === "br") return <br key={key} />;
  const Tag = tag as "p";
  return <Tag key={key}>{children}</Tag>;
}

/**
 * Preview store-description HTML without dangerouslySetInnerHTML: the markup is parsed with DOMParser
 * (which never executes scripts) and rebuilt as React elements, keeping only the tags KDP allows.
 */
export function SafeHtml({ html, className }: { html: string; className?: string }) {
  if (typeof window === "undefined") return null;
  const doc = new DOMParser().parseFromString(html, "text/html");
  return <div className={className}>{Array.from(doc.body.childNodes).map((n, i) => convert(n, i))}</div>;
}
