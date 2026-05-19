import { test } from "node:test";
import assert from "node:assert/strict";
import { SIZES, STATE_ORDER, sizeFor, nextState, snapToState } from "../../../src/arboviz/static/popover/sizes.js";

test("SIZES defines all five named states with width and height", () => {
  for (const name of ["chip", "compact", "standard", "expanded", "full"]) {
    assert.ok(SIZES[name], `SIZES.${name} should exist`);
    assert.equal(typeof SIZES[name].w, "number");
    assert.equal(typeof SIZES[name].h, "number");
  }
});

test("STATE_ORDER is the canonical cycle order excluding chip", () => {
  assert.deepEqual(STATE_ORDER, ["compact", "standard", "expanded", "full"]);
});

test("sizeFor returns size for a known state", () => {
  assert.deepEqual(sizeFor("standard"), SIZES.standard);
});

test("nextState cycles through STATE_ORDER and wraps", () => {
  assert.equal(nextState("compact"), "standard");
  assert.equal(nextState("standard"), "expanded");
  assert.equal(nextState("expanded"), "full");
  assert.equal(nextState("full"), "compact");
});

test("snapToState returns the named state when within 12px of its width AND height", () => {
  const s = SIZES.standard;
  assert.equal(snapToState(s.w + 5, s.h - 3), "standard");
  assert.equal(snapToState(s.w + 11, s.h + 11), "standard");
  assert.equal(snapToState(s.w + 13, s.h), null, "outside threshold returns null");
});

test("snapToState returns null when between named states", () => {
  const between = (SIZES.standard.w + SIZES.expanded.w) / 2;
  const h = (SIZES.standard.h + SIZES.expanded.h) / 2;
  assert.equal(snapToState(between, h), null);
});
