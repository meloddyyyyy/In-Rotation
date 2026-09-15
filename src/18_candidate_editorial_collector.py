import html
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
import pandas as pd
import requests

from candidate_io import load_candidate_pool

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

ALIAS_FILE = DATA_DIR / "trend_aliases.csv"
RAW_OUTPUT_FILE = RAW_DIR / "candidate_editorial_evidence.csv"
SUMMARY_OUTPUT_FILE = PROCESSED_DIR / "candidate_editorial_summary.csv"

WINDOW_DAYS = 30
REQUEST_DELAY = 0.6
MAX_RETRIES = 3

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
    "The Zoe Report": 2.0,
    "Hypebae": 2.0,
    "Highsnobiety": 2.0,
    "GQ": 2.0,
    "Nylon": 2.0,
    "Dazed": 2.0,
    "i-D": 2.0,
}


def safe_read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def normalize_text(value):
    value = html.unescape(str(value or "")).lower()
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("-", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def canonical_source(source_text):
    source_lower = str(source_text or "").lower()
    for source_name, weight in SOURCE_WEIGHTS.items():
        if source_name.lower() in source_lower:
            return source_name, weight
    return None, None


def extract_source(entry):
    if hasattr(entry, "source"):
        try:
            source_name = entry.source.title
            if source_name:
                return source_name
        except Exception:
            pass

    title = str(getattr(entry, "title", ""))
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()

    return "Unknown"


def build_terms(trend, aliases):
    terms = [trend]

    if not aliases.empty:
        subset = aliases[aliases["Trend"] == trend].copy()
        if not subset.empty:
            subset["priority"] = subset["Alias_Type"].map(
                {"canonical": 0, "alternate": 1, "fallback": 2, "broad": 3}
            ).fillna(2)
            subset = subset[subset["Alias_Type"].fillna("") != "broad"]
            subset = subset.sort_values("priority")

            for alias in subset["Alias"]:
                alias = str(alias).strip()
                if alias and alias.lower() not in {term.lower() for term in terms}:
                    terms.append(alias)
                if len(terms) >= 3:
                    break

    return terms


def build_query(terms):
    quoted = [f'"{term}"' for term in terms]
    phrase_query = " OR ".join(quoted)
    return f"({phrase_query}) (fashion OR style)"


def fetch_rss(query):
    encoded = quote_plus(query)
    url = (
        "https://news.google.com/rss/search?"
        f"q={encoded}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )
    headers = {"User-Agent": "Mozilla/5.0"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()
            return feedparser.parse(response.content)
        except requests.RequestException as error:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 2)

    return None


def entry_published(entry):
    if not hasattr(entry, "published_parsed") or entry.published_parsed is None:
        return None
    return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)


def entry_matches_terms(entry, terms):
    title = getattr(entry, "title", "")
    summary = getattr(entry, "summary", "")
    combined = normalize_text(f"{title} {summary}")

    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and re.search(
            rf"\b{re.escape(normalized_term)}\b",
            combined,
        ):
            return True
    return False


candidates, candidate_source = load_candidate_pool()
aliases = safe_read(ALIAS_FILE)

if not aliases.empty:
    required_alias_columns = {"Trend", "Alias"}
    missing_alias_columns = required_alias_columns - set(aliases.columns)
    if missing_alias_columns:
        raise ValueError(
            f"trend_aliases.csv missing columns: {sorted(missing_alias_columns)}"
        )

    aliases["Trend"] = aliases["Trend"].astype(str).str.strip().str.lower()
    aliases["Alias"] = aliases["Alias"].astype(str).str.strip()
    if "Alias_Type" not in aliases.columns:
        aliases["Alias_Type"] = "alternate"

print(f"\nCandidate source: {candidate_source}")
print(f"Candidates to check: {len(candidates)}")

today = datetime.now(timezone.utc)
evidence_rows = []
candidate_status = {}

for index, candidate_row in candidates.iterrows():
    trend = candidate_row["Trend"]
    category = candidate_row.get("Category", "Unknown")
    terms = build_terms(trend, aliases)
    query = build_query(terms)

    print(f"\n[{index + 1}/{len(candidates)}] Editorial search: {trend}")

    feed = fetch_rss(query)
    if feed is None:
        candidate_status[trend] = "Fetch Failed"
        continue

    candidate_status[trend] = "No Evidence"
    seen_articles = set()

    for entry in feed.entries:
        published = entry_published(entry)
        if published is None:
            continue

        age_days = (today - published).days
        if age_days < 0 or age_days > WINDOW_DAYS:
            continue

        raw_source = extract_source(entry)
        source, source_weight = canonical_source(raw_source)
        if source is None:
            continue

        if not entry_matches_terms(entry, terms):
            continue

        title = str(getattr(entry, "title", "")).strip()
        url = str(getattr(entry, "link", "")).strip()
        article_key = f"{source.lower()}|{normalize_text(title)}"

        if article_key in seen_articles:
            continue
        seen_articles.add(article_key)

        evidence_rows.append(
            {
                "Trend": trend,
                "Category": category,
                "Search_Query": query,
                "Matched_Terms": "; ".join(terms),
                "Source": source,
                "Source_Weight": source_weight,
                "Published": published.isoformat(),
                "Age_Days": age_days,
                "Title": title,
                "URL": url,
            }
        )
        candidate_status[trend] = "Confirmed"

    time.sleep(REQUEST_DELAY)

evidence_columns = [
    "Trend",
    "Category",
    "Search_Query",
    "Matched_Terms",
    "Source",
    "Source_Weight",
    "Published",
    "Age_Days",
    "Title",
    "URL",
]
evidence = pd.DataFrame(evidence_rows, columns=evidence_columns)

summary_rows = []

for _, candidate_row in candidates.iterrows():
    trend = candidate_row["Trend"]
    category = candidate_row.get("Category", "Unknown")
    subset = evidence[evidence["Trend"] == trend] if not evidence.empty else pd.DataFrame()

    if subset.empty:
        summary_rows.append(
            {
                "Trend": trend,
                "Category": category,
                "Mentions_30D": pd.NA,
                "Unique_Sources": pd.NA,
                "Authority_Score": pd.NA,
                "Latest_Mention_Days_Ago": pd.NA,
                "Editorial_Sources": pd.NA,
                "Example_Title": pd.NA,
                "Editorial_Collection_Status": candidate_status.get(
                    trend, "No Evidence"
                ),
            }
        )
        continue

    unique_source_weights = subset.groupby("Source")["Source_Weight"].max().sum()

    summary_rows.append(
        {
            "Trend": trend,
            "Category": category,
            "Mentions_30D": int(len(subset)),
            "Unique_Sources": int(subset["Source"].nunique()),
            "Authority_Score": round(float(unique_source_weights), 2),
            "Latest_Mention_Days_Ago": int(subset["Age_Days"].min()),
            "Editorial_Sources": "; ".join(sorted(subset["Source"].unique())),
            "Example_Title": subset.sort_values("Age_Days").iloc[0]["Title"],
            "Editorial_Collection_Status": "Confirmed",
        }
    )

summary = pd.DataFrame(summary_rows)

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
evidence.to_csv(RAW_OUTPUT_FILE, index=False)
summary.to_csv(SUMMARY_OUTPUT_FILE, index=False)

confirmed = int((summary["Editorial_Collection_Status"] == "Confirmed").sum())
failed = int((summary["Editorial_Collection_Status"] == "Fetch Failed").sum())

print("\nSaved:", RAW_OUTPUT_FILE)
print("Saved:", SUMMARY_OUTPUT_FILE)
print(f"Editorial coverage: {confirmed}/{len(summary)}")
print(f"Fetch failed: {failed}")
