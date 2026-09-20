import pandas as pd
import feedparser
import requests
import time
import re

from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime, timezone
from collections import defaultdict


# ==================================================
# 1. Paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

TREND_MASTER_FILE = (
    DATA_DIR
    / "trend_master.csv"
)

OUTPUT_FILE = (
    DATA_DIR
    / "trend_candidates.csv"
)


# ==================================================
# 2. Load existing trend universe
# ==================================================

trend_master = pd.read_csv(
    TREND_MASTER_FILE
)

existing_trends = set(
    trend_master["Trend"]
    .astype(str)
    .str.lower()
    .str.strip()
)


# ==================================================
# 3. Discovery queries
# ==================================================

DISCOVERY_QUERIES = [

    "2026 fashion trends",
    "fall 2026 fashion trends",

    "shoe trends",
    "footwear trends",

    "bag trends",
    "handbag trends",

    "jewelry trends",

    "dress trends",
    "denim trends",

    "street style trends",

    "fashion accessories trends"

]


# ==================================================
# 4. Fashion media sources
# ==================================================

# Higher number = more weight

SOURCE_WEIGHTS = {

    "Vogue": 3.0,
    "Who What Wear": 3.0,
    "WWD": 3.0,
    "ELLE": 3.0,
    "Harper's BAZAAR": 3.0,

    "Fashionista": 2.5,
    "Refinery29": 2.5,
    "InStyle": 2.5,
    "Glamour": 2.5,
    "The Cut": 2.5,
    "Marie Claire": 2.5,

    "Hypebae": 2.0,
    "Highsnobiety": 2.0,
    "GQ": 2.0

}


def get_source_weight(source):

    source_lower = source.lower()

    for name, weight in SOURCE_WEIGHTS.items():

        if name.lower() in source_lower:
            return weight

    return 0


# ==================================================
# 5. Product vocabulary
# ==================================================

# Map variants/plurals to a consistent form

PRODUCT_NOUNS = {

    # Shoes
    "flat": "flats",
    "flats": "flats",
    "heel": "heels",
    "heels": "heels",
    "pump": "pumps",
    "pumps": "pumps",
    "loafer": "loafers",
    "loafers": "loafers",
    "sneaker": "sneakers",
    "sneakers": "sneakers",
    "boot": "boots",
    "boots": "boots",
    "sandal": "sandals",
    "sandals": "sandals",
    "mule": "mules",
    "mules": "mules",
    "clog": "clogs",
    "clogs": "clogs",
    "shoe": "shoes",
    "shoes": "shoes",

    # Apparel
    "pants": "pants",
    "jeans": "jeans",
    "shorts": "shorts",

    "skirt": "skirt",
    "skirts": "skirt",

    "dress": "dress",
    "dresses": "dress",

    "top": "top",
    "tops": "top",

    "blouse": "blouse",
    "blouses": "blouse",

    "camisole": "camisole",
    "camisoles": "camisole",

    "jacket": "jacket",
    "jackets": "jacket",

    "coat": "coat",
    "coats": "coat",

    "blazer": "blazer",
    "blazers": "blazer",

    "cardigan": "cardigan",
    "cardigans": "cardigan",

    # Bags
    "bag": "bag",
    "bags": "bag",

    "tote": "tote",
    "totes": "tote",

    "clutch": "clutch",
    "clutches": "clutch",

    # Jewelry
    "necklace": "necklace",
    "necklaces": "necklace",

    "earring": "earrings",
    "earrings": "earrings",

    "bracelet": "bracelet",
    "bracelets": "bracelet",

    "ring": "ring",
    "rings": "ring",

    "jewelry": "jewelry",

    # Accessories
    "belt": "belt",
    "belts": "belt",

    "scarf": "scarf",
    "scarves": "scarf",

    "sunglasses": "sunglasses"

}


# ==================================================
# 6. Fashion descriptors
# ==================================================

# V1 is deliberately precision-first.
# We would rather miss some candidates
# than return nonsense.

FASHION_DESCRIPTORS = {

    # Shapes / silhouettes
    "ballet",
    "kitten",
    "slingback",
    "mary",
    "jane",
    "square",
    "pointed",
    "round",

    "barrel",
    "capri",
    "bermuda",
    "bubble",
    "peplum",

    "oversized",
    "mini",
    "micro",
    "maxi",
    "cropped",

    "east",
    "west",
    "bowling",
    "bucket",
    "crescent",
    "pouch",

    "chunky",
    "sculptural",
    "statement",
    "pendant",
    "charm",

    # Materials
    "mesh",
    "suede",
    "satin",
    "lace",
    "leather",
    "denim",
    "sheer",
    "silk",
    "velvet",

    # Metallic / jewelry
    "silver",
    "gold",
    "metallic",
    "mixed",
    "two",
    "tone",

    # Prints
    "polka",
    "dot",
    "leopard",
    "zebra",
    "floral",
    "plaid",
    "striped",

    # Colors
    "yellow",
    "butter",
    "burgundy",
    "brown",
    "red",
    "pink",
    "blue",
    "green",
    "white",
    "black",

    # Aesthetic modifiers
    "romantic",
    "boho",
    "minimalist",
    "sporty",
    "utility",

    # Fit / rise
    "low",
    "high",
    "wide",
    "slim",
    "straight"
}

INVALID_CANDIDATES = {
    "two shoes",
    "low top",
    "high top",
}


def is_valid_candidate(candidate):
    candidate = str(candidate).strip().lower()

    if candidate in INVALID_CANDIDATES:
        return False

    # Numeric-like headline fragments such as "two shoe styles" are not trends.
    # Keep the legitimate fashion phrase "two tone ...".
    if candidate.startswith("two ") and not candidate.startswith("two tone "):
        return False

    return True


# ==================================================
# 7. RSS fetch
# ==================================================

def fetch_rss(query):

    encoded_query = quote_plus(
        query
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded_query}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()

            return feedparser.parse(
                response.content
            )

        except requests.RequestException as error:

            print(
                f"Attempt {attempt + 1} failed:"
            )

            print(error)

            time.sleep(2)

    return None


# ==================================================
# 8. Clean title
# ==================================================

def clean_title(title):

    title = title.lower()

    # Remove punctuation
    title = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        title
    )

    # Convert hyphens to spaces
    title = title.replace(
        "-",
        " "
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    )

    return title.strip()


# ==================================================
# 9. Extract meaningful fashion phrases
# ==================================================

def extract_candidates(title):

    words = title.split()

    candidates = []

    for i, word in enumerate(words):

        if word not in PRODUCT_NOUNS:
            continue

        canonical_noun = PRODUCT_NOUNS[word]

        descriptors = []

        # Look backwards up to 3 words.
        #
        # IMPORTANT:
        # Only accept words from the
        # fashion descriptor vocabulary.

        for distance in range(1, 4):

            position = i - distance

            if position < 0:
                break

            previous_word = words[position]

            if previous_word in FASHION_DESCRIPTORS:

                descriptors.insert(
                    0,
                    previous_word
                )

            else:

                break

        # Product noun alone is too generic
        if len(descriptors) == 0:
            continue

        candidate = (
            " ".join(descriptors)
            + " "
            + canonical_noun
        )

        # Reject numbers
        if any(
            character.isdigit()
            for character in candidate
        ):
            continue

        if not is_valid_candidate(candidate):
            continue

        candidates.append(
            candidate
        )

    return list(
        set(candidates)
    )


# ==================================================
# 10. Candidate storage
# ==================================================

candidate_data = defaultdict(
    lambda: {

        "mentions": 0,

        "sources": set(),

        "source_weight": 0,

        "titles": [],

        "latest_age": 999

    }
)


today = datetime.now(
    timezone.utc
)


# ==================================================
# 11. Search articles
# ==================================================

# De-duplicate the same article across different discovery queries.
# Previously the same headline could be counted once under "shoe trends"
# and again under "footwear trends", artificially creating 2 mentions.
global_seen_titles = set()

for query in DISCOVERY_QUERIES:

    print(
        f"\nSearching: {query}"
    )

    feed = fetch_rss(
        query
    )

    if feed is None:
        continue

    for article in feed.entries:

        if not hasattr(
            article,
            "published_parsed"
        ):
            continue

        published = datetime(
            *article.published_parsed[:6],
            tzinfo=timezone.utc
        )

        age_days = (
            today
            - published
        ).days

        # Use 30 days instead of 14
        if (
            age_days < 0
            or age_days > 30
        ):
            continue

        source = "Unknown"

        if hasattr(
            article,
            "source"
        ):

            try:

                source = (
                    article.source.title
                )

            except Exception:

                pass

        # ------------------------------------------
        # Only keep recognized fashion publications
        # ------------------------------------------

        source_weight = get_source_weight(
            source
        )

        if source_weight == 0:
            continue

        title = clean_title(
            article.title
        )

        # Remove duplicate headlines

        unique_key = (
            source.lower()
            + "|"
            + title
        )

        if unique_key in global_seen_titles:
            continue

        global_seen_titles.add(
            unique_key
        )

        candidates = extract_candidates(
            title
        )

        for candidate in candidates:

            if candidate in existing_trends:
                continue

            info = candidate_data[
                candidate
            ]

            info["mentions"] += 1

            info["sources"].add(
                source
            )

            info["source_weight"] += (
                source_weight
            )

            info["titles"].append(
                article.title
            )

            info["latest_age"] = min(
                info["latest_age"],
                age_days
            )


# ==================================================
# 12. Build candidate table
# ==================================================

rows = []


for candidate, info in candidate_data.items():

    mentions = info[
        "mentions"
    ]

    unique_sources = len(
        info["sources"]
    )

    authority_score = info[
        "source_weight"
    ]

    latest_age = info[
        "latest_age"
    ]


    # ----------------------------------------------
    # Candidate score
    #
    # Cross-source confirmation matters most.
    # ----------------------------------------------

    candidate_score = (

        unique_sources * 4

        +

        mentions * 1.5

        +

        authority_score

        +

        max(
            0,
            10 - latest_age
        ) * 0.3

    )


    # ----------------------------------------------
    # Minimum evidence
    # ----------------------------------------------

    if (
        mentions < 2
        and unique_sources < 2
    ):
        continue


    # ----------------------------------------------
    # Priority
    # ----------------------------------------------

    if (
        unique_sources >= 4
        and candidate_score >= 20
    ):

        priority = "High"


    elif (
        unique_sources >= 2
        and candidate_score >= 10
    ):

        priority = "Medium"


    else:

        priority = "Low"


    rows.append(
        {

            "Candidate":
                candidate,

            "Candidate_Score":
                round(
                    candidate_score,
                    2
                ),

            "Mentions_30D":
                mentions,

            "Unique_Sources":
                unique_sources,

            "Authority_Score":
                round(
                    authority_score,
                    2
                ),

            "Latest_Mention_Days_Ago":
                latest_age,

            "Priority":
                priority,

            "Sources":
                "; ".join(
                    sorted(
                        info["sources"]
                    )
                ),

            "Example_Title":
                info["titles"][0],

            "Search_Validation":
                "Pending",

            "Status":
                "Candidate"

        }
    )


candidate_df = pd.DataFrame(
    rows
)


# ==================================================
# 13. Sort
# ==================================================

if not candidate_df.empty:

    candidate_df = (
        candidate_df
        .sort_values(
            "Candidate_Score",
            ascending=False
        )
        .reset_index(
            drop=True
        )
    )


# ==================================================
# 14. Display
# ==================================================

print(
    "\n========== TREND CANDIDATES =========="
)


if candidate_df.empty:

    print(
        "No qualified candidates found."
    )


else:

    print(
        candidate_df[
            [
                "Candidate",
                "Candidate_Score",
                "Mentions_30D",
                "Unique_Sources",
                "Priority"
            ]
        ]
        .head(25)
        .to_string(
            index=False
        )
    )


# ==================================================
# 15. Save
# ==================================================

candidate_df.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)