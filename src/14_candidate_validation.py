from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_FILE = DATA_DIR / "raw" / "candidate_google_trends.csv"
EDITORIAL_SUMMARY_FILE = DATA_DIR / "processed" / "candidate_editorial_summary.csv"
EDITORIAL_FALLBACK_FILE = DATA_DIR / "trend_candidates.csv"
PINTEREST_FILE = DATA_DIR / "pinterest_signal.csv"
OUTPUT_FILE = DATA_DIR / "processed" / "candidate_validation.csv"


def safe_read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


google = safe_read(RAW_FILE)
editorial = safe_read(EDITORIAL_SUMMARY_FILE)
if editorial.empty:
    editorial = safe_read(EDITORIAL_FALLBACK_FILE)
pinterest = safe_read(PINTEREST_FILE)

if google.empty:
    raise RuntimeError(
        "candidate_google_trends.csv is missing or empty. Run 15_candidate_google_collector.py first."
    )

required = {"Time", "Trend", "Category", "Search_Term_Used", "Value", "Collection_Status"}
missing = required - set(google.columns)
if missing:
    raise ValueError(f"candidate_google_trends.csv missing columns: {sorted(missing)}")

google["Time"] = pd.to_datetime(google["Time"], errors="coerce")
google["Value"] = pd.to_numeric(google["Value"], errors="coerce")

rows = []
for trend, group in google.groupby("Trend", dropna=False):
    group = group.sort_values("Time")
    valid = group.dropna(subset=["Time", "Value"])
    category = group["Category"].dropna().iloc[0] if group["Category"].notna().any() else "Unknown"
    search_term = (
        group["Search_Term_Used"].dropna().iloc[0]
        if group["Search_Term_Used"].notna().any()
        else None
    )

    if len(valid) >= 8:
        recent_4w = valid["Value"].tail(4).mean()
        previous_4w = valid["Value"].iloc[-8:-4].mean()
        recent_base = recent_4w
        if previous_4w > 0:
            growth = ((recent_4w - previous_4w) / previous_4w) * 100
            google_status = "Valid" if recent_4w > 0 else "Low Signal"
        elif previous_4w == 0 and recent_4w > 0:
            growth = None
            google_status = "New Signal"
        else:
            growth = None
            google_status = "Low Signal"
    else:
        recent_4w = None
        previous_4w = None
        recent_base = None
        growth = None
        google_status = "Insufficient Data"

    rows.append(
        {
            "Trend": trend,
            "Category": category,
            "Google_Search_Term_Used": search_term,
            "Google_Recent_4W": round(recent_4w, 2) if pd.notna(recent_4w) else None,
            "Google_Previous_4W": round(previous_4w, 2) if pd.notna(previous_4w) else None,
            "Google_Growth": round(growth, 2) if growth is not None else None,
            "Recent_Search_Base": round(recent_base, 2) if pd.notna(recent_base) else None,
            "Google_Data_Status": google_status,
        }
    )

result = pd.DataFrame(rows)

# Prefer the dedicated editorial evidence collector; fall back to the original
# discovery output so the experimental pipeline remains non-blocking.
if not editorial.empty:
    editorial_copy = editorial.copy()

    if "Trend" not in editorial_copy.columns and "Candidate" in editorial_copy.columns:
        editorial_copy["Trend"] = editorial_copy["Candidate"]

    if "Trend" in editorial_copy.columns:
        editorial_copy["Trend"] = (
            editorial_copy["Trend"].astype(str).str.lower().str.strip()
        )
        editorial_cols = ["Trend"]
        for col in [
            "Mentions_30D",
            "Unique_Sources",
            "Authority_Score",
            "Quality_Adjusted_Mentions",
            "High_Quality_Mentions",
            "Medium_Quality_Mentions",
            "Low_Quality_Mentions",
            "Editorial_Evidence_Quality",
            "Editorial_Search_Mode",
            "Priority",
            "Latest_Mention_Days_Ago",
            "Editorial_Sources",
            "Example_Title",
            "Editorial_Collection_Status",
        ]:
            if col in editorial_copy.columns:
                editorial_cols.append(col)

        editorial_copy = editorial_copy[editorial_cols].drop_duplicates("Trend")
        result = result.merge(editorial_copy, on="Trend", how="left")

for col in [
    "Mentions_30D",
    "Unique_Sources",
    "Authority_Score",
    "Quality_Adjusted_Mentions",
    "High_Quality_Mentions",
    "Medium_Quality_Mentions",
    "Low_Quality_Mentions",
]:
    if col not in result.columns:
        result[col] = pd.NA

for col in ["Editorial_Evidence_Quality", "Editorial_Search_Mode"]:
    if col not in result.columns:
        result[col] = pd.NA

if "Editorial_Collection_Status" not in result.columns:
    result["Editorial_Collection_Status"] = pd.NA
if "Editorial_Sources" not in result.columns:
    result["Editorial_Sources"] = pd.NA
if "Latest_Mention_Days_Ago" not in result.columns:
    result["Latest_Mention_Days_Ago"] = pd.NA
if "Example_Title" not in result.columns:
    result["Example_Title"] = pd.NA

# Pinterest remains missing if there is no real Pinterest data.
result["Pinterest_Score"] = pd.NA
result["Pinterest_Stage"] = pd.NA

if not pinterest.empty:
    keyword_col = "Keyword" if "Keyword" in pinterest.columns else None
    if keyword_col and "Pinterest_Score" in pinterest.columns:
        pin = pinterest.copy()
        pin["Trend"] = pin[keyword_col].astype(str).str.lower().str.strip()
        keep = ["Trend", "Pinterest_Score"]
        if "Pinterest_Stage" in pin.columns:
            keep.append("Pinterest_Stage")
        pin = pin[keep].drop_duplicates("Trend")
        result = result.drop(columns=["Pinterest_Score", "Pinterest_Stage"], errors="ignore")
        result = result.merge(pin, on="Trend", how="left")
        if "Pinterest_Stage" not in result.columns:
            result["Pinterest_Stage"] = pd.NA

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_FILE, index=False)

print("\nSaved:", OUTPUT_FILE)
print("Candidates validated:", len(result))
print(result["Google_Data_Status"].value_counts(dropna=False))

if "Editorial_Collection_Status" in result.columns:
    print("\nEditorial status:")
    print(result["Editorial_Collection_Status"].value_counts(dropna=False))
