import time
from pathlib import Path

import pandas as pd
from pytrends_modern import TrendReq

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CANDIDATE_FILE = DATA_DIR / "trend_candidates_v2.csv"
ALIAS_FILE = DATA_DIR / "trend_aliases.csv"
OUTPUT_FILE = RAW_DIR / "candidate_google_trends.csv"

TIMEFRAME = "today 12-m"
GEO = "US"
REQUEST_DELAY = 3
MAX_RETRIES = 3

candidates = pd.read_csv(CANDIDATE_FILE)
aliases = pd.read_csv(ALIAS_FILE)

candidates["Trend"] = candidates["Trend"].astype(str).str.strip().str.lower()
aliases["Trend"] = aliases["Trend"].astype(str).str.strip().str.lower()
aliases["Alias"] = aliases["Alias"].astype(str).str.strip()

client = TrendReq(
    hl="en-US",
    tz=360,
    timeout=(10, 30),
    retries=2,
    backoff_factor=0.5,
)


def fetch_alias(alias):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client.build_payload(
                kw_list=[alias],
                timeframe=TIMEFRAME,
                geo=GEO,
                gprop="",
            )
            data = client.interest_over_time()
            if data is None or data.empty or alias not in data.columns:
                return None
            data = data.reset_index()
            data = data.rename(columns={data.columns[0]: "Time"})
            data["Time"] = pd.to_datetime(data["Time"], errors="coerce")
            data = data.dropna(subset=["Time"])
            data[alias] = pd.to_numeric(data[alias], errors="coerce").fillna(0)
            return data[["Time", alias]]
        except Exception as error:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed for '{alias}': {error}")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 6)
    return None


rows = []

for _, candidate_row in candidates.iterrows():
    trend = candidate_row["Trend"]
    category = candidate_row.get("Category", "Unknown")
    alias_rows = aliases[aliases["Trend"] == trend].copy()

    if alias_rows.empty:
        alias_rows = pd.DataFrame(
            [{"Trend": trend, "Alias": trend, "Alias_Type": "fallback"}]
        )

    selected_alias = None
    selected_data = None

    # Try narrow/explicit aliases first; broad aliases last.
    alias_rows["priority"] = alias_rows["Alias_Type"].map(
        {"canonical": 0, "alternate": 1, "fallback": 2, "broad": 3}
    ).fillna(2)
    alias_rows = alias_rows.sort_values("priority")

    for _, alias_row in alias_rows.iterrows():
        alias = alias_row["Alias"]
        print(f"\n{trend}: testing alias '{alias}'")
        data = fetch_alias(alias)
        if data is None:
            continue

        values = data[alias]
        usable = len(values) >= 8 and values.tail(8).sum() > 0
        if usable:
            selected_alias = alias
            selected_data = data
            break

        # Keep the first returned series as a fallback so zero evidence is recorded honestly.
        if selected_data is None:
            selected_alias = alias
            selected_data = data

        time.sleep(REQUEST_DELAY)

    if selected_data is None:
        rows.append(
            {
                "Time": pd.NaT,
                "Trend": trend,
                "Category": category,
                "Search_Term_Used": None,
                "Value": None,
                "Collection_Status": "Fetch Failed",
            }
        )
        continue

    status = "Usable" if selected_data[selected_alias].tail(8).sum() > 0 else "Low Signal"

    for _, data_row in selected_data.iterrows():
        rows.append(
            {
                "Time": data_row["Time"],
                "Trend": trend,
                "Category": category,
                "Search_Term_Used": selected_alias,
                "Value": data_row[selected_alias],
                "Collection_Status": status,
            }
        )

    time.sleep(REQUEST_DELAY)

result = pd.DataFrame(rows)
RAW_DIR.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_FILE, index=False)

print("\nSaved:", OUTPUT_FILE)
print("Candidate trends:", result["Trend"].nunique())
print(result.groupby("Collection_Status")["Trend"].nunique())
