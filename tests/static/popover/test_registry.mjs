import { test } from "node:test";
import assert from "node:assert/strict";
import { createRegistry } from "../../../src/treeboard/static/popover/registry.js";

test("register returns a PopoverModel with id, node, state, and rect", () => {
  const reg = createRegistry();
  const node = { path: "/a/b.ts", kind: "file" };
  const m = reg.register(node, { state: "compact", rect: { x: 10, y: 20, w: 240, h: 140 } });
  assert.ok(m.id);
  assert.equal(m.node, node);
  assert.equal(m.state, "compact");
  assert.deepEqual(m.rect, { x: 10, y: 20, w: 240, h: 140 });
});

test("get returns the model by id", () => {
  const reg = createRegistry();
  const m = reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.equal(reg.get(m.id), m);
});

test("unregister removes the model and returns true", () => {
  const reg = createRegistry();
  const m = reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.equal(reg.unregister(m.id), true);
  assert.equal(reg.get(m.id), undefined);
});

test("unregister returns false for unknown id", () => {
  const reg = createRegistry();
  assert.equal(reg.unregister("nope"), false);
});

test("all() returns models in insertion order", () => {
  const reg = createRegistry();
  const a = reg.register({ path: "/a" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  const b = reg.register({ path: "/b" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  assert.deepEqual(reg.all().map(m => m.id), [a.id, b.id]);
});

test("findByPath returns the first model for the given path", () => {
  const reg = createRegistry();
  reg.register({ path: "/x" }, { state: "compact", rect: { x: 0, y: 0, w: 240, h: 140 } });
  const m = reg.findByPath("/x");
  assert.ok(m);
  assert.equal(m.node.path, "/x");
});
