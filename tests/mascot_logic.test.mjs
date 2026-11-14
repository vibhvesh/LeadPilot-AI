import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const characters = require("../app/web/mascot-characters.js");
const insights = require("../app/web/mascot-insights.js");
const idle = require("../app/web/mascot-idle.js");

const cast = ["hanuman", "mango", "noodle", "pickle", "biscuit"];
const banned = /\b(stupid|idiot|dumb|lazy|ugly|hate|moron|jerk)\b|shut up/i;

function quip(id, insight) {
  return characters.quip(id, insight, () => 0);
}

const leads = insights.choose({
  page: "leads",
  leads: [
    {id: 9, score: 99, status: "Contacted", company: "Already Called", contact_name: "Priya", email: "priya@example.com"},
    {id: 5, score: 50, status: "New", company: "Newer Co", contact_name: "Sam"},
    {id: 4, score: 88, status: "New", company: "Northwind", email: "hidden@example.com"},
    {id: 3, score: 10, status: "New", company: "Quiet Co"},
  ],
});
assert.equal(leads.kind, "lead-top");
assert.equal(leads.facts.company, "Northwind");
assert.equal(leads.facts.score, "88");
assert.equal(leads.selector, '#lead-rows tr[data-preview-lead="4"]');
assert.equal(leads.facts.contact_name, undefined);
assert.equal(leads.facts.email, undefined);
assert.doesNotMatch(JSON.stringify(leads.facts), /Priya|@/);

const tied = insights.choose({
  page: "leads",
  leads: [
    {id: 8, score: 50, status: "New", company: "Newer Tie"},
    {id: 2, score: 50, status: "New", company: "Older Tie"},
  ],
});
assert.equal(tied.facts.company, "Newer Tie");

const unscored = insights.choose({
  page: "leads",
  leads: [
    {id: 7, score: null, status: "New", company: "Fresh Co"},
    {id: 6, score: null, status: "New", company: "Older Co"},
  ],
});
assert.equal(unscored.kind, "lead-new");
assert.equal(unscored.selector, '#lead-rows tr[data-preview-lead="7"]');

const emailCompany = insights.choose({
  page: "leads",
  leads: [{id: 1, score: 10, status: "New", company: "Pat <pat@example.com>"}],
});
assert.equal(emailCompany.facts.company, "A new lead");
assert.doesNotMatch(quip("hanuman", emailCompany), /@/);

assert.equal(insights.choose({page: "leads", leads: []}).kind, "lead-empty");
assert.equal(insights.choose({
  page: "leads",
  leads: [{id: 1, score: 5, status: "Contacted", company: "Done"}],
}).kind, "lead-quiet");

const lines = cast.map((id) => quip(id, leads));
assert.equal(new Set(lines).size, cast.length);
for (const line of lines) {
  assert.match(line, /Northwind/);
  assert.match(line, /88/);
  assert.match(line, /new lead/);
  assert.doesNotMatch(line, banned);
  assert.doesNotMatch(line, /@/);
}

const now = Date.parse("2026-11-14T00:00:00Z");
const followups = insights.choose({
  page: "followups",
  now,
  followups: [
    {id: 3, status: "done", due: "2026-10-01T00:00:00Z"},
    {id: 2, status: "open", due: "2026-11-20T00:00:00Z"},
    {id: 1, status: "open", due: "2026-11-01T00:00:00Z"},
    {id: 4, status: "open", due: "2026-11-10T00:00:00Z"},
  ],
});
assert.equal(followups.kind, "followup-overdue");
assert.equal(followups.facts.count, 2);
assert.equal(followups.selector, '#fu-list [data-fu-id="1"]');
const one = quip("hanuman", {kind: "followup-overdue", facts: {count: 1}});
const two = quip("hanuman", {kind: "followup-overdue", facts: {count: 2}});
assert.match(one, /^1 follow-up overdue/);
assert.doesNotMatch(one, /follow-ups/);
assert.match(two, /^2 follow-ups overdue/);

const pipeline = insights.choose({
  page: "pipeline",
  pipeline: [
    {status: "New", count: 1},
    {status: "Contacted", count: 4},
    {status: "Qualified", count: 0},
    {status: "Won", count: 2},
    {status: "Lost", count: 9},
  ],
});
assert.equal(pipeline.kind, "pipeline-stalled");
assert.equal(pipeline.facts.status, "Contacted");
assert.equal(pipeline.facts.count, 4);
assert.equal(pipeline.selector, '#pipeline-board [data-status="Contacted"]');

const tiedStages = insights.choose({
  page: "pipeline",
  pipeline: [
    {status: "New", count: 3},
    {status: "Contacted", count: 3},
  ],
});
assert.equal(tiedStages.facts.status, "New");

assert.equal(insights.choose({
  page: "reports",
  reports: [
    {label: "Leads this month", value: "0"},
    {label: "Conversion", value: "0.0%"},
  ],
}).facts.label, "Leads this month");

assert.equal(insights.choose({
  page: "reports",
  reports: [
    {label: "Leads this month", value: "6"},
    {label: "Conversion", value: "12.5%"},
  ],
}).facts.label, "Conversion");

const keys = insights.choose({
  page: "apis",
  keys: [
    {provider: "xai", configured: false},
    {provider: "gemini", configured: false},
    {provider: "openai", configured: false},
    {provider: "tavily", configured: true},
    {provider: "brave", configured: false},
  ],
});
assert.equal(keys.kind, "apis-missing");
assert.match(keys.facts.providers, /xAI/);
assert.match(keys.facts.providers, /Gemini/);
assert.match(keys.facts.providers, /OpenAI/);
assert.equal(keys.selector, '#key-rows tr[data-provider="xai"]');

const searchGap = insights.choose({
  page: "apis",
  keys: [
    {provider: "xai", configured: true},
    {provider: "gemini", configured: false},
    {provider: "openai", configured: false},
    {provider: "tavily", configured: false},
    {provider: "brave", configured: false},
  ],
});
assert.match(searchGap.facts.providers, /Tavily/);
assert.equal(searchGap.selector, '#key-rows tr[data-provider="tavily"]');
assert.equal(insights.choose({
  page: "apis",
  keys: [
    {provider: "xai", configured: true},
    {provider: "tavily", configured: true},
  ],
}).kind, "apis-ok");

assert.equal(insights.choose({page: "team", pendingUsers: 2, teamCount: 4}).kind, "team-pending");
assert.match(quip("biscuit", insights.choose({page: "users", users: [{status: "pending"}, {status: "approved"}]})), /waiting for access/);
assert.equal(insights.choose({page: "ai", aiMissing: true}).kind, "ai-missing");
assert.equal(insights.choose({page: "search", searchMissing: true, savedSearches: 3}).kind, "search-missing");
assert.equal(insights.choose({page: "geo", geoCountry: ""}).kind, "geo-empty");
assert.equal(insights.choose({page: "geo", geoCountry: "India"}).facts.country, "India");
assert.equal(insights.choose({page: "overview", overview: {total: 0, banner: true}}).kind, "overview-start");
assert.equal(insights.choose({
  page: "overview",
  overview: {total: 4, followupsOpen: 3, recent: []},
}).kind, "overview-followups");
assert.equal(insights.choose({
  page: "overview",
  overview: {
    total: 4,
    followupsOpen: 3,
    warnings: [{level: "alert", label: "Overdue follow-ups", count: 2, selector: "#lamp-overdue"}],
  },
}).kind, "cockpit-alert");
assert.match(quip("hanuman", insights.choose({
  page: "overview",
  overview: {warnings: [{level: "alert", label: "Overdue follow-ups", count: 2, selector: "#lamp-overdue"}]},
})), /Cockpit warning/);
assert.equal(insights.choose({
  page: "overview",
  overview: {
    total: 4,
    followupsOpen: 3,
    warnings: [{level: "warn", label: "No LLM key", count: 0, selector: "#lamp-llm"}],
  },
}).kind, "overview-followups");
assert.equal(insights.choose({
  page: "overview",
  overview: {
    total: 4,
    followupsOpen: 0,
    recent: [],
    warnings: [{level: "warn", label: "No search key", count: 0, selector: "#lamp-search"}],
  },
}).kind, "cockpit-caution");
assert.equal(insights.choose({
  page: "leads",
  previewOpen: true,
  leads: [{id: 1, score: 9, status: "New", company: "Ignored"}],
}).kind, "preview");
assert.match(quip("hanuman", {kind: "preview", facts: {}}), /Here's the summary!/);
assert.equal(insights.choose({page: "social", social: {reply: 2, engage: 1}}).kind, "social-reply");
assert.equal(insights.choose({page: "social", social: {reply: 0, engage: 0}}).kind, "social-clear");
assert.equal(insights.choose({page: "pulse", pulse: {urgent: 1, week: 3}}).facts.count, 1);
assert.equal(insights.choose({page: "pulse", pulse: {urgent: 0, week: 2}}).kind, "pulse-week");
assert.match(quip("mango", insights.choose({page: "pulse", pulse: {urgent: 2, week: 0}})), /urgent/i);

const kinds = cast.flatMap((id) => [
  quip(id, leads),
  quip(id, followups),
  quip(id, pipeline),
  quip(id, {kind: "report-metric", facts: {label: "Conversion", value: "12%"}}),
  quip(id, {kind: "users-pending", facts: {count: 2}}),
  quip(id, {kind: "apis-missing", facts: {providers: "xAI"}}),
  quip(id, {kind: "ai-missing", facts: {}}),
  quip(id, {kind: "generic", facts: {}}),
  quip(id, {kind: "team-roster", facts: {count: 3}}),
  quip(id, {kind: "settings-profile", facts: {}}),
]);
for (const line of kinds) {
  assert.doesNotMatch(line, banned);
  assert.doesNotMatch(line, /@/);
  assert.ok(line.length > 8);
}

assert.deepEqual(characters.list().map((item) => item.id), ["hanuman"]);
assert.equal(characters.next("biscuit").id, "hanuman");
assert.equal(characters.byId("mango").pose, "wink");
assert.match(characters.byId("hanuman").svg, /hanuman-crown/);
assert.match(characters.byId("hanuman").svg, /hanuman-gada/);
assert.match(characters.byId("hanuman").svg, /hanuman-tail/);
assert.match(characters.byId("hanuman").svg, /hanuman-tilak/);

assert.ok(idle.MOUSE_IDLE_MS >= 2000 && idle.MOUSE_IDLE_MS <= 3000);
assert.ok(idle.TOUCH_IDLE_MS >= 6000);
assert.equal(idle.prefersTouch({pointerType: "touch"}), true);
assert.equal(idle.prefersTouch({coarse: true, hover: false}), true);
assert.equal(idle.prefersTouch({coarse: true, hover: true}), false);
assert.equal(idle.movementDismisses({idle: true, overMascot: true, distance: 80}), false);
assert.equal(idle.movementDismisses({idle: true, towardMascot: true, distance: 80}), false);
assert.equal(idle.movementDismisses({idle: true, distance: idle.DISMISS_PX - 1}), false);
assert.equal(idle.movementDismisses({idle: true, distance: idle.DISMISS_PX}), true);
assert.equal(idle.isMovingToward({x: 100, y: 100}, {x: 80, y: 100}, {x: 40, y: 100}), true);
assert.equal(idle.isMovingToward({x: 100, y: 100}, {x: 140, y: 100}, {x: 40, y: 100}), false);

const near = idle.anchorNear(400, 300, 112, 140, 800, 600);
assert.ok(near.left < 400 && near.top < 300);
assert.equal(near.flip, false);
const corner = idle.anchorNear(10, 10, 112, 140, 800, 600);
assert.ok(corner.left >= 8 && corner.top >= 8);
assert.equal(corner.flip, true);
assert.equal(corner.below, true);
const dock = idle.dockPoint(112, 140, 800, 600);
assert.equal(dock.left, 676);
assert.equal(dock.top, 448);

console.log("mascot logic ok");
