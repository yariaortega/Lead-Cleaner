from pathlib import Path
from collections import Counter
import csv
import re
import sys
from unicodedata import normalize


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

INPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("b.txt")
OUTPUT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("cleaned_email_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FREE_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.de",
    "hotmail.com", "hotmail.de", "outlook.com", "outlook.de",
    "live.com", "live.de", "msn.com", "aol.com", "icloud.com",
    "gmx.de", "gmx.net", "web.de", "arcor.de", "freenet.de",
}

AUTOMATED_LOCAL_PARTS = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "mailer-daemon", "postmaster", "abuse", "root",
}

# Exact city/location tokens only. No locations are guessed.
CITY_ALIASES = {
    # Germany
    "aachen": "Aachen",
    "augsburg": "Augsburg",
    "bad-homburg": "Bad Homburg",
    "bamberg": "Bamberg",
    "bayreuth": "Bayreuth",
    "berlin": "Berlin",
    "bielefeld": "Bielefeld",
    "bochum": "Bochum",
    "bonn": "Bonn",
    "braunschweig": "Braunschweig",
    "bremen": "Bremen",
    "chemnitz": "Chemnitz",
    "darmstadt": "Darmstadt",
    "dortmund": "Dortmund",
    "dresden": "Dresden",
    "duesseldorf": "Düsseldorf",
    "duisburg": "Duisburg",
    "erfurt": "Erfurt",
    "essen": "Essen",
    "frankfurt": "Frankfurt am Main",
    "freiburg": "Freiburg im Breisgau",
    "fulda": "Fulda",
    "gelsenkirchen": "Gelsenkirchen",
    "giessen": "Gießen",
    "goettingen": "Göttingen",
    "hagen": "Hagen",
    "halle": "Halle (Saale)",
    "hamburg": "Hamburg",
    "hamm": "Hamm",
    "hanau": "Hanau",
    "hannover": "Hannover",
    "heidelberg": "Heidelberg",
    "heilbronn": "Heilbronn",
    "herford": "Herford",
    "herne": "Herne",
    "hildesheim": "Hildesheim",
    "ingolstadt": "Ingolstadt",
    "kassel": "Kassel",
    "kiel": "Kiel",
    "koblenz": "Koblenz",
    "koeln": "Köln",
    "krefeld": "Krefeld",
    "leipzig": "Leipzig",
    "luebeck": "Lübeck",
    "magdeburg": "Magdeburg",
    "mainz": "Mainz",
    "mannheim": "Mannheim",
    "moenchengladbach": "Mönchengladbach",
    "muenchen": "München",
    "muenster": "Münster",
    "neu-ulm": "Neu-Ulm",
    "nuernberg": "Nürnberg",
    "oldenburg": "Oldenburg",
    "osnabrueck": "Osnabrück",
    "passau": "Passau",
    "pforzheim": "Pforzheim",
    "regensburg": "Regensburg",
    "rostock": "Rostock",
    "saarbruecken": "Saarbrücken",
    "solingen": "Solingen",
    "stuttgart": "Stuttgart",
    "traunstein": "Traunstein",
    "tuebingen": "Tübingen",
    "ulm": "Ulm",
    "wiesbaden": "Wiesbaden",
    "wolfsburg": "Wolfsburg",
    "wuppertal": "Wuppertal",
    "wuerzburg": "Würzburg",
    "zwickau": "Zwickau",

    # Other explicit locations found in international addresses
    "wien": "Vienna",
    "vienna": "Vienna",
    "zuerich": "Zurich",
    "zurich": "Zurich",
    "paris": "Paris",
    "toronto": "Toronto",
    "milano": "Milan",
    "milan": "Milan",
    "roma": "Rome",
    "rome": "Rome",
    "sofia": "Sofia",
    "helsinki": "Helsinki",
    "hongkong": "Hong Kong",
    "hong-kong": "Hong Kong",
    "malmo": "Malmö",
    "copenhagen": "Copenhagen",
    "kopenhagen": "Copenhagen",
    "stockholm": "Stockholm",
    "budapest": "Budapest",
    "london": "London",
    "newyork": "New York",
    "new-york": "New York",
    "tokyo": "Tokyo",
    "daikanyama": "Daikanyama",
}

# Industries are assigned only when explicit terms occur in the email.
INDUSTRY_RULES = [
    (
        "Architecture / Planning / Engineering",
        {
            "architekt", "architekten", "architektur", "architect",
            "architects", "architecture", "archiplan", "archipoint",
            "planung", "planer", "engineering", "ingenieur", "ingenieure",
            "landschaftsarchitekten", "stadtplanung", "staedtebau",
        },
        ("architekt", "architect", "archiplan", "archipoint", "arch", "archi"),
    ),
    (
        "Construction / Building Trades",
        {
            "bau", "hochbau", "tiefbau", "ausbau", "umbau", "sanierung",
            "bedachung", "dach", "dachdecker", "holzbau", "maler",
            "elektro", "elektrotechnik", "sanitaer", "haustechnik",
            "heizung", "lueftung", "klimatechnik", "geruestbau",
            "schreinerei", "tischlerei", "fenster", "fassade", "beton",
            "baustoff", "baustatik", "bautechnik", "bauleitung",
            "baubegleitung", "bauunternehmen", "bauservice",
        },
        (),
    ),
    (
        "Real Estate / Property",
        {
            "immobilien", "immo", "property", "realestate",
            "hausverwaltung", "wohnbau", "wohnen", "wohnungsbau",
            "grundstueck", "makler",
        },
        (),
    ),
    (
        "Hospitality / Food / Events",
        {
            "hotel", "hostel", "restaurant", "cafe", "coffee",
            "backerei", "baeckerei", "getraenke", "brauerei", "wein",
            "event", "events", "tourismus", "tours", "reisen",
            "bistro", "grill",
        },
        (),
    ),
    (
        "Media / Publishing / Marketing",
        {
            "media", "medien", "pr", "presse", "verlag", "publisher",
            "publishing", "communication", "kommunikation", "marketing",
            "werbung", "nachrichten", "news", "radio", "film", "design",
        },
        (),
    ),
    (
        "Legal / Consulting / Professional Services",
        {
            "rechtsanwalt", "rechtsanwaelte", "anwalt", "legal", "law",
            "consult", "consulting", "beratung", "berater", "audit",
            "steuer", "notariat",
        },
        (),
    ),
    (
        "Education / Research",
        {
            "uni", "university", "universitaet", "hochschule", "school",
            "schule", "academy", "institut", "research", "forschung",
        },
        (),
    ),
    (
        "Healthcare / Care",
        {
            "apotheke", "pharma", "medizin", "health", "gesundheit",
            "pflege", "care", "zahn", "arzt", "aerzte", "hospital",
            "klinik", "physio",
        },
        (),
    ),
    (
        "Nonprofit / Social / Religious",
        {
            "awo", "caritas", "kirche", "kirchenkreis", "kirchen",
            "church", "diakon", "mission", "unhcr", "stiftung",
            "foundation", "hilfe", "social", "sozial", "ehrenamt",
            "verein",
        },
        (),
    ),
    (
        "Culture / Museums",
        {
            "museum", "museums", "theater", "theatre", "kultur",
            "culture", "opera", "oper",
        },
        (),
    ),
    (
        "Technology / IT",
        {
            "tech", "software", "digital", "cloud", "data", "systems",
            "online", "app", "github",
        },
        (),
    ),
    (
        "Public / Government",
        {
            "gov", "government", "stadt", "city", "bezirk", "amt",
            "rathaus", "polizei", "ministerium",
        },
        (),
    ),
    (
        "Finance / Insurance",
        {
            "bank", "finance", "finanz", "versicherung", "insurance",
            "asset", "capital",
        },
        (),
    ),
    (
        "Manufacturing / Industrial",
        {
            "industrie", "industrial", "factory", "production",
            "manufacturing", "metall", "stahl", "glas", "holz",
            "chemie",
        },
        (),
    ),
    (
        "Transportation / Logistics",
        {
            "logistik", "transport", "cargo", "shipping", "fahrzeug",
        },
        (),
    ),
    (
        "Energy",
        {
            "energie", "energy", "solar", "wind", "power",
        },
        (),
    ),
    (
        "Environment / Agriculture",
        {
            "oeko", "umwelt", "environment", "green", "natur",
            "garten", "gaerten", "agrar", "landwirtschaft",
        },
        (),
    ),
]


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

EMAIL_RE = re.compile(
    r"^(?=.{3,254}$)"
    r"[A-Z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}"
    r"@"
    r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
    r"[A-Z]{2,63}$",
    re.IGNORECASE,
)


def read_input(path: Path) -> list[str]:
    for encoding in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding).splitlines()
        except UnicodeError:
            continue
    raise UnicodeError(f"Could not decode: {path}")


def clean_address(value: str) -> str:
    # Removes unnecessary spaces, tabs, and carriage returns.
    return " ".join(value.split()).lower()


def text_tokens(email: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", email))


def detect_industries(email: str) -> list[str]:
    tokens = text_tokens(email)
    matches = []

    for industry, exact_terms, prefixes in INDUSTRY_RULES:
        found = bool(tokens & exact_terms)

        if not found:
            found = any(
                token.startswith(prefix)
                for token in tokens
                for prefix in prefixes
            )

        if found:
            matches.append(industry)

    return matches


def detect_cities(email: str) -> list[str]:
    matches = []

    # Longest aliases first prevents "Neu-Ulm" from also matching "Ulm".
    for alias in sorted(CITY_ALIASES, key=len, reverse=True):
        pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        if re.search(pattern, email):
            city = CITY_ALIASES[alias]
            if city not in matches:
                matches.append(city)

    return matches


def organization_type(email: str, domain: str, industries: list[str]) -> str:
    if domain in FREE_PROVIDERS:
        return "Personal / free-mail (unverified)"

    if "Education / Research" in industries:
        return "Education / research"

    if "Nonprofit / Social / Religious" in industries:
        return "Nonprofit / social / religious"

    if "Public / Government" in industries or "Culture / Museums" in industries:
        return "Public / institutional"

    return "Business / organization (domain-based)"


def review_status(local_part: str, domain: str) -> str:
    notes = []

    if domain in FREE_PROVIDERS:
        notes.append("free/generic mail provider")

    if local_part in AUTOMATED_LOCAL_PARTS:
        notes.append("automated or non-personal mailbox")

    if len(local_part) <= 1:
        notes.append("very short local part")

    if re.fullmatch(r"[0-9._-]+", local_part):
        notes.append("numeric-only local part")

    if notes:
        return "Valid - review: " + "; ".join(notes)

    return "Valid"


def safe_filename(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def write_table(path: Path, rows: list[dict[str, str]]) -> None:
    columns = [
        "Email",
        "Company/Organization",
        "Industry",
        "City/Location",
        "Category",
        "Status",
    ]

    # CSV
    with path.with_suffix(".csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    # Readable tab-delimited TXT
    with path.with_suffix(".txt").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------
# Parse, validate, and deduplicate
# ---------------------------------------------------------

raw_lines = read_input(INPUT)
seen = {}
duplicate_rows = []
invalid_rows = []
master_rows = []

for row_number, raw_line in enumerate(raw_lines, start=1):
    normalized = clean_address(raw_line)

    if not normalized:
        continue

    if normalized in seen:
        duplicate_rows.append(
            {
                "row": row_number,
                "address": normalized,
                "first_row": seen[normalized],
            }
        )
        continue

    seen[normalized] = row_number

    if not EMAIL_RE.fullmatch(normalized):
        invalid_rows.append(
            {"row": row_number, "address": normalized}
        )
        continue

    local_part, domain = normalized.rsplit("@", 1)
    industries = detect_industries(normalized)
    cities = detect_cities(normalized)

    # The domain is used as evidence. It is not expanded into an invented
    # legal or marketing company name.
    organization = (
        "Not determinable from email"
        if domain in FREE_PROVIDERS
        else f"Domain: {domain}"
    )

    row = {
        "Email": normalized,
        "Company/Organization": organization,
        "Industry": "; ".join(industries),
        "City/Location": "; ".join(cities),
        "Category": organization_type(normalized, domain, industries),
        "Status": review_status(local_part, domain),
    }

    master_rows.append(row)


# ---------------------------------------------------------
# Master and review files
# ---------------------------------------------------------

write_table(OUTPUT_DIR / "master_cleaned", master_rows)

review_rows = [
    row for row in master_rows
    if row["Status"] != "Valid"
]
write_table(OUTPUT_DIR / "review_flagged", review_rows)


# ---------------------------------------------------------
# Separate category, industry, and location lists
# ---------------------------------------------------------

def write_grouped_files(
    rows: list[dict[str, str]],
    field: str,
    prefix: str,
    minimum_rows: int = 1,
) -> dict[str, int]:
    groups = {}

    for row in rows:
        labels = [x.strip() for x in row[field].split(";") if x.strip()]
        if not labels:
            labels = ["Not determinable from email"]

        for label in labels:
            groups.setdefault(label, []).append(row)

    counts = {
        label: len(group_rows)
        for label, group_rows in groups.items()
        if len(group_rows) >= minimum_rows
    }

    for label, group_rows in groups.items():
        if len(group_rows) < minimum_rows:
            continue
        filename = safe_filename(label)
        write_table(OUTPUT_DIR / f"{prefix}_{filename}", group_rows)

    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


category_counts = write_grouped_files(
    master_rows, "Category", "category"
)

industry_counts = write_grouped_files(
    master_rows, "Industry", "industry", minimum_rows=5
)

location_counts = write_grouped_files(
    master_rows, "City/Location", "location", minimum_rows=5
)


# ---------------------------------------------------------
# Cleaning report
# ---------------------------------------------------------

report_path = OUTPUT_DIR / "cleaning_report.txt"

with report_path.open("w", encoding="utf-8", newline="\n") as f:
    f.write("EMAIL LIST CLEANING REPORT\n")
    f.write("==========================\n\n")
    f.write(f"Input file: {INPUT}\n")
    f.write(f"Nonblank input rows: {len(seen) + len(duplicate_rows)}\n")
    f.write(f"Unique valid addresses retained: {len(master_rows)}\n")
    f.write(f"Duplicate rows removed: {len(duplicate_rows)}\n")
    f.write(f"Invalid/malformed rows removed: {len(invalid_rows)}\n")
    f.write(f"Review-flagged valid addresses: {len(review_rows)}\n\n")

    f.write("Category counts:\n")
    for label, count in category_counts.items():
        f.write(f"- {label}: {count}\n")

    f.write("\nIndustries represented by at least five addresses:\n")
    for label, count in industry_counts.items():
        f.write(f"- {label}: {count}\n")

    f.write("\nLocations represented by at least five addresses:\n")
    for label, count in location_counts.items():
        f.write(f"- {label}: {count}\n")

    f.write("\nDuplicate rows removed:\n")
    if duplicate_rows:
        for item in duplicate_rows:
            f.write(
                f"- Row {item['row']}: {item['address']} "
                f"(first occurrence: row {item['first_row']})\n"
            )
    else:
        f.write("- None\n")

    f.write("\nInvalid or malformed rows removed:\n")
    if invalid_rows:
        for item in invalid_rows:
            f.write(f"- Row {item['row']}: {item['address']}\n")
    else:
        f.write("- None\n")

    f.write("\nMethod notes:\n")
    f.write("- Addresses were trimmed, whitespace-normalized, and lowercased.\n")
    f.write("- The first occurrence of each duplicate was retained.\n")
    f.write("- Only strict syntactically valid addresses are in the master list.\n")
    f.write("- Company/organization names were not invented; non-free domains are cited as domain evidence.\n")
    f.write("- Industry and location values are assigned only when explicit terms appear in the address.\n")
    f.write("- No DNS, MX, SMTP, or mailbox-existence verification was performed.\n")


print(f"Complete. Files written to: {OUTPUT_DIR.resolve()}")
print(f"Master rows: {len(master_rows)}")
print(f"Review-flagged rows: {len(review_rows)}")
print(f"Duplicates removed: {len(duplicate_rows)}")
print(f"Invalid rows removed: {len(invalid_rows)}")