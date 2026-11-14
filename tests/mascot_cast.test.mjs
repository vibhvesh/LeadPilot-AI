import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
require("../app/web/mascot-ramayana.js");
require("../app/web/mascot-mahabharata.js");
const characters = require("../app/web/mascot-characters.js");
const idle = require("../app/web/mascot-idle.js");

const ramayana = ["rama", "lakshmana", "sita", "jambavan", "jatayu", "sugriva", "vibhishana", "ravana"];
const mahabharata = ["krishna", "arjuna", "bhima", "karna", "draupadi", "bhishma", "shakuni", "ghatotkacha"];
const props = {
  rama: "rama-bow",
  lakshmana: "lakshmana-bow",
  sita: "sita-lotus",
  jambavan: "jambavan-club",
  jatayu: "jatayu-wing",
  sugriva: "sugriva-crown",
  vibhishana: "vibhishana-banner",
  ravana: "ravana-heads",
  krishna: "krishna-flute",
  arjuna: "arjuna-bow",
  bhima: "bhima-mace",
  karna: "karna-armor",
  draupadi: "draupadi-flame",
  bhishma: "bhishma-bow",
  shakuni: "shakuni-dice",
  ghatotkacha: "ghatotkacha-club",
};

const list = characters.list();
const ids = list.map((item) => item.id);
assert.deepEqual(ids.slice(0, 5), ["hanuman", "mango", "noodle", "pickle", "biscuit"]);
for (const id of ramayana) assert.equal(list.find((item) => item.id === id).group, "ramayana");
for (const id of mahabharata) assert.equal(list.find((item) => item.id === id).group, "mahabharata");
assert.deepEqual(characters.GROUPS.map((group) => group.id), ["classic", "ramayana", "mahabharata"]);

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
