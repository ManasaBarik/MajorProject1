"""Shared vocabulary and heuristics for the civic-complaint AI layer.

The complaint model historically accumulated several duplicate category values
(``ROAD``/``ROADS``, ``WATER``/``WATER_SUPPLY``/``WATER_QUALITY``,
``STREET_LIGHT``/``STREETLIGHT``, ``WASTE_MANAGEMENT``/``GARBAGE``,
``SEWERAGE``/``SEWAGE``).  Rather than migrate live data we keep the database
values intact and expose a single *canonical* set that the AI is allowed to
return; legacy values are folded into the canonical ones on the way in.
"""

# Canonical categories the AI may return (all are valid Complaint.Category values).
CANONICAL_CATEGORIES = (
    "GARBAGE",
    "DRAINAGE",
    "SEWAGE",
    "ROAD",
    "STREETLIGHT",
    "WATER_SUPPLY",
    "SANITATION",
    "OTHER",
)

# Legacy / duplicate database values mapped onto the canonical set.
CATEGORY_ALIASES = {
    "ROADS": "ROAD",
    "WATER": "WATER_SUPPLY",
    "WATER_QUALITY": "WATER_SUPPLY",
    "STREET_LIGHT": "STREETLIGHT",
    "WASTE_MANAGEMENT": "GARBAGE",
    "SEWERAGE": "SEWAGE",
    "PARKS": "OTHER",
    "TRAFFIC": "ROAD",
    "HEALTH": "OTHER",
    "ENCROACHMENT": "OTHER",
}

PRIORITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# Keyword hints used by the offline heuristic provider (and nowhere else).
CATEGORY_KEYWORDS = {
    "GARBAGE": (
        "garbage", "trash", "waste", "dumping", "litter", "rubbish", "bin",
        "uncollected", "debris", "dump",
    ),
    "DRAINAGE": (
        "drain", "drainage", "waterlogging", "water logging", "waterlog",
        "stagnant", "clog", "clogged", "gutter", "storm water", "flood",
        "flooding", "overflowing drain", "blocked", "choked",
    ),
    "SEWAGE": (
        "sewage", "sewer", "manhole", "septic", "excreta", "faecal",
        "fecal", "toilet overflow", "sewage overflow", "smell",
    ),
    "ROAD": (
        "road", "pothole", "pavement", "footpath", "asphalt", "crack",
        "speed breaker", "tar", "damaged road", "road damage",
    ),
    "STREETLIGHT": (
        "street light", "streetlight", "street lamp", "lamp post", "lamp",
        "lighting", "dark street", "no light", "bulb",
    ),
    "WATER_SUPPLY": (
        "water supply", "no water", "water not", "pipeline", "pipe", "tap",
        "drinking water", "water pressure", "water leak", "water meter",
        "contaminated water",
    ),
    "SANITATION": (
        "sanitation", "public toilet", "toilet", "cleanliness", "sweeping",
        "sweeper", "mosquito", "hygiene", "fogging",
    ),
}

# Urgency signals used only for the offline priority estimate.
URGENT_KEYWORDS = (
    "urgent", "emergency", "danger", "dangerous", "accident", "injured",
    "collapse", "collapsed", "live wire", "electric shock", "fire", "hospital",
    "school", "children", "elderly", "disease", "outbreak", "severe",
)
HIGH_KEYWORDS = (
    "overflow", "overflowing", "sewage", "blocked", "no water", "deep",
    "large", "major", "days", "weeks", "spreading", "leak",
)

# Used only by the optional seed command to bootstrap CategoryDepartmentMapping
# from existing Department names. Administrators can edit the result freely.
CATEGORY_DEPARTMENT_HINTS = {
    "GARBAGE": ("waste", "sanitation", "solid", "health", "cleansing"),
    "DRAINAGE": ("drain", "storm", "sewer", "water", "public works"),
    "SEWAGE": ("sewer", "drain", "sanitation", "water", "public health"),
    "ROAD": ("road", "public works", "engineering", "works", "transport"),
    "STREETLIGHT": ("electric", "light", "energy", "public works", "works"),
    "WATER_SUPPLY": ("water", "supply", "utility", "public health"),
    "SANITATION": ("sanitation", "health", "waste", "cleansing"),
}
