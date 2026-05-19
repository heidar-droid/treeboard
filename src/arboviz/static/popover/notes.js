export async function injectNotes(pop, node) {
  if (node.kind === "dir") return;
  const section = document.createElement("div");
  section.className = "pop-notes";
  section.innerHTML = `<div class="pop-notes-label">NOTE</div>
    <textarea class="pop-notes-input" placeholder="Add a note about this file..."></textarea>`;
  pop.appendChild(section);

  try {
    const r = await fetch("/api/notes");
    if (r.ok) {
      const notes = await r.json();
      const existing = notes[node.path] || "";
      section.querySelector(".pop-notes-input").value = existing;
    }
  } catch {}

  let _debounce = null;
  section.querySelector(".pop-notes-input").addEventListener("input", e => {
    clearTimeout(_debounce);
    _debounce = setTimeout(async () => {
      try {
        await fetch("/api/notes", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: node.path, note: e.target.value.trim() }),
        });
      } catch {}
    }, 600);
  });
}
