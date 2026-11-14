import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const crew = require("../app/web/mascot-crew.js");

const opts = {chosen: "krishna", cap: 4, startMs: 60000, stepMs: 60000, roster: crew.ROSTER};
assert.deepEqual(crew.crewIds(59000, opts), []);
assert.deepEqual(crew.crewIds(60000, opts), ["krishna"]);
assert.equal(crew.crewIds(120000, opts).length, 2);
assert.equal(crew.crewIds(120000, opts)[0], "krishna");
assert.equal(crew.crewIds(600000, opts).length, 4);
assert.equal(crew.crewIds(600000, Object.assign({}, opts, {cap: 10})).length, 10);

const two = crew.crewIds(120000, opts);
assert.deepEqual(crew.withBoss(two, 120000, 300000), two);
const round = crew.withBoss(two, 300000, 300000);
assert.equal(round[round.length - 1], "rocket-boss");
assert.equal(crew.offer(false), "A cigar and a beer?");
assert.equal(crew.offer(true), "Chai and a laddoo?");
assert.match(crew.reply("hanuman", false), /pass|mace/i);
assert.match(crew.reply("rama", false), /No, thank you/);
assert.match(crew.reply("narad", false), /Narayan Narayan/);
assert.match(crew.reply("krishna", false), /Cheers/);
assert.match(crew.reply("narad", true), /laddoo/);
assert.match(crew.tip("leads"), /lead/i);

console.log("mascot crew ok");
