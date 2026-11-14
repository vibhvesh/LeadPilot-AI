import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const cast = require("../app/web/ramayana-cast.js");
const scenes = require("../app/web/ramayana-scenes.js");
const story = require("../app/web/ramayana-story.js");
const boot = require("../app/web/story-boot.js");

const list = scenes.list();
assert.equal(list.length, 55);
assert.deepEqual(list.map((scene) => scene.id), Array.from({length: 55}, (_, index) => `s${String(index + 1).padStart(2, "0")}`));
list.forEach((scene) => {
  assert.ok(scene.duration >= 6000 && scene.duration <= 12000);
  assert.match(scene.caption, /^Narayan Narayan/);
});

const gags = list.map((scene, index) => (scene.gag ? index : -1)).filter((index) => index >= 0);
assert.ok(gags.length >= 11);
for (let i = 1; i < gags.length; i += 1) {
  const gap = gags[i] - gags[i - 1];
  assert.ok(gap >= 3 && gap <= 5, `gag gap ${gap}`);
}
gags.forEach((index) => {
  assert.ok(list[index].lines["rocket-boss"]);
  assert.ok(list[index].lines["old-man-boss"]);
  assert.match(list[index].lines.chase, /Old Man Boss/);
});
assert.match(list[gags[0]].lines["rocket-boss"], /gada/i);
assert.match(list[gags[0]].lines["old-man-boss"], /plan/i);

const blob = list.map((scene) => `${scene.title} ${scene.caption} ${Object.values(scene.lines).join(" ")}`).join("\n").toLowerCase();
["ayodhya", "vishwamitra", "tadaka", "shiva", "swayamvar", "kaikeyi", "exile", "bharata", "paduka", "panchavati", "surpanakha", "golden deer", "lakshman rekha", "jatayu", "shabari", "hanuman", "sugriva", "vali", "search", "leap", "ashok", "ring", "setu", "vibhishana", "angad", "kumbhakarna", "indrajit", "sanjeevani", "pushpak", "diwali", "ram rajya"].forEach((word) => {
  assert.ok(blob.includes(word), word);
});
assert.equal(blob.includes("elon"), false);

["rama", "lakshmana", "sita", "hanuman", "jambavan", "sugriva", "vibhishana", "ravana", "kumbhakarna", "narad", "rocket-boss", "old-man-boss"].forEach((id) => {
  const markup = cast.svg(id);
  assert.match(markup, new RegExp(`/static/story/${id}\\.png\\?v=`));
  assert.match(markup, /<img/);
  assert.equal(/elon|cigar/i.test(markup), false);
});
assert.match(cast.svg("hanuman"), /story-hanuman-sprite/);
for (let team = 1; team <= 8; team += 1) assert.match(cast.svg(`team-${team}`), new RegExp(`/static/story/team-${team}\\.png`));
assert.equal(cast.name("old-man-boss"), "Old Man Boss");
assert.equal(boot.STORY_V, "crew1");
assert.ok(cast.STORY_V);

const sample = list[0];
const visits = list.map((scene, index) => (scene.blessing ? index : -1)).filter((index) => index >= 0);
assert.equal(visits[0], 0);
assert.equal(visits[visits.length - 1], 54);
for (let i = 1; i < visits.length; i += 1) {
  const gap = visits[i] - visits[i - 1];
  assert.ok(gap >= 8 && gap <= 10, `valmiki gap ${gap}`);
}
assert.ok(list[0].lines.valmiki);
assert.ok(list[54].lines.valmiki);
assert.match(list[0].lines.valmiki, /Valmiki/);
const sage = cast.svg("valmiki");
["valmiki-beard", "valmiki-topknot", "valmiki-hair", "valmiki-dhoti", "valmiki-shawl", "valmiki-beads", "valmiki-tilak", "valmiki-staff", "valmiki-palm", "valmiki-smile", "valmiki-hand"].forEach((token) => {
  assert.match(sage, new RegExp(token));
});
assert.equal(/elon|musk/i.test(sage), false);
assert.equal(cast.name("valmiki"), "Maharishi Valmiki");
assert.equal(story.textFor(list[0], "valmiki", {"s01:valmiki": "Aashirvad, beta."}), "Aashirvad, beta.");

assert.equal(story.textFor(sample, "narad", {}), sample.caption);
assert.equal(story.textFor(sample, "narad", {"s01:narad": "Edited line"}), "Edited line");
assert.equal(boot.IDLE_MS, 120000);
