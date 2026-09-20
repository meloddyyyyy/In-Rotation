import time
from pathlib import Path

import numpy as np
import pandas as pd
from pytrends_modern import TrendReq

from candidate_io import load_candidate_pool

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
ALIAS_FILE = DATA_DIR / "trend_aliases.csv"

RAW_OUTPUT_FILE = RAW_DIR / "candidate_visual_trends.csv"
SUMMARY_OUTPUT_FILE = PROCESSED_DIR / "candidate_visual_summary.csv"

TIMEFRAME = "today 12-m"
GEO = "US"
REQUEST_DELAY = 3
MAX_RETRIES = 3

candidates, candidate_source = load_candidate_pool()
aliases = pd.read_csv(ALIAS_FILE)

candidates["Trend"] = candidates["Trend"].astype(str).str.strip().str.lower()
aliases["Trend"] = aliases["Trend"].astype(str).str.strip().str.lower()
aliases["Alias"] = aliases["Alias"].astype(str).str.strip()

if "Alias_Type" not in aliases.columns:
    aliases["Alias_Type"] = "alternate"

print(f"\nCandidate source: {candidate_source}")
print(f"Candidates to validate with Image Search: {len(candidates)}")

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
                gprop="images",
            )
            data = client.interest_over_time()
            if data is None or data.empty or alias not in data.columns:
                return None

            if "isPartial" in data.columns:
                data = data.drop(columns=["isPartial"])

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


def visual_score(growth, recent_base, status):
    if status == "New Signal":
        return 65.0

    if status != "Valid":
        return np.nan

    growth_score = 50.0 if pd.isna(growth) else 50 + 50 * np.tanh(float(growth) / 40)
    base_score = 50.0 if pd.isna(recent_base) else min(100.0, max(0.0, float(recent_base)))

    return round(float(0.75 * growth_score + 0.25 * base_score), 2)


def visual_stage(score, growth, status):
    if status in {"Low Signal", "Insufficient Data", "Fetch Failed"} or pd.isna(score):
        return "Low Signal"

    if status == "New Signal":
        return "New Visual Signal"

    if pd.notna(growth) and float(growth) <= -15:
        return "Cooling"

    if score >= 70 and pd.notna(growth) and float(growth) > 0:
        return "Emerging Visual"

    if score >= 55:
        return "Growing"

    return "Stable"


raw_rows = []
summary_rows = []

for index, candidate_row in candidates.iterrows():
    trend = candidate_row["Trend"]
    category = candidate_row.get("Category", "Unknown")

    alias_rows = aliases[aliases["Trend"] == trend].copy()
    if alias_rows.empty:
        alias_rows = pd.DataFrame(
            [{"Trend": trend, "Alias": trend, "Alias_Type": "fallback"}]
        )

    alias_rows["priority"] = alias_rows["Alias_Type"].map(
        {"canonical": 0, "alternate": 1, "fallback": 2, "broad": 3}
    ).fillna(2)
    alias_rows = alias_rows.sort_values("priority")

    selected_alias = None
    selected_data = None

    print(f"\n[{index + 1}/{len(candidates)}] Visual search: {trend}")

    for _, alias_row in alias_rows.iterrows():
        alias = str(alias_row["Alias"]).strip()
        if not alias:
            continue

        print(f"  testing alias '{alias}'")
        data = fetch_alias(alias)
        if data is None:
            continue

        usable = len(data) >= 8 and data[alias].tail(8).sum() > 0

        if selected_data is None:
            selected_alias = alias
            selected_data = data

        if usable:
            selected_alias = alias
            selected_data = data
            break

        time.sleep(REQUEST_DELAY)

    if selected_data is None:
        summary_rows.append(
            {
                "Trend": trend,
                "Category": category,
                "Visual_Search_Term_Used": pd.NA,
                "Visual_Recent_4W": pd.NA,
                "Visual_Previous_4W": pd.NA,
                "Visual_Growth": pd.NA,
                "Visual_Score": pd.NA,
                "Visual_Stage": "Fetch Failed",
                "Visual_Data_Status": "Fetch Failed",
            }
        )
        continue

    for _, data_row in selected_data.iterrows():
        raw_rows.append(
            {
                "Time": data_row["Time"],
                "Trend": trend,
                "Category": category,
                "Search_Term_Used": selected_alias,
                "Value": data_row[selected_alias],
            }
        )

    valid = selected_data.dropna(subset=["Time", selected_alias]).sort_values("Time")

    if len(valid) < 8:
        recent_4w = pd.NA
        previous_4w = pd.NA
        growth = pd.NA
        status = "Insufficient Data"
    else:
        recent_4w = float(valid[selected_alias].tail(4).mean())
        previous_4w = float(valid[selected_alias].iloc[-8:-4].mean())

        if previous_4w > 0:
            growth = ((recent_4w - previous_4w) / previous_4w) * 100
            status = "Valid" if recent_4w > 0 else "Low Signal"
        elif previous_4w == 0 and recent_4w > 0:
            growth = pd.NA
            status = "New Signal"
        else:
            growth = pd.NA
            status = "Low Signal"

    score = visual_score(growth, recent_4w, status)
    stage = visual_stage(score, growth, status)

    summary_rows.append(
        {
            "Trend": trend,
            "Category": category,
            "Visual_Search_Term_Used": selected_alias,
            "Visual_Recent_4W": round(recent_4w, 2) if pd.notna(recent_4w) else pd.NA,
            "Visual_Previous_4W": round(previous_4w, 2) if pd.notna(previous_4w) else pd.NA,
            "Visual_Growth": round(float(growth), 2) if pd.notna(growth) else pd.NA,
            "Visual_Score": score,
            "Visual_Stage": stage,
            "Visual_Data_Status": status,
        }
    )

    time.sleep(REQUEST_DELAY)

raw = pd.DataFrame(raw_rows)
summary = pd.DataFrame(summary_rows)

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
raw.to_csv(RAW_OUTPUT_FILE, index=False)
summary.to_csv(SUMMARY_OUTPUT_FILE, index=False)

print("\nSaved:", RAW_OUTPUT_FILE)
print("Saved:", SUMMARY_OUTPUT_FILE)
print("Visual candidates:", len(summary))
print("\nVisual status:")
print(summary["Visual_Data_Status"].value_counts(dropna=False))
print("\nVisual stages:")
print(summary["Visual_Stage"].value_counts(dropna=False))
