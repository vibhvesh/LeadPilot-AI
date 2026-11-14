import assert from "node:assert/strict";
import {createRequire} from "node:module";

const require = createRequire(import.meta.url);
const links = require("../app/web/js/deeplink.js");

const android = {ua: "Mozilla/5.0 (Linux; Android 14; Pixel 7)"};
const ios = {ua: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"};
const desktop = {ua: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0"};

const tweet = "https://x.com/ada/status/1234567890";
const desktopPlan = links.build(tweet, desktop);
assert.equal(desktopPlan.mode, "web");
assert.equal(desktopPlan.target, "_blank");
assert.equal(desktopPlan.app, "");
assert.equal(desktopPlan.https, tweet);

const androidX = links.build(tweet, android);
assert.equal(androidX.mode, "intent");
assert.equal(
  androidX.app,
  "intent://status?id=1234567890#Intent;scheme=twitter;package=com.twitter.android;S.browser_fallback_url=" + encodeURIComponent(tweet) + ";end",
);

const iosX = links.build("https://twitter.com/ada/status/42", ios);
assert.equal(iosX.mode, "scheme");
assert.equal(iosX.app, "twitter://status?id=42");
assert.equal(iosX.fallbackMs, 1500);
assert.equal(iosX.https, "https://twitter.com/ada/status/42");

const profile = links.build("https://x.com/ada", android);
assert.equal(profile.mode, "web");

const post = "https://www.linkedin.com/posts/ada_hiring-activity-99";
const androidLi = links.build(post, android);
assert.equal(androidLi.mode, "intent");
assert.match(androidLi.app, /package=com\.linkedin\.android/);
assert.match(androidLi.app, new RegExp("S\\.browser_fallback_url=" + encodeURIComponent(post).replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
const iosLi = links.build(post, ios);
assert.equal(iosLi.app, "linkedin://posts/ada_hiring-activity-99");
assert.equal(iosLi.fallbackMs, 1500);

const facebook = "https://www.facebook.com/story.php?id=7";
const fb = links.build(facebook, ios);
assert.equal(fb.app, "fb://facewebmodal/f?href=" + encodeURIComponent(facebook));
assert.equal(fb.mode, "scheme");
assert.equal(links.build(facebook, android).app, fb.app);

const dice = "https://www.dice.com/job-detail/abc";
const dicePlan = links.build(dice, android);
assert.match(dicePlan.app, /package=com\.dice\.app/);
assert.equal(dicePlan.mode, "intent");
assert.equal(links.build(dice, ios).mode, "web");
assert.equal(links.build("https://www.indeed.com/viewjob?jk=1", android).mode, "web");

const html = links.anchor(tweet, "Open on X", desktop);
assert.match(html, /target="_blank"/);
assert.match(html, /Open on X/);
const intentHtml = links.anchor(tweet, "Open on X", android);
assert.match(intentHtml, /^<a href="intent:/);
assert.doesNotMatch(intentHtml, /target=/);

console.log("deeplink ok");
