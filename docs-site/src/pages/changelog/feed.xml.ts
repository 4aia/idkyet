// RSS-2.0-Feed des Changelogs (/changelog/feed.xml). Dependency-frei
// handgeschrieben (wie llms.txt.ts): export GET -> Response (application/rss+xml).
// Single Source ist src/data/changelog.ts. Prosa mit echten Umlauten, keine
// Em-Dashes, keine Emojis. XML-Sonderzeichen werden escaped.
import type { APIRoute } from "astro";
import { changelog, KIND_LABEL } from "../../data/changelog";

function siteBase(site: URL | undefined): string {
  return (site?.toString() ?? "https://infranode.dev").replace(/\/$/, "");
}

function esc(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// Stabile, ASCII-reine guid je Eintrag (Datum + slugifizierter Titel), damit
// Feed-Reader neue Einträge zuverlässig erkennen, auch wenn zwei am selben Tag.
function slug(s: string): string {
  return s
    .toLowerCase()
    .replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "")
    .slice(0, 60);
}

export const GET: APIRoute = async ({ site }) => {
  const base = siteBase(site);
  const pageUrl = `${base}/changelog/`;
  const selfUrl = `${base}/changelog/feed.xml`;
  const entries = [...changelog].sort((a, b) => b.date.localeCompare(a.date));
  const lastBuild = entries.length
    ? new Date(entries[0].date + "T00:00:00Z").toUTCString()
    : new Date().toUTCString();

  const items = entries
    .map((e) => {
      const title = `[${KIND_LABEL[e.kind].de}] ${e.de.title}`;
      const guid = `infranode-changelog-${e.date}-${slug(e.de.title)}`;
      const pubDate = new Date(e.date + "T00:00:00Z").toUTCString();
      return [
        "    <item>",
        `      <title>${esc(title)}</title>`,
        `      <link>${esc(pageUrl)}</link>`,
        `      <guid isPermaLink="false">${esc(guid)}</guid>`,
        `      <pubDate>${pubDate}</pubDate>`,
        `      <description>${esc(e.de.body)}</description>`,
        "    </item>",
      ].join("\n");
    })
    .join("\n");

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    "  <channel>",
    "    <title>InfraNode Changelog</title>",
    `    <link>${esc(pageUrl)}</link>`,
    "    <description>Neue Datenquellen, neue Städte, Verhaltensänderungen und Abkündigungen der InfraNode-API.</description>",
    "    <language>de</language>",
    `    <lastBuildDate>${lastBuild}</lastBuildDate>`,
    `    <atom:link href="${esc(selfUrl)}" rel="self" type="application/rss+xml" />`,
    items,
    "  </channel>",
    "</rss>",
    "",
  ].join("\n");

  return new Response(xml, {
    headers: { "Content-Type": "application/rss+xml; charset=utf-8" },
  });
};
