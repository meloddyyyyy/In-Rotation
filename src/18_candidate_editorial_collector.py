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

TREND_CUES = {
    "trend", "trends", "trending", "comeback", "return", "returns",
    "returning", "revival", "rise", "rising", "everywhere", "popular",
    "season", "runway", "runways", "street style", "fashion week",
    "must have", "must-have", "biggest", "new wave", "next big",
    "taking over",
}

STYLE_CUES = {
    "fashion", "style", "styling", "wear", "wardrobe", "outfit", "look",
    "looks", "fall", "autumn", "winter", "spring", "summer",
}

WEAK_ARTICLE_CUES = {
    "red carpet", "steps out", "stepped out", "arrives", "wore", "wears",
    "spotted", "celebrity", "shopping", "sale", "amazon", "deal", "deals",
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


def contains_any(text, cues):
    normalized = normalize_text(text)
    return any(normalize_text(cue) in normalized for cue in cues)


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


def build_query(terms, mode):
    quoted = [f'"{term}"' for term in terms]
    phrase_query = " OR ".join(quoted)
    if mode == "strict":
        return f"({phrase_query}) (fashion OR style)"
    if mode == "relaxed":
        return f"({phrase_query})"
    raise ValueError(f"Unknown search mode: {mode}")


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


def matching_terms(entry, terms):
    title = normalize_text(getattr(entry, "title", ""))
    summary = normalize_text(getattr(entry, "summary", ""))
    combined = f"{title} {summary}".strip()
    matches = []
    for term in terms:
        normalized_term = normalize_text(term)
        if normalized_term and re.search(
            rf"\b{re.escape(normalized_term)}\b", combined
        ):
            matches.append(term)
    return matches


def match_location(entry, matched_terms):
    title = normalize_text(getattr(entry, "title", ""))
    for term in matched_terms:
        normalized_term = normalize_text(term)
        if normalized_term and re.search(
            rf"\b{re.escape(normalized_term)}\b", title
        ):
            return "Title"
    return "Summary"


def classify_evidence(entry, matched_terms):
    title = str(getattr(entry, "title", ""))
    summary = str(getattr(entry, "summary", ""))
    combined = f"{title} {summary}"

    location = match_location(entry, matched_terms)
    has_trend_cue = contains_any(combined, TREND_CUES)
    has_style_cue = contains_any(combined, STYLE_CUES)
    has_weak_cue = contains_any(title, WEAK_ARTICLE_CUES)

    if location == "Title" and has_trend_cue and not has_weak_cue:
        return "HIGH", 1.0
    if has_trend_cue:
        return "MEDIUM", 0.65
    if location == "Title" and has_style_cue and not has_weak_cue:
        return "MEDIUM", 0.65
    return "LOW", 0.25


def collect_evidence(feed, trend, category, terms, query, search_mode, today, seen_articles):
    rows = []
    if feed is None:
        return rows

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

        matched = matching_terms(entry, terms)
        if not matched:
            continue

        title = str(getattr(entry, "title", "")).strip()
        url = str(getattr(entry, "link", "")).strip()
        article_key = f"{source.lower()}|{normalize_text(title)}"
        if article_key in seen_articles:
            continue
        seen_articles.add(article_key)

        quality, quality_weight = classify_evidence(entry, matched)
        rows.append(
            {
                "Trend": trend,
                "Category": category,
                "Search_Mode": search_mode.title(),
                "Search_Query": query,
                "Matched_Terms": "; ".join(matched),
                "Match_Location": match_location(entry, matched),
                "Source": source,
                "Source_Weight": source_weight,
                "Published": published.isoformat(),
                "Age_Days": age_days,
                "Evidence_Quality": quality,
                "Quality_Weight": quality_weight,
                "Title": title,
                "URL": url,
            }
        )
    return rows


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
candidate_search_mode = {}

for index, candidate_row in candidates.iterrows():
    trend = candidate_row["Trend"]
    category = candidate_row.get("Category", "Unknown")
    terms = build_terms(trend, aliases)
    seen_articles = set()

    print(f"\n[{index + 1}/{len(candidates)}] Editorial search: {trend}")

    strict_query = build_query(terms, "strict")
    strict_feed = fetch_rss(strict_query)
    if strict_feed is None:
        candidate_status[trend] = "Fetch Failed"
        candidate_search_mode[trend] = "Strict Failed"
        continue

    strict_rows = collect_evidence(
        strict_feed, trend, category, terms, strict_query, "strict", today, seen_articles
    )

    if strict_rows:
        evidence_rows.extend(strict_rows)
        candidate_status[trend] = "Confirmed"
        candidate_search_mode[trend] = "Strict"
        time.sleep(REQUEST_DELAY)
        continue

    relaxed_query = build_query(terms, "relaxed")
    relaxed_feed = fetch_rss(relaxed_query)
    if relaxed_feed is None:
        candidate_status[trend] = "Fetch Failed"
        candidate_search_mode[trend] = "Relaxed Failed"
        time.sleep(REQUEST_DELAY)
        continue

    relaxed_rows = collect_evidence(
        relaxed_feed, trend, category, terms, relaxed_query, "relaxed", today, seen_articles
    )

    if relaxed_rows:
        evidence_rows.extend(relaxed_rows)
        candidate_status[trend] = "Confirmed"
        candidate_search_mode[trend] = "Relaxed"
    else:
        candidate_status[trend] = "No Evidence"
        candidate_search_mode[trend] = "Relaxed"

    time.sleep(REQUEST_DELAY)

evidence_columns = [
    "Trend", "Category", "Search_Mode", "Search_Query", "Matched_Terms",
    "Match_Location", "Source", "Source_Weight", "Published", "Age_Days",
    "Evidence_Quality", "Quality_Weight", "Title", "URL",
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
                "Quality_Adjusted_Mentions": pd.NA,
                "High_Quality_Mentions": pd.NA,
                "Medium_Quality_Mentions": pd.NA,
                "Low_Quality_Mentions": pd.NA,
                "Editorial_Evidence_Quality": pd.NA,
                "Latest_Mention_Days_Ago": pd.NA,
                "Editorial_Sources": pd.NA,
                "Example_Title": pd.NA,
                "Editorial_Search_Mode": candidate_search_mode.get(trend, pd.NA),
                "Editorial_Collection_Status": candidate_status.get(trend, "No Evidence"),
            }
        )
        continue

    unique_source_weights = subset.groupby("Source")["Source_Weight"].max().sum()
    high_count = int((subset["Evidence_Quality"] == "HIGH").sum())
    medium_count = int((subset["Evidence_Quality"] == "MEDIUM").sum())
    low_count = int((subset["Evidence_Quality"] == "LOW").sum())
    quality_adjusted_mentions = round(float(subset["Quality_Weight"].sum()), 2)
    strong_mentions = high_count + medium_count
    unique_sources = int(subset["Source"].nunique())

    if high_count >= 2 or (unique_sources >= 2 and strong_mentions >= 2):
        overall_quality = "STRONG"
    elif high_count >= 1 or strong_mentions >= 2:
        overall_quality = "MODERATE"
    else:
        overall_quality = "WEAK"

    best_example = (
        subset.assign(
            _quality_rank=subset["Evidence_Quality"].map(
                {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
            )
        )
        .sort_values(["_quality_rank", "Age_Days"])
        .iloc[0]
    )

    summary_rows.append(
        {
            "Trend": trend,
            "Category": category,
            "Mentions_30D": int(len(subset)),
            "Unique_Sources": unique_sources,
            "Authority_Score": round(float(unique_source_weights), 2),
            "Quality_Adjusted_Mentions": quality_adjusted_mentions,
            "High_Quality_Mentions": high_count,
            "Medium_Quality_Mentions": medium_count,
            "Low_Quality_Mentions": low_count,
            "Editorial_Evidence_Quality": overall_quality,
            "Latest_Mention_Days_Ago": int(subset["Age_Days"].min()),
            "Editorial_Sources": "; ".join(sorted(subset["Source"].unique())),
            "Example_Title": best_example["Title"],
            "Editorial_Search_Mode": candidate_search_mode.get(trend, pd.NA),
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
strong = int((summary["Editorial_Evidence_Quality"] == "STRONG").sum())
moderate = int((summary["Editorial_Evidence_Quality"] == "MODERATE").sum())
weak = int((summary["Editorial_Evidence_Quality"] == "WEAK").sum())
relaxed = int((summary["Editorial_Search_Mode"] == "Relaxed").sum())

print("\nSaved:", RAW_OUTPUT_FILE)
print("Saved:", SUMMARY_OUTPUT_FILE)
print(f"Editorial coverage: {confirmed}/{len(summary)}")
print(f"Strong evidence: {strong}")
print(f"Moderate evidence: {moderate}")
print(f"Weak evidence: {weak}")
print(f"Relaxed-search candidates: {relaxed}")
print(f"Fetch failed: {failed}")
