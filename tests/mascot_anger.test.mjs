import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const anger = require("../app/web/mascot-anger.js");

const tracker = anger.createTracker({windowMs: 500, need: 3, cooldownMs: 10000});
assert.deepEqual(tracker(0), {fired: false, ignored: false});
assert.deepEqual(tracker(120), {fired: false, ignored: false});
assert.deepEqual(tracker(240), {fired: true, ignored: false});
assert.deepEqual(tracker(300), {fired: false, ignored: true});
assert.deepEqual(tracker(10300), {fired: false, ignored: false});

const spaced = anger.createTracker({windowMs: 400, need: 3, cooldownMs: 10000});
assert.equal(spaced(0).fired, false);
assert.equal(spaced(100).fired, false);
assert.equal(spaced(900).fired, false);
assert.equal(spaced(1000).fired, false);

assert.match(anger.leaveLine("hanuman"), /Sanjeevani/);
assert.equal(anger.leaveLine("rocket-boss"), "I'm going to Mars. Bye.");
assert.match(anger.leaveLine("mango"), /Enough poking/);
assert.match(anger.returnLine("rocket-boss"), /Reentry/);
assert.equal(anger.COOLDOWN_MS, 10000);

console.log("mascot anger ok");
