import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {readFileSync} from "node:fs";

const require = createRequire(import.meta.url);
const crew = require("../app/web/story-crew.js");
const css = readFileSync(new URL("../app/web/story-crew.css", import.meta.url), "utf8");

assert.equal(crew.CAST.length, 10);
assert.deepEqual(crew.CAST.map((person) => person.id), [
  "chacha", "aunty", "bunty", "dabbu", "golu", "uncle", "simran", "chintu", "ashok", "pappu",
]);
assert.equal(crew.lineFor(crew.byId("chacha"), {}), "Chai garam!");
assert.equal(crew.lineFor(crew.byId("aunty"), {}), "Hai Ram, ye kya ho raha hai!");
assert.equal(crew.lineFor(crew.byId("simran"), {}), "Ek selfie please!");
assert.equal(crew.lineFor(crew.byId("chintu"), {}), "It works on my machine");
assert.equal(crew.lineFor(crew.byId("chacha"), {"s01:say": "Cutting chai!"}), "Cutting chai!");
assert.equal(crew.V, "crew1");
assert.match(css, /steps\(6\)/);
assert.match(css, /story-crew-bob/);
assert.match(css, /scaleX\(-1\)/);
assert.match(css, /--crew-h: 70px/);
assert.match(css, /--crew-h: 55px/);
