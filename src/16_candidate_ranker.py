from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INPUT_FILE = DATA_DIR / "processed" / "candidate_validation.csv"
OUTPUT_FILE = DATA_DIR / "processed" / "candidate_intelligence.csv"

if not INPUT_FILE.exists() or INPUT_FILE.stat().st_size == 0:
    raise RuntimeError(
        "candidate_validation.csv is missing or empty. Run 14_candidate_validation.py first."
    )

try:
    df = pd.read_csv(INPUT_FILE)
except pd.errors.EmptyDataError as error:
    raise RuntimeError("candidate_validation.csv is empty.") from error

required = {
    "Trend",
    "Category",
    "Google_Search_Term_Used",
    "Google_Recent_4W",
    "Google_Growth",
    "Google_Data_Status",
    "Recent_Search_Base",
}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"candidate_validation.csv missing columns: {sorted(missing)}")


def google_component(row):
    status = row.get("Google_Data_Status")
    growth = row.get("Google_Growth")
    base = row.get("Recent_Search_Base")

    if status == "Valid":
        growth_score = 50.0 if pd.isna(growth) else 50 + 50 * np.tanh(float(growth) / 30)
        base_score = 50.0 if pd.isna(base) else min(100.0, max(0.0, float(base)))
        return round(0.7 * growth_score + 0.3 * base_score, 2)

    if status == "New Signal":
        return 60.0

    if status in {"Low Signal", "Insufficient Data"}:
        return np.nan

    return np.nan


def editorial_component(row):
    mentions = row.get("Mentions_30D")
    sources = row.get("Unique_Sources")
    authority = row.get("Authority_Score")

    if pd.isna(mentions) and pd.isna(sources) and pd.isna(authority):
        return np.nan

    mentions = 0 if pd.isna(mentions) else float(mentions)
    sources = 0 if pd.isna(sources) else float(sources)
    authority = 0 if pd.isna(authority) else float(authority)

    score = min(100.0, mentions * 8 + sources * 18 + authority * 2)
    return round(score, 2)


df["Google_Score"] = df.apply(google_component, axis=1)
df["Editorial_Score"] = df.apply(editorial_component, axis=1)

df["Pinterest_Score"] = pd.to_numeric(df.get("Pinterest_Score"), errors="coerce")


def combine_scores(row):
    components = {
        "google": row.get("Google_Score"),
        "editorial": row.get("Editorial_Score"),
        "pinterest": row.get("Pinterest_Score"),
    }
    weights = {"google": 0.5, "editorial": 0.3, "pinterest": 0.2}

    usable = {k: v for k, v in components.items() if pd.notna(v)}
    if not usable:
        return np.nan

    weight_sum = sum(weights[k] for k in usable)
    return round(sum(usable[k] * weights[k] for k in usable) / weight_sum, 2)


df["Candidate_Score"] = df.apply(combine_scores, axis=1)


def evidence_count(row):
    count = 0
    if pd.notna(row.get("Google_Score")):
        count += 1
    if pd.notna(row.get("Editorial_Score")):
        count += 1
    if pd.notna(row.get("Pinterest_Score")):
        count += 1
    return count


df["Evidence_Count"] = df.apply(evidence_count, axis=1)


def classify(row):
    score = row.get("Candidate_Score")
    evidence = row.get("Evidence_Count", 0)
    google_status = row.get("Google_Data_Status")
    editorial = row.get("Editorial_Score")
    pinterest = row.get("Pinterest_Score")

    if evidence == 0 or pd.isna(score):
        return "LOW EVIDENCE"

    non_google_strength = max(
        [v for v in [editorial, pinterest] if pd.notna(v)] or [np.nan]
    )

    if google_status in {"Low Signal", "Insufficient Data"} and pd.notna(non_google_strength):
        if non_google_strength >= 60:
            return "NICHE / EARLY SIGNAL"

    if evidence >= 2 and score >= 70:
        return "EMERGING"

    if score >= 50:
        return "WATCH"

    if evidence == 1:
        return "LOW EVIDENCE"

    return "REJECT"


df["Candidate_Status"] = df.apply(classify, axis=1)

output_columns = [
    "Trend",
    "Category",
    "Google_Search_Term_Used",
    "Google_Recent_4W",
    "Google_Growth",
    "Google_Data_Status",
    "Mentions_30D",
    "Unique_Sources",
    "Editorial_Score",
    "Pinterest_Score",
    "Evidence_Count",
    "Google_Score",
    "Candidate_Score",
    "Candidate_Status",
]

for column in output_columns:
    if column not in df.columns:
        df[column] = pd.NA

result = df[output_columns].sort_values(
    ["Candidate_Status", "Candidate_Score"],
    ascending=[True, False],
    na_position="last",
)

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
result.to_csv(OUTPUT_FILE, index=False)

print("\nSaved:", OUTPUT_FILE)
print("Total candidates:", len(result))
print("\nStatus counts:")
print(result["Candidate_Status"].value_counts(dropna=False))
