// RSS-2.0-Feed des Changelogs, englische Fassung (/en/changelog/feed.xml).
// Dependency-frei handgeschrieben, Single Source src/data/changelog.ts.
import type { APIRoute } from "astro";
import { changelog, KIND_LABEL } from "../../../data/changelog";

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
  const pageUrl = `${base}/en/changelog/`;
  const selfUrl = `${base}/en/changelog/feed.xml`;
  const entries = [...changelog].sort((a, b) => b.date.localeCompare(a.date));
  const lastBuild = entries.length
    ? new Date(entries[0].date + "T00:00:00Z").toUTCString()
    : new Date().toUTCString();

  const items = entries
    .map((e) => {
      const title = `[${KIND_LABEL[e.kind].en}] ${e.en.title}`;
      const guid = `infranode-changelog-en-${e.date}-${slug(e.en.title)}`;
      const pubDate = new Date(e.date + "T00:00:00Z").toUTCString();
      return [
        "    <item>",
        `      <title>${esc(title)}</title>`,
        `      <link>${esc(pageUrl)}</link>`,
        `      <guid isPermaLink="false">${esc(guid)}</guid>`,
        `      <pubDate>${pubDate}</pubDate>`,
        `      <description>${esc(e.en.body)}</description>`,
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
    "    <description>New data sources, new cities, behaviour changes and deprecations of the InfraNode API.</description>",
    "    <language>en</language>",
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
