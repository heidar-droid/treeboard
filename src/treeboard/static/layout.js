// Top-down hierarchical layout: assigns each node an (x, y) and width/height.
// Pills are uniform-height; horizontal positions are derived from subtree widths
// so siblings don't overlap.

const NODE_H = 22;
const FILE_H = 18;
const SIBLING_GAP = 14;
const LEVEL_GAP = 90;
const PILL_PAD_X = 14;

function _measure(label, isRoot) {
  // approximate width: characters × 6.6 + padding. Renderer will refine if needed.
  const w = Math.max(58, Math.ceil(label.length * 6.6) + PILL_PAD_X * 2);
  return { w, h: isRoot ? 22 : (isRoot === false ? FILE_H : NODE_H) };
}

export function layout(tree, { collapsed = new Set() } = {}) {
  // Recursive subtree-width computation, then position resolution.
  function compute(node, depth) {
    const isRoot = depth === 0;
    const kind = node.kind === "dir" ? "fold" : "file";
    const { w, h } = _measure(node.name, isRoot ? true : (kind === "file" ? false : null));
    node.__w = w;
    node.__h = h;
    node.__depth = depth;
    node.__kind = isRoot ? "root" : kind;

    const isCollapsed = collapsed.has(node.path);
    if (kind === "fold" && !isCollapsed && node.children && node.children.length) {
      let totalChildWidth = 0;
      for (const c of node.children) {
        compute(c, depth + 1);
        totalChildWidth += c.__subtreeW;
      }
      totalChildWidth += SIBLING_GAP * (node.children.length - 1);
      node.__subtreeW = Math.max(w, totalChildWidth);
    } else {
      node.__subtreeW = w;
    }
  }

  function place(node, cx, y) {
    node.__cx = cx;
    node.__cy = y;
    node.__x = cx - node.__w / 2;
    node.__y = y;
    const isCollapsed = collapsed.has(node.path);
    if (node.__kind !== "fold" || isCollapsed || !node.children || node.children.length === 0) {
      return;
    }
    const childY = y + node.__h + LEVEL_GAP;
    const totalW = node.children.reduce(
      (acc, c, i) => acc + c.__subtreeW + (i > 0 ? SIBLING_GAP : 0),
      0,
    );
    let cursor = cx - totalW / 2;
    for (const c of node.children) {
      const childCx = cursor + c.__subtreeW / 2;
      place(c, childCx, childY);
      cursor += c.__subtreeW + SIBLING_GAP;
    }
  }

  compute(tree, 0);
  place(tree, 0, 0);

  // Collect everything for the renderer
  const all = [];
  const edges = [];
  function collect(node, parent) {
    all.push(node);
    if (parent) edges.push({ from: parent, to: node });
    const isCollapsed = collapsed.has(node.path);
    if (node.__kind === "fold" && !isCollapsed) {
      for (const c of node.children || []) collect(c, node);
    }
  }
  collect(tree, null);

  // Compute overall bounds
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const n of all) {
    if (n.__x < minX) minX = n.__x;
    if (n.__y < minY) minY = n.__y;
    if (n.__x + n.__w > maxX) maxX = n.__x + n.__w;
    if (n.__y + n.__h > maxY) maxY = n.__y + n.__h;
  }
  return { nodes: all, edges, bounds: { minX, minY, maxX, maxY } };
}

export function nodeBoundingBox(node) {
  return { x: node.__x, y: node.__y, w: node.__w, h: node.__h };
}

export function subtreeBoundingBox(node) {
  let minX = node.__x, minY = node.__y;
  let maxX = node.__x + node.__w, maxY = node.__y + node.__h;
  function visit(n) {
    if (!n.children) return;
    for (const c of n.children) {
      if (c.__x === undefined) continue;
      if (c.__x < minX) minX = c.__x;
      if (c.__y < minY) minY = c.__y;
      if (c.__x + c.__w > maxX) maxX = c.__x + c.__w;
      if (c.__y + c.__h > maxY) maxY = c.__y + c.__h;
      visit(c);
    }
  }
  visit(node);
  return { x: minX, y: minY, w: maxX - minX, h: maxY - minY };
}
