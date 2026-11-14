import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
require("../app/web/mascot-fun.js");
require("../app/web/mascot-ramayana.js");
require("../app/web/mascot-mahabharata.js");
require("../app/web/mascot-roster.js");
const characters = require("../app/web/mascot-characters.js");
const idle = require("../app/web/mascot-idle.js");

const roster = ["hanuman", "rama", "lakshmana", "sita", "jambavan", "krishna", "arjuna", "bhima", "narad", "rocket-boss"];
const props = {
  rama: "rama-bow",
  lakshmana: "lakshmana-bow",
  sita: "sita-lotus",
  jambavan: "jambavan-club",
  krishna: "krishna-flute",
  arjuna: "arjuna-bow",
  bhima: "bhima-mace",
  narad: "narad-veena",
};

const list = characters.list();
const ids = list.map((item) => item.id);
assert.deepEqual(ids, roster);
assert.equal(list.length, 10);
assert.equal(list.find((item) => item.id === "narad").group, "ramayana");
assert.match(list.find((item) => item.id === "narad").svg, /narad-topknot/);
assert.match(characters.quip("narad", {kind: "generic", facts: {}}, () => 0), /Narayan Narayan/);
assert.deepEqual(characters.GROUPS.map((group) => group.id), ["classic", "ramayana", "mahabharata", "fun"]);
const boss = list.find((item) => item.id === "rocket-boss");
assert.equal(boss.group, "fun");
assert.equal(boss.idleMs, 10000);
assert.match(boss.svg, /rocket-shirt/);
assert.match(boss.svg, /rocket-badge/);
assert.match(boss.svg, /rocket-ship/);
assert.match(boss.svg, /mascot-leg-left/);
assert.match(boss.svg, /mascot-leg-right/);
assert.match(characters.quip("rocket-boss", {kind: "lead-top", facts: {company: "Pad", score: 9}}, () => 0), /Shipping it|Mars|rocket/i);

for (const [id, prop] of Object.entries(props)) {
  const item = characters.byId(id);
  assert.ok(item, id);
  assert.match(item.svg, new RegExp(prop));
  const line = characters.quip(id, {kind: "followup-overdue", facts: {count: 2}}, () => 0);
  assert.ok(line.length > 8, id);
  assert.doesNotMatch(line, /@|stupid|idiot|hate religion/i);
}

assert.equal(characters.next(ids[ids.length - 1]).id, "hanuman");
const polite = characters.quip("mango", {kind: "lead-quiet", tone: "polite", facts: {}}, () => 0);
assert.doesNotMatch(polite, /SQUAWK/);
const cheeky = characters.quip("mango", {kind: "lead-quiet", facts: {}}, () => 0);
assert.match(cheeky, /SQUAWK/);

assert.equal(idle.MOUSE_IDLE_MS, 2600);
idle.setMouseIdle(1500);
assert.equal(idle.mouseIdle(), 1500);
idle.setMouseIdle(500);
assert.equal(idle.mouseIdle(), 1500);
idle.setMouseIdle(10000);
assert.equal(idle.mouseIdle(), 10000);
assert.equal(idle.dockPoint(112, 140, 800, 600).left, 676);
assert.equal(idle.dockPoint(112, 140, 800, 600, "left").left, 12);

console.log("mascot cast ok");
