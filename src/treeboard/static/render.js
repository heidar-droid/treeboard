const SVG_NS = "http://www.w3.org/2000/svg";

function bezier(a, b) {
  const ax = a.__cx, ay = a.__y + a.__h;
  const bx = b.__cx, by = b.__y;
  const my = (ay + by) / 2;
  return `M${ax} ${ay} C ${ax} ${my}, ${bx} ${my}, ${bx} ${by}`;
}

export function renderBoard({ nodes, edges }, board, { collapsed, emptyFolders }) {
  const edgesG = board.querySelector("#edges");
  const nodesG = board.querySelector("#nodes");
  // wipe & rebuild — simpler than diffing for v1
  edgesG.innerHTML = "";
  nodesG.innerHTML = "";

  // edges — base then pulse overlay
  let edgeIdx = 0;
  for (const { from, to } of edges) {
    const d = bezier(from, to);
    const base = document.createElementNS(SVG_NS, "path");
    base.setAttribute("class", "edge-base");
    base.setAttribute("d", d);
    base.setAttribute("data-edge", `${from.path}->${to.path}`);
    edgesG.appendChild(base);

    const pulse = document.createElementNS(SVG_NS, "path");
    pulse.setAttribute("class", "edge-pulse");
    pulse.setAttribute("d", d);
    pulse.setAttribute("data-edge", `${from.path}->${to.path}`);
    pulse.style.animationDelay = `-${(edgeIdx * 0.3) % 3.2}s`;
    edgesG.appendChild(pulse);
    edgeIdx++;
  }

  // nodes
  for (const n of nodes) {
    const kind = n.__kind; // 'root' | 'fold' | 'file'
    const g = document.createElementNS(SVG_NS, "g");
    g.setAttribute("class", "node");
    g.setAttribute("data-path", n.path);
    g.setAttribute("data-kind", kind);

    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("class", classFor(kind, n, collapsed, emptyFolders));
    rect.setAttribute("x", n.__x);
    rect.setAttribute("y", n.__y);
    rect.setAttribute("width", n.__w);
    rect.setAttribute("height", n.__h);
    rect.setAttribute("rx", n.__h / 2);
    g.appendChild(rect);

    const txt = document.createElementNS(SVG_NS, "text");
    txt.setAttribute("class", `lbl ${kind}-lbl`);
    txt.setAttribute("x", n.__cx);
    txt.setAttribute("y", n.__y + n.__h / 2 + (kind === "root" ? 4 : 3.4));
    txt.setAttribute("text-anchor", "middle");
    txt.textContent = n.name;
    g.appendChild(txt);
    nodesG.appendChild(g);
  }
}

function classFor(kind, n, collapsed, emptyFolders) {
  if (kind === "root") return "pill root-fill";
  if (kind === "fold") {
    let cls = "pill fold-stroke";
    if (collapsed.has(n.path)) cls += " collapsed";
    if (emptyFolders.has(n.path)) cls += " empty";
    return cls;
  }
  return "pill file-stroke";
}

export function flagEmptyFolders(tree) {
  const empty = new Set();
  function visit(node) {
    if (node.kind === "dir") {
      if (!node.children || node.children.length === 0) {
        empty.add(node.path);
      } else {
        node.children.forEach(visit);
      }
    }
  }
  visit(tree);
  return empty;
}
