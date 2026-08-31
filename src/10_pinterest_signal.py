import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime


# ==================================================
# 1. Paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

PINTEREST_FILE = DATA_DIR / "pinterest_candidates.csv"
TREND_MASTER_FILE = DATA_DIR / "trend_master.csv"

OUTPUT_FILE = DATA_DIR / "pinterest_signal.csv"


# ==================================================
# 2. Create template if file does not exist
# ==================================================

if not PINTEREST_FILE.exists():

    template = pd.DataFrame(
        columns=[
            "Keyword",
            "Category",
            "WoW_Growth",
            "MoM_Growth",
            "YoY_Growth",
            "Captured_Time"
        ]
    )

    template.to_csv(
        PINTEREST_FILE,
        index=False
    )

    print(
        "Pinterest template created:"
    )

    print(
        PINTEREST_FILE
    )

    print(
        "\nFill in pinterest_candidates.csv, "
        "then run this script again."
    )

    raise SystemExit


# ==================================================
# 3. Load Pinterest candidates
# ==================================================

df = pd.read_csv(
    PINTEREST_FILE
)


trend_master = pd.read_csv(
    TREND_MASTER_FILE
)


# ==================================================
# 4. Clean data
# ==================================================

df["Keyword"] = (
    df["Keyword"]
    .astype(str)
    .str.lower()
    .str.strip()
)


for column in [
    "WoW_Growth",
    "MoM_Growth",
    "YoY_Growth"
]:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ==================================================
# 5. Remove empty rows
# ==================================================

df = df[
    df["Keyword"].notna()
    & (df["Keyword"] != "")
    & (df["Keyword"] != "nan")
].copy()


# ==================================================
# 6. Check whether trend is already monitored
# ==================================================

existing_trends = set(
    trend_master["Trend"]
    .astype(str)
    .str.lower()
    .str.strip()
)


df["Already_Monitored"] = (
    df["Keyword"]
    .isin(existing_trends)
)


# ==================================================
# 7. Stable growth-to-score function
# ==================================================

def growth_score(
    value,
    scale
):

    if pd.isna(value):
        return 50.0

    score = (
        50
        +
        50
        * np.tanh(
            value / scale
        )
    )

    return round(
        float(score),
        2
    )


# Weekly growth reacts fastest
df["Pinterest_WoW_Score"] = (
    df["WoW_Growth"]
    .apply(
        lambda x:
        growth_score(
            x,
            50
        )
    )
)


# Monthly trend is more important
df["Pinterest_MoM_Score"] = (
    df["MoM_Growth"]
    .apply(
        lambda x:
        growth_score(
            x,
            100
        )
    )
)


# Yearly growth is slowest-moving
df["Pinterest_YoY_Score"] = (
    df["YoY_Growth"]
    .apply(
        lambda x:
        growth_score(
            x,
            200
        )
    )
)


# ==================================================
# 8. Pinterest Momentum Score
# ==================================================

df["Pinterest_Score"] = (

    0.35
    * df["Pinterest_WoW_Score"]

    +

    0.45
    * df["Pinterest_MoM_Score"]

    +

    0.20
    * df["Pinterest_YoY_Score"]

).round(2)


# ==================================================
# 9. Pinterest trend stage
# ==================================================

def classify_pinterest(row):

    score = row[
        "Pinterest_Score"
    ]

    wow = row[
        "WoW_Growth"
    ]

    mom = row[
        "MoM_Growth"
    ]

    if (
        score >= 75
        and mom > 0
    ):
        return "Emerging Strong"

    if (
        score >= 60
        and (
            wow > 0
            or mom > 0
        )
    ):
        return "Growing"

    if score >= 45:
        return "Stable"

    return "Cooling"


df["Pinterest_Stage"] = (
    df.apply(
        classify_pinterest,
        axis=1
    )
)


# ==================================================
# 10. Candidate decision
# ==================================================

def candidate_decision(row):

    if row["Already_Monitored"]:
        return "Already Active"

    if row["Pinterest_Score"] >= 75:
        return "Validate Now"

    if row["Pinterest_Score"] >= 60:
        return "Watch"

    return "Low Priority"


df["Decision"] = (
    df.apply(
        candidate_decision,
        axis=1
    )
)


# ==================================================
# 11. Sort
# ==================================================

df = df.sort_values(
    "Pinterest_Score",
    ascending=False
)


# ==================================================
# 12. Display
# ==================================================

display_columns = [
    "Keyword",
    "Category",
    "WoW_Growth",
    "MoM_Growth",
    "YoY_Growth",
    "Pinterest_Score",
    "Pinterest_Stage",
    "Decision"
]


print(
    "\n========== PINTEREST SIGNAL =========="
)


print(
    df[
        display_columns
    ].to_string(
        index=False
    )
)


# ==================================================
# 13. Save
# ==================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)