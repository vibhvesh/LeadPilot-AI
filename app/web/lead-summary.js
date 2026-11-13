/* Report-style summary shown at the top of a lead detail. */
(function () {
  function esc(value) {
    return window.LeadPilot.esc(value);
  }

  function text(value) {
    return String(value ?? "").trim();
  }

  function missing() {
    return `<span class="summary-missing">Not listed</span>`;
  }

  function phoneHref(phone) {
    const digits = text(phone).replace(/[^\d+]/g, "");
    return digits ? "tel:" + digits : "";
  }

  function emailOk(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }

  function when(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return text(value);
    return date.toLocaleString(undefined, {dateStyle: "medium", timeStyle: "short"});
  }

  function roles(keywords) {
    return text(keywords).split(/[,;]+/).map((part) => part.trim()).filter(Boolean);
  }

  function linkRow(label, href, value) {
    if (!text(value) || !href) return `<div class="summary-row"><span>${esc(label)}</span>${missing()}</div>`;
    return `<div class="summary-row"><span>${esc(label)}</span><a href="${esc(href)}">${esc(value)}</a></div>`;
  }

  function fact(label, value) {
    const shown = text(value);
    return `<div class="summary-row"><span>${esc(label)}</span>${shown ? `<b>${esc(shown)}</b>` : missing()}</div>`;
  }

  function render(lead) {
    const company = text(lead.company) || "Untitled lead";
    const place = text(lead.region) || [lead.city, lead.state, lead.country].map(text).filter(Boolean).join(", ");
    const industry = text(lead.industry);
    const status = text(lead.status) || "New";
    const phone = text(lead.phone);
    const email = text(lead.email);
    const person = text(lead.contact_name);
    const signal = text(lead.why_fit) || text(lead.qualification_summary);
    const roleList = roles(lead.keywords);
    const notes = text(lead.notes);
    const sourceUrl = text(lead.source_url);
    const website = text(lead.website);
    const chips = roleList.map((role) => `<span class="summary-chip">${esc(role)}</span>`).join("");
    const extra = [
      lead.company_size ? fact("Company size", lead.company_size) : "",
      lead.postal_code ? fact("PIN / ZIP", lead.postal_code) : "",
      lead.district ? fact("District", lead.district) : "",
      Number(lead.estimated_value) > 0 ? fact("Estimated value", Number(lead.estimated_value).toLocaleString()) : "",
      lead.owner_name ? fact("Owner", lead.owner_name) : "",
      lead.human_reviewed ? fact("Reviewed by", lead.reviewed_by || "Reviewed") : "",
      lead.deep_search_request_id ? fact("Deep search", "#" + lead.deep_search_request_id) : "",
    ].join("");

    return `<section class="summary" aria-label="Summary preview">
      <p class="summary-kicker">Summary preview</p>
      <header class="summary-head">
        <div>
          <h2>${esc(company)}</h2>
          <p>${place ? esc(place) : missing()} <span class="summary-dot">·</span> ${industry ? esc(industry) : missing()}</p>
        </div>
        <span class="summary-badge summary-${esc(status.toLowerCase())}">${esc(status)}</span>
      </header>
      <div class="summary-facts">
        ${fact("Source", lead.source || "manual")}
        <div class="summary-row"><span>Score</span>${lead.score == null || lead.score === "" ? missing() : `<b>${esc(lead.score)}</b>`}</div>
      </div>
      <div class="summary-grid">
        <article class="summary-card">
          <h3>Contact</h3>
          ${fact("Person", person)}
          ${linkRow("Phone", phoneHref(phone), phone)}
          ${linkRow("Email", emailOk(email) ? "mailto:" + email : "", email)}
        </article>
        <article class="summary-card">
          <h3>Hiring signal</h3>
          <p class="summary-copy">${signal ? esc(signal) : missing()}</p>
          <h3>Roles</h3>
          <div class="summary-chips">${chips || missing()}</div>
        </article>
        <article class="summary-card">
          <h3>Notes</h3>
          <p class="summary-copy">${notes ? esc(notes) : missing()}</p>
        </article>
        <article class="summary-card">
          <h3>Record</h3>
          ${fact("Added", when(lead.created_at))}
          ${fact("Updated", when(lead.updated_at))}
          ${linkRow("Source page", sourceUrl, sourceUrl)}
          ${linkRow("Website", website, website)}
          ${extra}
        </article>
      </div>
    </section>`;
  }

  window.LeadSummary = {render};
})();
