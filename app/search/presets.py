"""Search dropdowns, ready-made query presets, and the text sent to search providers.

The registry is configuration. It does not invent companies or contacts.
"""

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record
from app.core.errors import AppError
from app.models.search import SearchCriteria, SearchPreset, SearchRun
from app.models.workspace import WorkspaceSettings

US_STATES = (
    "Alabama",
    "Alaska",
    "Arizona",
    "Arkansas",
    "California",
    "Colorado",
    "Connecticut",
    "Delaware",
    "Florida",
    "Georgia",
    "Hawaii",
    "Idaho",
    "Illinois",
    "Indiana",
    "Iowa",
    "Kansas",
    "Kentucky",
    "Louisiana",
    "Maine",
    "Maryland",
    "Massachusetts",
    "Michigan",
    "Minnesota",
    "Mississippi",
    "Missouri",
    "Montana",
    "Nebraska",
    "Nevada",
    "New Hampshire",
    "New Jersey",
    "New Mexico",
    "New York",
    "North Carolina",
    "North Dakota",
    "Ohio",
    "Oklahoma",
    "Oregon",
    "Pennsylvania",
    "Rhode Island",
    "South Carolina",
    "South Dakota",
    "Tennessee",
    "Texas",
    "Utah",
    "Vermont",
    "Virginia",
    "Washington",
    "West Virginia",
    "Wisconsin",
    "Wyoming",
    "District of Columbia",
)

COUNTRIES = ("United States", "Canada", "United Kingdom", "India", "Australia")

OPPORTUNITY_TYPES = (
    "Staffing/recruitment RFP or bid",
    "Contract / C2C roles (agencies welcome)",
    "Contract-to-hire",
    "MSP/VMS supplier programs",
    "High-volume / seasonal hiring",
    "New plant / facility expansion hiring",
    "Executive search",
)

BUYER_TYPES = (
    "Public sector (city, county, state, school district, university, transit/port/utility)",
    "Private enterprise",
    "Healthcare system",
    "Staffing MSP/platform",
)

ROLE_CATEGORIES = (
    "IT/Software",
    "Healthcare/Nursing",
    "Engineering",
    "Manufacturing/Skilled trades",
    "Finance/Accounting",
    "Admin/Clerical",
    "Warehouse/Logistics",
    "Sales",
    "Executive",
)

INDUSTRIES = (
    "Staffing and recruiting",
    "Healthcare",
    "Information technology",
    "Manufacturing",
    "Education",
    "Government",
    "Logistics and warehousing",
    "Finance",
    "Construction",
    "Energy and utilities",
)

COMPANY_SIZES = ("1–50", "51–200", "201–1,000", "500+", "1,000+")

POSTED_WINDOWS = (
    ("open", "Open bids only"),
    ("7", "Last 7 days"),
    ("30", "Last 30 days"),
    ("90", "Last 90 days"),
)

MIN_SCORES = (("40", "40+"), ("55", "55+"), ("65", "65+"), ("75", "75+"), ("85", "85+"))

WINDOW_PHRASES = {
    "open": "open bids request for proposal",
    "7": "posted within the last 7 days",
    "30": "posted within the last 30 days",
    "90": "posted within the last 90 days",
}

CITY_SUGGESTIONS = (
    "New York",
    "Los Angeles",
    "Chicago",
    "Houston",
    "Phoenix",
    "Philadelphia",
    "San Antonio",
    "San Diego",
    "Dallas",
    "Austin",
    "San Jose",
    "Jacksonville",
    "Fort Worth",
    "Columbus",
    "Charlotte",
    "Indianapolis",
    "Seattle",
    "Denver",
    "Washington",
    "Boston",
    "Nashville",
    "Detroit",
    "Portland",
    "Atlanta",
    "Miami",
    "Minneapolis",
)

ICP_DEFAULTS = {
    "country": "United States",
    "states": [],
    "city": "",
    "opportunity_type": "Staffing/recruitment RFP or bid",
    "buyer_type": "",
    "role_category": "",
    "industry": "",
    "company_size": "",
    "posted_window": "open",
    "min_score": None,
    "keywords": '"staffing services" "agencies welcome"',
}

IDEAL_CUSTOMER = (
    "US companies hiring for US-based roles that want to hire, or are open to, "
    "recruitment vendors and staffing agencies."
)
PREVIOUS_IDEAL_CUSTOMER = "Growing companies that are hiring"


def _preset(**kwargs) -> dict:
    row = {
        "country": "United States",
        "states": [],
        "city": "",
        "opportunity_type": "",
        "buyer_type": "",
        "role_category": "",
        "industry": "",
        "company_size": "",
        "posted_window": "open",
        "min_score": None,
        "keywords": "",
        "query_templates": [],
        "ai_text": "",
    }
    row.update(kwargs)
    return row


DEFAULT_PRESETS = [
    _preset(
        slug="open-us-staffing-rfps",
        label="Open US staffing RFPs (temp personnel)",
        opportunity_type="Staffing/recruitment RFP or bid",
        buyer_type="Public sector (city, county, state, school district, university, transit/port/utility)",
        keywords='"temporary personnel" "staffing services"',
        query_templates=[
            '"request for proposal" "staffing services"',
            "site:bidnet.com temporary staffing personnel",
            '"temporary personnel" RFP United States',
        ],
        ai_text="Find open US requests for proposal for temporary personnel and staffing services, including BidNet and other public procurement notices.",
    ),
    _preset(
        slug="travel-nurse-staffing-bids",
        label="Travel nurse staffing bids",
        opportunity_type="Staffing/recruitment RFP or bid",
        buyer_type="Healthcare system",
        role_category="Healthcare/Nursing",
        industry="Healthcare",
        keywords='"travel nurse" staffing',
        query_templates=[
            '"travel nurse" staffing RFP',
            '"nursing staffing" "request for proposal"',
            "site:bidnet.com travel nurse staffing",
        ],
        ai_text="Find US travel nurse staffing bids and nursing vendor RFPs at healthcare systems.",
    ),
    _preset(
        slug="it-c2c-agencies-welcome",
        label="IT staffing / C2C contracts – agencies welcome",
        opportunity_type="Contract / C2C roles (agencies welcome)",
        role_category="IT/Software",
        industry="Information technology",
        keywords='"agencies welcome" C2C',
        query_templates=[
            '"agencies welcome" C2C IT contract',
            '"corp to corp" software developer staffing',
            '"staffing agencies" IT contract United States',
        ],
        ai_text="Find US IT and software contract roles that welcome agencies or C2C vendors.",
    ),
    _preset(
        slug="msp-new-suppliers",
        label="MSP programs accepting new suppliers",
        opportunity_type="MSP/VMS supplier programs",
        buyer_type="Staffing MSP/platform",
        keywords="MSP staffing new suppliers",
        query_templates=[
            'MSP "new suppliers" staffing',
            '"vendor management system" "become a supplier"',
            '"supplier program" staffing agencies welcome',
        ],
        ai_text="Find managed service provider and VMS programs in the United States that are accepting new staffing suppliers.",
    ),
    _preset(
        slug="seasonal-high-volume",
        label="Holiday/seasonal high-volume hiring",
        opportunity_type="High-volume / seasonal hiring",
        role_category="Warehouse/Logistics",
        industry="Logistics and warehousing",
        keywords="seasonal hiring staffing agency",
        query_templates=[
            'seasonal hiring "staffing agency"',
            '"holiday hiring" warehouse temporary',
            '"high volume" temporary workers agencies welcome',
        ],
        ai_text="Find US companies running holiday or seasonal high-volume hiring that use staffing vendors.",
    ),
    _preset(
        slug="new-manufacturing-plants",
        label="New manufacturing plants hiring 500+",
        opportunity_type="New plant / facility expansion hiring",
        role_category="Manufacturing/Skilled trades",
        industry="Manufacturing",
        company_size="500+",
        keywords='"new plant" hiring manufacturing',
        query_templates=[
            '"new plant" hiring manufacturing staffing',
            '"facility expansion" "now hiring" manufacturing',
            '"grand opening" factory jobs staffing agency',
        ],
        ai_text="Find new US manufacturing plants or facility expansions hiring 500 or more people and open to staffing vendors.",
    ),
    _preset(
        slug="executive-search-rfps",
        label="Executive search RFPs (public sector)",
        opportunity_type="Executive search",
        buyer_type="Public sector (city, county, state, school district, university, transit/port/utility)",
        role_category="Executive",
        keywords='"executive search" RFP',
        query_templates=[
            '"executive search" "request for proposal"',
            'site:bidnet.com "executive recruitment"',
            '"executive recruiter" RFP city OR county OR university',
        ],
        ai_text="Find public-sector executive search RFPs from US cities, counties, universities, and agencies.",
    ),
    _preset(
        slug="school-district-staffing",
        label="School district staffing RFPs",
        opportunity_type="Staffing/recruitment RFP or bid",
        buyer_type="Public sector (city, county, state, school district, university, transit/port/utility)",
        industry="Education",
        keywords='"school district" staffing RFP',
        query_templates=[
            '"school district" staffing "request for proposal"',
            '"substitute teacher" staffing bid',
            "site:bidnet.com school district personnel",
        ],
        ai_text="Find US school district staffing and substitute personnel RFPs.",
    ),
    _preset(
        slug="healthcare-vendor-systems",
        label="Healthcare systems using vendors",
        opportunity_type="Staffing/recruitment RFP or bid",
        buyer_type="Healthcare system",
        industry="Healthcare",
        role_category="Healthcare/Nursing",
        keywords='"healthcare system" "staffing vendor"',
        query_templates=[
            '"healthcare system" "staffing vendor"',
            '"health system" "vendor partners" nursing',
            '"contingent labor" hospital staffing',
        ],
        ai_text="Find US healthcare systems that hire through staffing vendors or contingent labor partners.",
    ),
    _preset(
        slug="government-it-staffing",
        label="Government IT staffing contracts",
        opportunity_type="Contract / C2C roles (agencies welcome)",
        buyer_type="Public sector (city, county, state, school district, university, transit/port/utility)",
        role_category="IT/Software",
        industry="Government",
        keywords='"IT staffing" government contract',
        query_templates=[
            '"IT staffing" contract government',
            'site:sam.gov "information technology" staffing',
            '"staff augmentation" "request for proposal" IT',
        ],
        ai_text="Find US government IT staffing contracts and staff-augmentation solicitations.",
    ),
]


def option_catalog() -> dict:
    return {
        "countries": list(COUNTRIES),
        "us_states": list(US_STATES),
        "opportunity_types": list(OPPORTUNITY_TYPES),
        "buyer_types": list(BUYER_TYPES),
        "role_categories": list(ROLE_CATEGORIES),
        "industries": list(INDUSTRIES),
        "company_sizes": list(COMPANY_SIZES),
        "posted_windows": [{"value": value, "label": label} for value, label in POSTED_WINDOWS],
        "min_scores": [{"value": value, "label": label} for value, label in MIN_SCORES],
        "cities": list(CITY_SUGGESTIONS),
    }


def _get(source, key, default=""):
    if isinstance(source, dict):
        value = source.get(key, default)
    else:
        value = getattr(source, key, default)
    return default if value is None else value


def _strings(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = [part.strip() for part in value.splitlines() if part.strip()]
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        text = " ".join(str(item or "").split())
        if text and text.lower() != "any" and text not in items:
            items.append(text)
    return items


def _choice(value, allowed: tuple[str, ...], label: str, *, required: bool = False) -> str:
    text = " ".join(str(value or "").split())
    if text.lower() in {"", "any", "any size", "any industry"}:
        if required:
            raise AppError(f"Choose a {label}")
        return ""
    if text not in allowed:
        raise AppError(f"Unknown {label}")
    return text


def clean_states(payload, country: str) -> list[str]:
    if isinstance(payload, dict) and payload.get("states") is not None:
        raw = payload.get("states")
    else:
        raw = _get(payload, "state", "")
    names = _strings(raw)
    if country in {"", "United States"}:
        for name in names:
            if name not in US_STATES:
                raise AppError("Unknown US state")
    return names[:51]


def clean_criteria(payload: dict, *, default_country: str = "") -> dict:
    country = " ".join(str(payload.get("country") or "").split())
    if not country:
        country = default_country
    if country and country not in COUNTRIES:
        raise AppError("Unknown country")
    window = str(payload.get("posted_window") or "").strip()
    if window.lower() in {"", "any"}:
        window = ""
    elif window not in WINDOW_PHRASES:
        raise AppError("Unknown posted window")
    min_score = payload.get("min_score")
    if min_score in (None, "", "any", "Any"):
        score = None
    else:
        try:
            score = int(min_score)
        except (TypeError, ValueError):
            raise AppError("Unknown minimum score") from None
        if score < 0 or score > 100:
            raise AppError("Unknown minimum score")
    templates = [item[:180] for item in _strings(payload.get("query_templates"))][:8]
    industry = " ".join(str(payload.get("industry") or "").split())[:160]
    if industry.lower() in {"any", "any industry"}:
        industry = ""
    size = _choice(payload.get("company_size"), COMPANY_SIZES + ("Any size",), "company size")
    if size == "Any size":
        size = ""
    return {
        "country": country,
        "states": clean_states(payload, country),
        "state": "",
        "city": " ".join(str(payload.get("city") or "").split())[:80],
        "district": " ".join(str(payload.get("district") or "").split())[:80],
        "postal_code": " ".join(str(payload.get("postal_code") or "").split())[:20],
        "opportunity_type": _choice(payload.get("opportunity_type"), OPPORTUNITY_TYPES, "opportunity type"),
        "buyer_type": _choice(payload.get("buyer_type"), BUYER_TYPES, "buyer type"),
        "role_category": _choice(payload.get("role_category"), ROLE_CATEGORIES, "role category"),
        "industry": industry,
        "company_size": size,
        "posted_window": window,
        "min_score": score,
        "keywords": " ".join(str(payload.get("keywords") or "").split())[:500],
        "query_templates": templates,
    }


def compose_query(criteria) -> str:
    parts = []
    keywords = str(_get(criteria, "keywords", "") or "").strip()
    if keywords:
        parts.append(keywords)
    templates = _strings(_get(criteria, "query_templates", []))
    for template in templates:
        if template not in keywords:
            parts.append(template)
    for key in ("opportunity_type", "role_category", "buyer_type", "industry"):
        value = str(_get(criteria, key, "") or "").strip()
        if value and value.lower() not in {"any", "any industry"} and value not in " ".join(parts):
            parts.append(value)
    window = WINDOW_PHRASES.get(str(_get(criteria, "posted_window", "") or "").strip(), "")
    if window and window not in " ".join(parts):
        parts.append(window)
    if not templates and "companies" not in " ".join(parts).lower():
        parts.append("companies")
    location = _location_phrase(criteria)
    if location:
        parts.append("in " + location)
    size = str(_get(criteria, "company_size", "") or "").strip()
    if size and size.lower() not in {"any", "any size"}:
        parts.append(size + " employees")
    return " ".join(part for part in parts if part)[:900]


def _location_phrase(criteria) -> str:
    country = str(_get(criteria, "country", "") or "").strip()
    states = _strings(_get(criteria, "states", []))
    if not states:
        raw = str(_get(criteria, "state", "") or "").strip()
        if raw and raw.lower() not in {"any", "any state"}:
            states = [part.strip() for part in raw.split(",") if part.strip()]
    bits = []
    city = str(_get(criteria, "city", "") or "").strip()
    if city:
        bits.append(city)
    if len(states) == 1:
        bits.append(states[0])
    elif states:
        bits.append("(" + " OR ".join(states[:8]) + ")")
    district = str(_get(criteria, "district", "") or "").strip()
    if district:
        bits.append(district)
    postal = str(_get(criteria, "postal_code", "") or "").strip()
    if postal:
        bits.append(postal)
    if country:
        bits.append(country)
    return ", ".join(bits)


def criteria_brief(criteria: dict | None) -> str:
    if not criteria:
        return ""
    labels = (
        ("country", "Country"),
        ("states", "States"),
        ("city", "City"),
        ("opportunity_type", "Opportunity"),
        ("buyer_type", "Buyer"),
        ("role_category", "Role"),
        ("industry", "Industry"),
        ("company_size", "Company size"),
        ("posted_window", "Posted window"),
        ("keywords", "Keywords"),
        ("query_templates", "Query templates"),
    )
    lines = []
    for key, label in labels:
        value = criteria.get(key)
        if value in (None, "", []):
            continue
        if key == "posted_window":
            value = dict(POSTED_WINDOWS).get(str(value), value)
        lines.append(f"{label}: {value}")
    return "\n".join(lines)


def merge_query_templates(plan: dict, criteria: dict | None) -> dict:
    if not criteria:
        return plan
    templates = _strings(criteria.get("query_templates") if isinstance(criteria, dict) else [])
    queries = []
    for item in templates + list(plan.get("queries") or []):
        text = str(item or "").strip()[:180]
        if text and text not in queries:
            queries.append(text)
    if not queries:
        return plan
    updated = dict(plan)
    updated["queries"] = queries[:8]
    return updated


def preset_dict(row: SearchPreset) -> dict:
    return {
        "id": row.id,
        "slug": row.slug,
        "label": row.label,
        "country": row.country or "",
        "states": list(row.states or []),
        "city": row.city or "",
        "opportunity_type": row.opportunity_type or "",
        "buyer_type": row.buyer_type or "",
        "role_category": row.role_category or "",
        "industry": row.industry or "",
        "company_size": row.company_size or "",
        "posted_window": row.posted_window or "",
        "min_score": row.min_score,
        "keywords": row.keywords or "",
        "query_templates": list(row.query_templates or []),
        "ai_text": row.ai_text or "",
        "sort_order": row.sort_order or 0,
    }


def workspace_defaults(db: Session) -> dict:
    row = db.get(WorkspaceSettings, 1)
    if row is None:
        return dict(ICP_DEFAULTS)
    states = list(row.icp_states or [])
    return {
        "country": row.icp_country or ICP_DEFAULTS["country"],
        "states": states,
        "city": row.icp_city or "",
        "opportunity_type": row.icp_opportunity_type if row.icp_opportunity_type is not None else ICP_DEFAULTS["opportunity_type"],
        "buyer_type": row.icp_buyer_type or "",
        "role_category": row.icp_role_category or "",
        "industry": row.icp_industry or "",
        "company_size": row.icp_company_size or "",
        "posted_window": row.icp_posted_window if row.icp_posted_window is not None else ICP_DEFAULTS["posted_window"],
        "min_score": row.icp_min_score,
        "keywords": row.icp_keywords if row.icp_keywords is not None else ICP_DEFAULTS["keywords"],
    }


def catalog_payload(db: Session) -> dict:
    rows = db.scalars(select(SearchPreset).order_by(SearchPreset.sort_order, SearchPreset.id)).all()
    return {"options": option_catalog(), "defaults": workspace_defaults(db), "presets": [preset_dict(row) for row in rows]}


def suggestions(db: Session, query: str, limit: int = 12) -> list[str]:
    needle = " ".join((query or "").split()).lower()
    found = []
    seen = set()

    def add(text):
        item = " ".join(str(text or "").split())
        if len(item) < 2:
            return
        key = item.lower()
        if key in seen:
            return
        if needle and needle not in key:
            return
        seen.add(key)
        found.append(item[:180])

    presets = db.scalars(select(SearchPreset).order_by(SearchPreset.sort_order, SearchPreset.id)).all()
    for preset in presets:
        add(preset.keywords)
        for template in preset.query_templates or []:
            add(template)
        add(preset.label)
    for row in db.scalars(select(SearchCriteria.keywords).order_by(SearchCriteria.id.desc()).limit(40)):
        add(row)
    for row in db.scalars(select(SearchRun.query).order_by(SearchRun.id.desc()).limit(20)):
        add(row)
    for city in CITY_SUGGESTIONS:
        add(city)
    return found[: max(1, min(limit, 20))]


def _slug(label: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")[:70] or "preset"
    slug = base
    number = 2
    while slug in taken:
        slug = f"{base}-{number}"
        number += 1
    return slug


def _write_preset(row: SearchPreset, cleaned: dict, label: str, ai_text: str) -> None:
    row.label = label[:160]
    row.ai_text = (ai_text or label)[:2000]
    row.country = cleaned["country"] or "United States"
    row.states = cleaned["states"]
    row.city = cleaned["city"]
    row.opportunity_type = cleaned["opportunity_type"]
    row.buyer_type = cleaned["buyer_type"]
    row.role_category = cleaned["role_category"]
    row.industry = cleaned["industry"]
    row.company_size = cleaned["company_size"]
    row.posted_window = cleaned["posted_window"]
    row.min_score = cleaned["min_score"]
    row.keywords = cleaned["keywords"]
    row.query_templates = cleaned["query_templates"]


def create_preset(db: Session, actor, payload: dict) -> dict:
    label = " ".join(str(payload.get("label") or "").split())
    if len(label) < 3:
        raise AppError("Give the preset a name")
    cleaned = clean_criteria(payload, default_country="United States")
    taken = set(db.scalars(select(SearchPreset.slug)).all())
    last = db.scalar(select(func.max(SearchPreset.sort_order))) or 0
    row = SearchPreset(slug=_slug(label, taken), sort_order=int(last) + 1)
    _write_preset(row, cleaned, label, str(payload.get("ai_text") or ""))
    db.add(row)
    db.flush()
    record(db, user=actor, action="search_preset_created", module="settings", target=row.slug, detail={"label": row.label})
    db.commit()
    db.refresh(row)
    return preset_dict(row)


def update_preset(db: Session, actor, preset_id: int, payload: dict) -> dict:
    row = db.get(SearchPreset, preset_id)
    if row is None:
        raise AppError("Preset not found", 404)
    label = " ".join(str(payload.get("label") or row.label).split())
    if len(label) < 3:
        raise AppError("Give the preset a name")
    cleaned = clean_criteria(payload, default_country=row.country or "United States")
    _write_preset(row, cleaned, label, str(payload.get("ai_text") if "ai_text" in payload else row.ai_text))
    record(db, user=actor, action="search_preset_updated", module="settings", target=row.slug, detail={"label": row.label})
    db.commit()
    db.refresh(row)
    return preset_dict(row)


def delete_preset(db: Session, actor, preset_id: int) -> None:
    row = db.get(SearchPreset, preset_id)
    if row is None:
        raise AppError("Preset not found", 404)
    slug = row.slug
    db.delete(row)
    record(db, user=actor, action="search_preset_deleted", module="settings", target=slug)
    db.commit()


def seed_presets(db: Session) -> None:
    count = db.scalar(select(func.count()).select_from(SearchPreset)) or 0
    if count:
        return
    for index, item in enumerate(DEFAULT_PRESETS):
        row = SearchPreset(slug=item["slug"], sort_order=index)
        payload = dict(item)
        label = payload.pop("label")
        slug = payload.pop("slug")
        ai_text = payload.pop("ai_text")
        del slug
        cleaned = clean_criteria(payload, default_country="United States")
        _write_preset(row, cleaned, label, ai_text)
        db.add(row)
    db.flush()


def apply_icp_defaults(row: WorkspaceSettings) -> None:
    if not row.icp_country:
        row.icp_country = ICP_DEFAULTS["country"]
    if row.icp_states is None:
        row.icp_states = []
    if row.icp_opportunity_type is None:
        row.icp_opportunity_type = ICP_DEFAULTS["opportunity_type"]
    if row.icp_buyer_type is None:
        row.icp_buyer_type = ""
    if row.icp_role_category is None:
        row.icp_role_category = ""
    if row.icp_industry is None:
        row.icp_industry = ""
    if row.icp_company_size is None:
        row.icp_company_size = ""
    if row.icp_posted_window is None:
        row.icp_posted_window = ICP_DEFAULTS["posted_window"]
    if row.icp_keywords is None:
        row.icp_keywords = ICP_DEFAULTS["keywords"]
    if row.icp_city is None:
        row.icp_city = ""
    if (row.ideal_customer or "") in {"", PREVIOUS_IDEAL_CUSTOMER}:
        row.ideal_customer = IDEAL_CUSTOMER
