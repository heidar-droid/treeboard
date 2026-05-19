export function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

export function humanSize(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1048576).toFixed(1)} MB`;
}

export function relPath(absPath) {
  const root = window.__tb?.tree?.path || "";
  return root && absPath.startsWith(root)
    ? absPath.slice(root.length).replace(/^\//, "")
    : absPath;
}
