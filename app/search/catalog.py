"""Deterministic sample companies used only when no search API key is configured."""

CATALOG = [
    {
        "company": "Northstar Logistics",
        "contact_name": "Alex Morgan",
        "email": "alex.morgan@northstarlogistics.example",
        "phone": "+1-415-555-0142",
        "website": "https://northstarlogistics.example",
        "industry": "logistics",
        "keywords": "freight warehouse supply chain",
        "company_size": "51–200",
        "country": "United States",
        "state": "California",
        "district": "San Francisco County",
        "city": "San Francisco",
        "postal_code": "94105",
        "snippet": "Northstar Logistics runs regional freight and warehouse hiring across California.",
    },
    {
        "company": "BluePeak Manufacturing",
        "contact_name": "Jordan Hale",
        "email": "jordan.hale@bluepeak.example",
        "phone": "+1-216-555-0194",
        "website": "https://bluepeak.example",
        "industry": "manufacturing",
        "keywords": "industrial plant expansion",
        "company_size": "201–1,000",
        "country": "United States",
        "state": "Ohio",
        "district": "Cuyahoga",
        "city": "Cleveland",
        "postal_code": "44114",
        "snippet": "BluePeak Manufacturing is adding a second shift at its Cleveland plant.",
    },
    {
        "company": "Summit Retail Services",
        "contact_name": "Casey Nguyen",
        "email": "casey.nguyen@summitretail.example",
        "phone": "+1-312-555-0177",
        "website": "https://summitretail.example",
        "industry": "retail",
        "keywords": "stores staffing",
        "company_size": "1,000+",
        "country": "United States",
        "state": "Illinois",
        "district": "Cook County",
        "city": "Chicago",
        "postal_code": "60601",
        "snippet": "Summit Retail Services operates multi-state store staffing programs.",
    },
    {
        "company": "Vertex Health Group",
        "contact_name": "Sarah Patel",
        "email": "sarah.patel@vertexhealth.example",
        "phone": "+91-79-5555-0148",
        "website": "https://vertexhealth.example",
        "industry": "healthcare",
        "keywords": "clinics hospitals hiring",
        "company_size": "201–1,000",
        "country": "India",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "city": "Ahmedabad",
        "postal_code": "380015",
        "snippet": "Vertex Health Group is opening clinics and hiring clinical operations staff.",
    },
    {
        "company": "BluePeak Tech",
        "contact_name": "Rahul Joshi",
        "email": "rahul.joshi@bluepeaktech.example",
        "phone": "+91-265-555-0190",
        "website": "https://bluepeaktech.example",
        "industry": "technology",
        "keywords": "software product engineering",
        "company_size": "51–200",
        "country": "India",
        "state": "Gujarat",
        "district": "Vadodara",
        "city": "Vadodara",
        "postal_code": "390007",
        "snippet": "BluePeak Tech builds B2B software for industrial customers in Gujarat.",
    },
    {
        "company": "Harbour & Co Advisors",
        "contact_name": "Priya Shah",
        "email": "priya.shah@harbourco.example",
        "phone": "+91-22-5555-0116",
        "website": "https://harbourco.example",
        "industry": "professional services",
        "keywords": "consulting finance",
        "company_size": "1–50",
        "country": "India",
        "state": "Maharashtra",
        "district": "Mumbai",
        "city": "Mumbai",
        "postal_code": "400001",
        "snippet": "Harbour & Co Advisors advises growing companies on finance and hiring plans.",
    },
    {
        "company": "Kanaka Foods",
        "contact_name": "Neha Kapoor",
        "email": "neha.kapoor@kanakafoods.example",
        "phone": "+91-80-5555-0133",
        "website": "https://kanakafoods.example",
        "industry": "food",
        "keywords": "processing distribution",
        "company_size": "51–200",
        "country": "India",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "postal_code": "560001",
        "snippet": "Kanaka Foods processes and distributes packaged foods across South India.",
    },
    {
        "company": "Cedar Grid Energy",
        "contact_name": "Morgan Ellis",
        "email": "morgan.ellis@cedargrid.example",
        "phone": "+1-512-555-0164",
        "website": "https://cedargrid.example",
        "industry": "energy",
        "keywords": "solar utilities field service",
        "company_size": "51–200",
        "country": "United States",
        "state": "Texas",
        "district": "Travis County",
        "city": "Austin",
        "postal_code": "78701",
        "snippet": "Cedar Grid Energy installs commercial solar and hires field technicians.",
    },
]

SYNTH_PEOPLE = ["Aarav Mehta", "Priya Shah", "Rahul Joshi", "Neha Kapoor", "Vikram Desai"]
SYNTH_SUFFIXES = ["Works", "Labs", "Systems", "Partners", "Group"]


def synthesize(criteria, count: int = 5) -> list[dict]:
    """Build stable fictional companies from the target profile when the catalog has no hit."""
    industry = (criteria.industry or "Business services").strip()
    city = (criteria.city or "Vadodara").strip()
    state = (criteria.state or "Gujarat").strip()
    district = (criteria.district or city).strip()
    country = (criteria.country or "India").strip()
    postal = (criteria.postal_code or "390001").strip()
    size = criteria.company_size if criteria.company_size and criteria.company_size != "Any size" else "51–200"
    rows = []
    for index in range(count):
        person = SYNTH_PEOPLE[index % len(SYNTH_PEOPLE)]
        suffix = SYNTH_SUFFIXES[index % len(SYNTH_SUFFIXES)]
        slug = re_slug(industry, city, index)
        company = f"{industry.title()} {suffix} {city[:3].upper()}{index + 1}"
        rows.append(
            {
                "company": company,
                "contact_name": person,
                "email": f"{slug}@leadpilot.example",
                "phone": f"+91-265-555-01{index:02d}",
                "website": f"https://{slug}.example",
                "industry": industry,
                "keywords": criteria.keywords or industry,
                "company_size": size,
                "country": country,
                "state": state,
                "district": district,
                "city": city,
                "postal_code": postal,
                "snippet": f"{company} operates in {city}. Demo search result for {industry}.",
                "estimated_value": 120000 + index * 35000,
            }
        )
    return rows


def re_slug(*parts) -> str:
    import re

    raw = "-".join(str(part) for part in parts)
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    return slug[:48] or "company"
