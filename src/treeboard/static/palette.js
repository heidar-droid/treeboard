function fuzzyScore(query, name) {
  if (!query) return 1;
  query = query.toLowerCase();
  name = name.toLowerCase();
  let qi = 0, score = 0, gap = 0;
  for (let i = 0; i < name.length && qi < query.length; i++) {
    if (name[i] === query[qi]) {
      score += 10 - Math.min(8, gap);
      gap = 0; qi++;
    } else gap++;
  }
  if (qi < query.length) return 0;
  if (name.startsWith(query)) score += 30;
  return score;
}

export function setupPalette(tree, openFile, zoomToNode) {
  const wrap = document.createElement("div");
  wrap.className = "palette";
  wrap.innerHTML = `<input type="text" placeholder="Find a file…" /><div class="results"></div>`;
  document.body.appendChild(wrap);
  const input = wrap.querySelector("input");
  const results = wrap.querySelector(".results");

  const flat = [];
  function flatten(n) {
    flat.push(n);
    (n.children || []).forEach(flatten);
  }
  flatten(tree);

  let sel = 0;
  let current = [];

  function render(query) {
    if (!query) { current = []; results.innerHTML = ""; sel = 0; return; }
    current = flat
      .filter(n => n.kind === "file")
      .map(n => ({ n, s: fuzzyScore(query, n.name) }))
      .filter(x => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 40)
      .map(x => x.n);
    results.innerHTML = current.map((n, i) => `
      <div class="row ${i === sel ? "sel" : ""}" data-i="${i}">
        <span class="name">${n.name}</span>
        <span class="path">${n.path}</span>
      </div>`).join("");
  }

  function open() {
    wrap.classList.add("open");
    input.value = "";
    sel = 0; current = [];
    results.innerHTML = "";
    setTimeout(() => input.focus(), 0);
  }
  function close() { wrap.classList.remove("open"); }
  function commit() {
    if (!current.length) return;
    const node = current[sel];
    close();
    zoomToNode(node);
    setTimeout(() => openFile(node), 620);
  }

  input.addEventListener("input", () => render(input.value));
  input.addEventListener("keydown", e => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(current.length - 1, sel + 1); render(input.value); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); render(input.value); }
    else if (e.key === "Enter") { e.preventDefault(); commit(); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  });
  results.addEventListener("click", e => {
    const row = e.target.closest(".row");
    if (!row) return;
    sel = +row.dataset.i;
    commit();
  });
  window.addEventListener("keydown", e => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); open(); }
  });
  document.addEventListener("click", e => {
    if (!wrap.contains(e.target)) close();
  });

  return { open, close };
}
