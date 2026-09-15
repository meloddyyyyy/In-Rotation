from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

SEED_FILE = DATA_DIR / "trend_candidates_v2.csv"
EDITORIAL_FILE = DATA_DIR / "trend_candidates.csv"
PINTEREST_RAW_FILE = DATA_DIR / "pinterest_candidates.csv"
PINTEREST_SIGNAL_FILE = DATA_DIR / "pinterest_signal.csv"
MASTER_FILE = DATA_DIR / "trend_master.csv"
OUTPUT_FILE = PROCESSED_DIR / "candidate_pool.csv"


def safe_read(path):
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def clean_text(series):
    return series.fillna("").astype(str).str.strip().str.lower()


def source_frame(df, trend_candidates, category_candidates, source_name):
    if df.empty:
        return pd.DataFrame(columns=["Trend", "Category", "Candidate_Source"])

    normalized = {str(col).strip().lower(): col for col in df.columns}
    trend_col = next(
        (normalized[name] for name in trend_candidates if name in normalized),
        None,
    )
    if trend_col is None:
        return pd.DataFrame(columns=["Trend", "Category", "Candidate_Source"])

    category_col = next(
        (normalized[name] for name in category_candidates if name in normalized),
        None,
    )

    result = pd.DataFrame()
    result["Trend"] = clean_text(df[trend_col])
    if category_col is not None:
        result["Category"] = df[category_col].fillna("Unknown").astype(str).str.strip()
    else:
        result["Category"] = "Unknown"
    result["Candidate_Source"] = source_name

    result = result[
        (result["Trend"] != "")
        & (result["Trend"] != "nan")
    ].copy()
    return result


def first_real_value(series):
    for value in series:
        if pd.notna(value) and str(value).strip() not in {"", "nan", "None"}:
            return value
    return pd.NA


def join_sources(series):
    values = []
    for value in series.dropna():
        for item in str(value).split(";"):
            item = item.strip()
            if item and item not in values:
                values.append(item)
    return "; ".join(values)


seed = safe_read(SEED_FILE)
editorial = safe_read(EDITORIAL_FILE)
pinterest_raw = safe_read(PINTEREST_RAW_FILE)
pinterest_signal = safe_read(PINTEREST_SIGNAL_FILE)
master = safe_read(MASTER_FILE)

if seed.empty:
    raise RuntimeError(f"Seed candidate file is missing or empty: {SEED_FILE}")

seed_frame = source_frame(
    seed,
    ("trend", "candidate", "keyword", "term"),
    ("category", "type", "segment"),
    "Discovery Seed",
)
editorial_frame = source_frame(
    editorial,
    ("candidate", "trend", "keyword", "term"),
    ("category", "type", "segment"),
    "Editorial Discovery",
)
pinterest_frame = source_frame(
    pinterest_raw,
    ("keyword", "trend", "candidate", "term"),
    ("category", "type", "segment"),
    "Pinterest Discovery",
)

frames = [frame for frame in [seed_frame, editorial_frame, pinterest_frame] if not frame.empty]
pool = pd.concat(frames, ignore_index=True)

# Preserve the broadest candidate universe, while keeping one row per normalized trend.
pool = (
    pool.groupby("Trend", as_index=False)
    .agg(
        Category=("Category", first_real_value),
        Candidate_Source=("Candidate_Source", join_sources),
    )
)

# Use trend_master only to improve missing categories. It does not add candidates.
if not master.empty and "Trend" in master.columns:
    master_copy = master.copy()
    master_copy["Trend"] = clean_text(master_copy["Trend"])
    if "Category" in master_copy.columns:
        master_categories = (
            master_copy[["Trend", "Category"]]
            .drop_duplicates("Trend")
            .rename(columns={"Category": "Master_Category"})
        )
        pool = pool.merge(master_categories, on="Trend", how="left")
        missing_category = pool["Category"].isna() | pool["Category"].astype(str).str.strip().isin(["", "Unknown", "nan"])
        pool.loc[missing_category, "Category"] = pool.loc[missing_category, "Master_Category"]
        pool = pool.drop(columns=["Master_Category"])

# Attach real editorial evidence when available. No synthetic values are created.
editorial_columns = [
    "Candidate",
    "Mentions_30D",
    "Unique_Sources",
    "Authority_Score",
    "Priority",
    "Sources",
    "Example_Title",
]
if not editorial.empty and "Candidate" in editorial.columns:
    ed = editorial[[col for col in editorial_columns if col in editorial.columns]].copy()
    ed["Trend"] = clean_text(ed["Candidate"])
    ed = ed.drop(columns=["Candidate"]).drop_duplicates("Trend")
    pool = pool.merge(ed, on="Trend", how="left")

# Attach Pinterest evidence only if a real signal file exists.
pool["Pinterest_Score"] = pd.NA
pool["Pinterest_Stage"] = pd.NA
if not pinterest_signal.empty:
    normalized = {str(col).strip().lower(): col for col in pinterest_signal.columns}
    keyword_col = next((normalized[name] for name in ("keyword", "trend", "candidate") if name in normalized), None)
    score_col = normalized.get("pinterest_score")
    stage_col = normalized.get("pinterest_stage")
    if keyword_col is not None and score_col is not None:
        pin = pd.DataFrame({
            "Trend": clean_text(pinterest_signal[keyword_col]),
            "Pinterest_Score_New": pd.to_numeric(pinterest_signal[score_col], errors="coerce"),
        })
        if stage_col is not None:
            pin["Pinterest_Stage_New"] = pinterest_signal[stage_col]
        pin = pin.drop_duplicates("Trend")
        pool = pool.merge(pin, on="Trend", how="left")
        pool["Pinterest_Score"] = pool["Pinterest_Score_New"]
        pool = pool.drop(columns=["Pinterest_Score_New"])
        if "Pinterest_Stage_New" in pool.columns:
            pool["Pinterest_Stage"] = pool["Pinterest_Stage_New"]
            pool = pool.drop(columns=["Pinterest_Stage_New"])

if "Mentions_30D" in pool.columns:
    pool["Editorial_Evidence"] = pool["Mentions_30D"].notna()
else:
    pool["Editorial_Evidence"] = False
pool["Pinterest_Evidence"] = pd.to_numeric(pool["Pinterest_Score"], errors="coerce").notna()

pool = pool.sort_values(["Category", "Trend"], na_position="last").reset_index(drop=True)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
pool.to_csv(OUTPUT_FILE, index=False)

print("Saved:", OUTPUT_FILE)
print("Candidate pool size:", len(pool))
print("Editorial evidence:", int(pool["Editorial_Evidence"].sum()))
print("Pinterest evidence:", int(pool["Pinterest_Evidence"].sum()))
print("No synthetic scores were created.")
