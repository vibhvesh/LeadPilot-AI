/* Picks the single most useful thing already on the page. No new services, no contact names. */
(function (root) {
  const OPEN_STAGES = ["New", "Contacted", "Qualified"];
  const LLM_KEYS = ["xai", "gemini", "openai"];
  const SEARCH_KEYS = ["tavily", "brave"];
  const PROVIDER_LABELS = {xai: "xAI", gemini: "Gemini", openai: "OpenAI", tavily: "Tavily", brave: "Brave"};

  function safeLabel(value, fallback) {
    const clean = String(value || "").replace(/[\u0000-\u001f<>{}]/g, "").replace(/\s+/g, " ").trim().slice(0, 48);
    if (!clean || clean.indexOf("@") !== -1) return fallback == null ? "A lead" : fallback;
    return clean;
  }

  function attr(value) {
    return String(value == null ? "" : value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
  }

  function scoreOf(lead) {
    if (!lead || lead.score == null || lead.score === "") return null;
    const number = Number(lead.score);
    return Number.isFinite(number) ? number : null;
  }

  function leadChoice(leads) {
    const rows = leads || [];
    const fresh = rows.filter(function (lead) { return lead.status === "New"; });
    if (!fresh.length) return rows.length ? {kind: "lead-quiet"} : null;
    const scored = fresh.filter(function (lead) { return scoreOf(lead) != null; });
    if (scored.length) {
      const best = Math.max.apply(null, scored.map(scoreOf));
      const pick = scored.filter(function (lead) { return scoreOf(lead) === best; })[0];
      return {
        kind: "lead-top",
        id: pick.id,
        facts: {company: safeLabel(pick.company, "A new lead"), score: String(best)},
      };
    }
    return {
      kind: "lead-new",
      id: fresh[0].id,
      facts: {company: safeLabel(fresh[0].company, "A new lead"), scorePhrase: ""},
    };
  }

  function rowSelector(prefix, id) {
    return prefix + ' tr[data-preview-lead="' + attr(id) + '"]';
  }

  function leadsInsight(snap) {
    const choice = leadChoice(snap.leads || []);
    if (!choice) return {kind: "lead-empty", selector: "#lead-rows", facts: {}};
    if (choice.kind === "lead-quiet") return {kind: "lead-quiet", selector: "#lead-rows", facts: {}};
    return {kind: choice.kind, selector: rowSelector("#lead-rows", choice.id), facts: choice.facts};
  }

  function followInsight(snap) {
    const now = snap.now || Date.now();
    const rows = snap.followups || [];
    const open = rows.filter(function (row) { return row.status === "open"; });
    const overdue = open.filter(function (row) {
      const due = Date.parse(row.due || "");
      return Number.isFinite(due) && due < now;
    }).sort(function (a, b) { return Date.parse(a.due) - Date.parse(b.due); });
    if (overdue.length) {
      return {
        kind: "followup-overdue",
        selector: '#fu-list [data-fu-id="' + attr(overdue[0].id) + '"]',
        facts: {count: overdue.length},
      };
    }
    if (open.length) {
      return {
        kind: "followup-open",
        selector: '#fu-list [data-fu-id="' + attr(open[0].id) + '"]',
        facts: {count: open.length},
      };
    }
    return {kind: "followup-clear", selector: "#fu-list", facts: {}};
  }

  function pipelineInsight(snap) {
    const columns = snap.pipeline || [];
    let stalled = null;
    OPEN_STAGES.forEach(function (status) {
      const column = columns.filter(function (item) { return item.status === status; })[0];
      const count = column ? Number(column.count) || 0 : 0;
      if (!stalled || count > stalled.count) stalled = {status: status, count: count};
    });
    if (stalled && stalled.count > 0) {
      return {
        kind: "pipeline-stalled",
        selector: '#pipeline-board [data-status="' + attr(stalled.status) + '"]',
        facts: {status: stalled.status, count: stalled.count},
      };
    }
    const won = columns.filter(function (item) { return item.status === "Won"; })[0];
    if (won && Number(won.count) > 0) {
      return {kind: "pipeline-won", selector: '#pipeline-board [data-status="Won"]', facts: {count: Number(won.count)}};
    }
    return {kind: "pipeline-empty", selector: "#pipeline-board", facts: {}};
  }

  function reportInsight(snap) {
    const cards = snap.reports || [];
    if (!cards.length) return {kind: "report-empty", selector: "#report-stats", facts: {}};
    const byLabel = {};
    cards.forEach(function (card) { byLabel[card.label] = card; });
    const leads = byLabel["Leads this month"];
    const conversion = byLabel.Conversion;
    const leadCount = leads ? Number(String(leads.value).replace(/[^\d.]/g, "")) : 0;
    const pick = leads && leadCount === 0 ? leads : (conversion || leads || cards[0]);
    return {
      kind: "report-metric",
      selector: '#report-stats [data-report="' + attr(pick.label) + '"]',
      facts: {label: pick.label, value: pick.value},
    };
  }

  function teamInsight(snap) {
    const pending = Number(snap.pendingUsers) || 0;
    if (pending > 0) return {kind: "team-pending", selector: '[data-tab="users"]', facts: {count: pending}};
    const count = Number(snap.teamCount) || 0;
    if (!count) return {kind: "team-empty", selector: "#team-list", facts: {}};
    return {kind: "team-roster", selector: "#team-list", facts: {count: count}};
  }

  function skipped(snap, key) {
    if (snap.restricted && snap.restricted[key]) {
      return {kind: "generic", selector: "section.page.active h1", facts: {}};
    }
    return null;
  }

  function usersInsight(snap) {
    const quiet = skipped(snap, "users");
    if (quiet) return quiet;
    const rows = snap.users || [];
    const pending = rows.filter(function (user) { return user.status === "pending"; }).length || Number(snap.pendingUsers) || 0;
    if (pending > 0) {
      return {kind: "users-pending", selector: '#user-rows tr[data-account-status="pending"]', facts: {count: pending}};
    }
    return {kind: "users-clear", selector: "#user-rows", facts: {count: rows.length}};
  }

  function providerList(keys) {
    return keys.map(function (key) { return PROVIDER_LABELS[key.provider] || key.provider; }).join(", ");
  }

  function apisInsight(snap) {
    const quiet = skipped(snap, "apis");
    if (quiet) return quiet;
    const keys = snap.keys || [];
    const missing = keys.filter(function (key) { return !key.configured; });
    const missingLlm = missing.filter(function (key) { return LLM_KEYS.indexOf(key.provider) !== -1; });
    const missingSearch = missing.filter(function (key) { return SEARCH_KEYS.indexOf(key.provider) !== -1; });
    const llmPresent = LLM_KEYS.some(function (name) {
      return keys.some(function (key) { return key.provider === name && key.configured; });
    });
    const searchPresent = SEARCH_KEYS.some(function (name) {
      return keys.some(function (key) { return key.provider === name && key.configured; });
    });
    if (!llmPresent && missingLlm.length) {
      return {kind: "apis-missing", selector: '#key-rows tr[data-provider="' + attr(missingLlm[0].provider) + '"]', facts: {providers: providerList(missingLlm)}};
    }
    if (!searchPresent && missingSearch.length) {
      return {kind: "apis-missing", selector: '#key-rows tr[data-provider="' + attr(missingSearch[0].provider) + '"]', facts: {providers: providerList(missingSearch)}};
    }
    if (missing.length) {
      return {kind: "apis-missing", selector: '#key-rows tr[data-provider="' + attr(missing[0].provider) + '"]', facts: {providers: providerList(missing)}};
    }
    return {kind: "apis-ok", selector: "#key-rows", facts: {}};
  }

  function cockpitWarning(warnings, level) {
    const pick = (warnings || []).filter(function (item) { return item && item.level === level; })[0];
    if (!pick) return null;
    return {
      kind: level === "alert" ? "cockpit-alert" : "cockpit-caution",
      selector: pick.selector || "#cockpit",
      facts: {label: pick.label || "Cockpit warning", count: Number(pick.count) || 0},
    };
  }

  function overviewInsight(snap) {
    const overview = snap.overview || {};
    const warnings = overview.warnings || [];
    const alert = cockpitWarning(warnings, "alert");
    if (alert) return alert;
    if (overview.banner || Number(overview.total) === 0) {
      return {kind: "overview-start", selector: "#start-banner", facts: {}};
    }
    if (Number(overview.followupsOpen) > 0) {
      return {kind: "overview-followups", selector: "#m-follow", facts: {count: Number(overview.followupsOpen)}};
    }
    const choice = leadChoice(overview.recent || []);
    if (choice && choice.id != null) {
      const phrase = choice.facts.score ? " (" + choice.facts.score + ")" : "";
      return {
        kind: "overview-lead",
        selector: rowSelector("#recent-leads", choice.id),
        facts: {company: choice.facts.company, scorePhrase: phrase},
      };
    }
    const caution = cockpitWarning(warnings, "warn");
    if (caution) return caution;
    return {kind: "overview-quiet", selector: "#m-total", facts: {count: Number(overview.total) || 0}};
  }

  const HANDLERS = {
    overview: overviewInsight,
    leads: leadsInsight,
    followups: followInsight,
    pipeline: pipelineInsight,
    reports: reportInsight,
    team: teamInsight,
    users: usersInsight,
    apis: apisInsight,
    ai: function (snap) {
      if (snap.aiMissing) return {kind: "ai-missing", selector: "#ai-primary", facts: {}};
      return {kind: "ai-ready", selector: "#ai-effective", facts: {}};
    },
    search: function (snap) {
      if (snap.searchMissing) return {kind: "search-missing", selector: "#search-provider-status", facts: {}};
      if (!Number(snap.savedSearches)) return {kind: "search-empty", selector: "#s-name", facts: {}};
      return {kind: "search-ready", selector: "#s-list", facts: {count: Number(snap.savedSearches)}};
    },
    geo: function (snap) {
      const country = safeLabel(snap.geoCountry, "");
      if (!country) return {kind: "geo-empty", selector: "#g-country", facts: {}};
      return {kind: "geo-set", selector: "#g-country", facts: {country: country}};
    },
    grokbot: function (snap) {
      if (snap.grokMissing) return {kind: "grok-missing", selector: "#agent-provider-status", facts: {}};
      if (!snap.grokLead) return {kind: "grok-idle", selector: "#agent-lead", facts: {}};
      return {kind: "grok-ready", selector: "#agent-run", facts: {}};
    },
    bots: function (snap) {
      const bots = snap.bots || [];
      const pending = bots.filter(function (bot) { return bot.status === "pending"; });
      if (pending.length) return {kind: "bots-pending", selector: '#bot-connections [data-bot-status="pending"]', facts: {count: pending.length}};
      const unread = bots.reduce(function (sum, bot) { return sum + (Number(bot.unread) || 0); }, 0);
      if (unread) return {kind: "bots-unread", selector: "#bots-badge", facts: {count: unread}};
      return {kind: "bots-clear", selector: "#bot-connections", facts: {count: bots.length}};
    },
    settings: function (snap) {
      const quiet = skipped(snap, "settings");
      if (quiet) return quiet;
      const settings = snap.settings || {};
      if (!safeLabel(settings.seller, "") || !safeLabel(settings.offering, "")) {
        const selector = safeLabel(settings.seller, "") ? "#set-offering" : "#set-seller";
        return {kind: "settings-profile", selector: selector, facts: {}};
      }
      return {kind: "settings-ready", selector: "#set-info", facts: {}};
    },
    activity: function (snap) {
      const quiet = skipped(snap, "activity");
      if (quiet) return quiet;
      const rows = snap.activity || [];
      const failed = rows.filter(function (row) { return row.label === "Failed" && Number(row.value) > 0; })[0];
      if (failed) return {kind: "activity-failed", selector: '#activity-stats [data-activity="Failed"]', facts: {count: Number(failed.value)}};
      const today = rows.filter(function (row) { return row.label === "Activities today"; })[0];
      if (today) return {kind: "activity-today", selector: '#activity-stats [data-activity="Activities today"]', facts: {count: Number(today.value) || 0}};
      return {kind: "activity-today", selector: "#activity-stats", facts: {count: 0}};
    },
    updates: function (snap) {
      if (snap.commentsEmpty) return {kind: "comments-empty", selector: "#comment-body", facts: {}};
      return {kind: "comments-ready", selector: "#comment-list", facts: {}};
    },
    social: function (snap) {
      const social = snap.social || {};
      if (Number(social.reply) > 0) {
        return {kind: "social-reply", selector: "#social-feed .social-reply", facts: {count: Number(social.reply)}};
      }
      if (Number(social.engage) > 0) {
        return {kind: "social-engage", selector: "#social-feed .social-engage", facts: {count: Number(social.engage)}};
      }
      return {kind: "social-clear", selector: "#social-counts", facts: {}};
    },
    pulse: function (snap) {
      const pulse = snap.pulse || {};
      if (Number(pulse.urgent) > 0) {
        return {kind: "pulse-urgent", selector: "#pulse-feed .pulse-urgent", facts: {count: Number(pulse.urgent)}};
      }
      if (Number(pulse.week) > 0) {
        return {kind: "pulse-week", selector: "#pulse-feed .pulse-week", facts: {count: Number(pulse.week)}};
      }
      return {kind: "pulse-clear", selector: "#pulse-counts", facts: {}};
    },
  };

  function choose(snapshot) {
    try {
      const snap = snapshot || {};
      if (snap.previewOpen) return {kind: "preview", selector: "#lead-preview .preview-panel", facts: {}};
      const handler = HANDLERS[snap.page] || HANDLERS.overview;
      const insight = handler(snap);
      if (!insight || !insight.kind) return {kind: "generic", selector: "section.page.active h1", facts: {}};
      return insight;
    } catch (error) {
      return {kind: "generic", selector: "section.page.active h1", facts: {}};
    }
  }

  function tabBlocked(doc, tab) {
    const button = doc.querySelector('.tab[data-tab="' + tab + '"]');
    return !!(button && button.hidden);
  }

  function shownText(el) {
    if (!el || el.hidden) return "";
    return String(el.textContent || "").trim();
  }

  function valueOf(el) {
    return el && el.value ? String(el.value).trim() : "";
  }

  function readLeads(doc, selector) {
    return Array.prototype.map.call(doc.querySelectorAll(selector), function (row) {
      return {
        id: row.getAttribute("data-preview-lead"),
        score: row.getAttribute("data-score"),
        status: row.getAttribute("data-status") || "",
        company: row.getAttribute("data-company") || "",
      };
    });
  }

  function countLine(text, patterns) {
    const counts = {};
    Object.keys(patterns).forEach(function (key) {
      const match = String(text || "").match(patterns[key]);
      counts[key] = match ? Number(match[1]) || 0 : 0;
    });
    return counts;
  }

  function read(doc, now) {
    const pageEl = doc.querySelector("section.page.active");
    const badge = doc.getElementById("pending-badge");
    const follow = shownText(doc.getElementById("m-follow"));
    const followMatch = follow.match(/(\d+)/);
    const banner = doc.getElementById("start-banner");
    const aiStatus = shownText(doc.getElementById("ai-provider-status"));
    const aiNote = shownText(doc.getElementById("ai-effective"));
    const searchStatus = shownText(doc.getElementById("search-provider-status"));
    const grokStatus = shownText(doc.getElementById("agent-provider-status"));
    const agentLead = doc.getElementById("agent-lead");
    return {
      page: pageEl ? pageEl.id : "overview",
      restricted: {
        users: tabBlocked(doc, "users"),
        apis: tabBlocked(doc, "apis"),
        activity: tabBlocked(doc, "activity"),
        settings: tabBlocked(doc, "settings"),
      },
      now: now || Date.now(),
      previewOpen: !!(doc.getElementById("lead-preview") && !doc.getElementById("lead-preview").hidden),
      pendingUsers: badge && !badge.hidden ? Number(badge.textContent) || 0 : 0,
      leads: readLeads(doc, "#lead-rows tr[data-preview-lead]"),
      followups: Array.prototype.map.call(doc.querySelectorAll("#fu-list [data-fu-id]"), function (row) {
        return {id: row.getAttribute("data-fu-id"), status: row.getAttribute("data-fu-status") || "", due: row.getAttribute("data-due") || ""};
      }),
      pipeline: Array.prototype.map.call(doc.querySelectorAll("#pipeline-board [data-status]"), function (col) {
        const count = col.querySelector("h3 span");
        return {status: col.getAttribute("data-status"), count: count ? Number(count.textContent) || 0 : 0};
      }),
      reports: Array.prototype.map.call(doc.querySelectorAll("#report-stats [data-report]"), function (card) {
        const num = card.querySelector(".num");
        return {label: card.getAttribute("data-report"), value: num ? num.textContent.trim() : ""};
      }),
      teamCount: doc.querySelectorAll("#team-list .item").length,
      users: Array.prototype.map.call(doc.querySelectorAll("#user-rows tr[data-account-status]"), function (row) {
        return {status: row.getAttribute("data-account-status") || ""};
      }),
      keys: Array.prototype.map.call(doc.querySelectorAll("#key-rows tr[data-provider]"), function (row) {
        return {provider: row.getAttribute("data-provider"), configured: row.getAttribute("data-configured") === "true"};
      }),
      aiMissing: aiStatus.indexOf("No LLM") !== -1 || aiNote.indexOf("No LLM") !== -1,
      searchMissing: searchStatus.indexOf("No search") !== -1,
      savedSearches: doc.querySelectorAll("#s-list .item").length,
      geoCountry: valueOf(doc.getElementById("g-country")),
      grokMissing: grokStatus.indexOf("No LLM") !== -1,
      grokLead: !!(agentLead && agentLead.value),
      bots: Array.prototype.map.call(doc.querySelectorAll("#bot-connections [data-bot-status]"), function (row) {
        return {status: row.getAttribute("data-bot-status") || "", unread: Number(row.getAttribute("data-bot-unread")) || 0};
      }),
      settings: {
        seller: valueOf(doc.getElementById("set-seller")),
        offering: valueOf(doc.getElementById("set-offering")),
      },
      activity: Array.prototype.map.call(doc.querySelectorAll("#activity-stats [data-activity]"), function (card) {
        const num = card.querySelector(".num");
        return {label: card.getAttribute("data-activity"), value: num ? Number(String(num.textContent).replace(/[^\d.-]/g, "")) || 0 : 0};
      }),
      commentsEmpty: shownText(doc.getElementById("comment-list")).indexOf("No updates yet") !== -1,
      social: countLine(shownText(doc.getElementById("social-counts")), {reply: /(\d+)\s+to reply/i, engage: /(\d+)\s+to engage/i}),
      pulse: countLine(shownText(doc.getElementById("pulse-counts")), {urgent: /(\d+)\s+urgent/i, week: /(\d+)\s+this week/i}),
      overview: {
        followupsOpen: followMatch ? Number(followMatch[1]) : 0,
        banner: !!(banner && !banner.hidden),
        total: Number(shownText(doc.getElementById("m-total")).replace(/[^\d.-]/g, "")) || 0,
        recent: readLeads(doc, "#recent-leads tr[data-preview-lead]"),
        warnings: Array.prototype.map.call(doc.querySelectorAll("#overview [data-cockpit-level]"), function (el) {
          const level = el.getAttribute("data-cockpit-level");
          if ((level !== "alert" && level !== "warn") || !el.id) return null;
          return {
            level: level,
            label: safeLabel(el.getAttribute("data-cockpit-label"), "Cockpit warning"),
            count: Number(el.getAttribute("data-cockpit-count")) || 0,
            selector: "#" + el.id,
          };
        }).filter(Boolean),
      },
    };
  }

  const api = {choose: choose, read: read, safeLabel: safeLabel};
  root.MascotInsights = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
