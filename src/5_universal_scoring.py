import pandas as pd
import numpy as np
from pathlib import Path


# ==================================================
# 1. Paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

INPUT_FILE = (
    PROCESSED_DIR
    / "integrated_trend_signals.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "universal_trend_scores.csv"
)

# Keep this filename too so that
# existing recommendation/app code can still work.
LEGACY_OUTPUT_FILE = (
    PROCESSED_DIR
    / "trendpulse_score.csv"
)


# ==================================================
# 2. Load integrated signals
# ==================================================

df = pd.read_csv(
    INPUT_FILE
)


# ==================================================
# 3. Fixed scoring functions
# ==================================================

def growth_to_score(
    value,
    scale=25
):

    """
    Convert a percentage growth rate to 0-100.

    Around:
    0% growth  -> ~50
    +25%       -> strong positive score
    -25%       -> weak score

    Unlike min-max normalization,
    this score does NOT depend on
    other trends in the dataset.
    """

    if pd.isna(value):
        return np.nan

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


def slope_to_score(
    value,
    scale=3
):

    """
    Convert normalized 12-week slope to 0-100.

    0 slope = 50
    positive slope > 50
    negative slope < 50
    """

    if pd.isna(value):
        return np.nan

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


def symmetric_media_index(
    current,
    previous
):

    """
    Stable media momentum score.

    50 = no change
    >50 = rising
    <50 = falling
    """

    if (
        pd.isna(current)
        or pd.isna(previous)
    ):
        return np.nan

    total = (
        current
        + previous
    )

    if total == 0:
        return 50.0

    symmetric_change = (
        200
        * (
            current
            - previous
        )
        / total
    )

    score = (
        symmetric_change
        + 200
    ) / 4

    return round(
        float(score),
        2
    )


# ==================================================
# 4. Search signal scores
# ==================================================

df["Web_Growth_Score"] = (
    df["Web_Growth"]
    .apply(
        lambda x:
        growth_to_score(
            x,
            scale=25
        )
    )
)


df["Web_Slope_Score"] = (
    df["Web_12W_Slope"]
    .apply(
        lambda x:
        slope_to_score(
            x,
            scale=3
        )
    )
)


df["Search_Score"] = (
    0.65
    * df["Web_Growth_Score"]
    +
    0.35
    * df["Web_Slope_Score"]
).round(2)


# ==================================================
# 5. Visual signal scores
# ==================================================

df["Image_Growth_Score"] = (
    df["Image_Growth"]
    .apply(
        lambda x:
        growth_to_score(
            x,
            scale=25
        )
    )
)


df["Image_Slope_Score"] = (
    df["Image_12W_Slope"]
    .apply(
        lambda x:
        slope_to_score(
            x,
            scale=3
        )
    )
)


df["Visual_Score"] = (
    0.65
    * df["Image_Growth_Score"]
    +
    0.35
    * df["Image_Slope_Score"]
).round(2)


# ==================================================
# 6. Media score
# ==================================================

if "Media_Momentum_Index" in df.columns:

    df["Media_Score"] = (
        pd.to_numeric(
            df["Media_Momentum_Index"],
            errors="coerce"
        )
    )

else:

    df["Media_Score"] = (
        df.apply(
            lambda row:
            symmetric_media_index(
                row["Media_Current_7D"],
                row["Media_Previous_7D"]
            ),
            axis=1
        )
    )


# ==================================================
# 7. Universal TrendPulse Score
# ==================================================

df["TrendPulse_Score"] = (
    0.40
    * df["Search_Score"]

    +

    0.30
    * df["Visual_Score"]

    +

    0.30
    * df["Media_Score"]
).round(2)


# ==================================================
# 8. Fast-rising score
# ==================================================

# This deliberately focuses on acceleration,
# not total popularity.

df["Fast_Rising_Score"] = (
    0.50
    * df["Web_Growth_Score"]

    +

    0.30
    * df["Image_Growth_Score"]

    +

    0.20
    * df["Media_Score"]
).round(2)


# ==================================================
# 9. Signal agreement
# ==================================================

def signal_agreement(row):

    directions = []

    if pd.notna(
        row["Web_Growth"]
    ):
        directions.append(
            row["Web_Growth"] >= 0
        )

    if pd.notna(
        row["Image_Growth"]
    ):
        directions.append(
            row["Image_Growth"] >= 0
        )

    if pd.notna(
        row["Media_Score"]
    ):
        directions.append(
            row["Media_Score"] >= 50
        )

    if len(directions) < 2:
        return "Low Data"

    positive_count = sum(
        directions
    )

    if (
        positive_count
        == len(directions)
        or positive_count == 0
    ):
        return "Strong"

    return "Mixed"


df["Signal_Agreement"] = (
    df.apply(
        signal_agreement,
        axis=1
    )
)


# ==================================================
# 10. Rankings
# ==================================================

# Important:
# Scores are universal/fixed.
#
# Rankings are naturally relative to the
# currently monitored trend universe.

df["Overall_Rank"] = (
    df["TrendPulse_Score"]
    .rank(
        method="min",
        ascending=False
    )
    .astype("Int64")
)


df["Fast_Rising_Rank"] = (
    df["Fast_Rising_Score"]
    .rank(
        method="min",
        ascending=False
    )
    .astype("Int64")
)


df["Search_Growth_Rank"] = (
    df["Web_Growth"]
    .rank(
        method="min",
        ascending=False
    )
    .astype("Int64")
)


# ==================================================
# 11. Simple label
# ==================================================

def score_label(score):

    if pd.isna(score):
        return "Insufficient Data"

    if score >= 75:
        return "Strong"

    if score >= 60:
        return "Promising"

    if score >= 45:
        return "Mixed"

    return "Weak"


df["TrendPulse_Label"] = (
    df["TrendPulse_Score"]
    .apply(
        score_label
    )
)


# ==================================================
# 12. Final output
# ==================================================

keep_columns = [

    "Trend",

    # Raw movement
    "Current_Interest",
    "Web_Growth",
    "Image_Growth",
    "Web_12W_Slope",
    "Image_12W_Slope",

    # Stable component scores
    "Search_Score",
    "Visual_Score",
    "Media_Score",

    # Final scores
    "TrendPulse_Score",
    "Fast_Rising_Score",

    # Ranking
    "Overall_Rank",
    "Fast_Rising_Rank",
    "Search_Growth_Rank",

    # Existing classification
    "Stage",
    "Confidence",

    # New interpretation
    "Signal_Agreement",
    "TrendPulse_Label"
]


result = df[
    [
        column
        for column in keep_columns
        if column in df.columns
    ]
].copy()


result = result.sort_values(
    "Overall_Rank"
)


# ==================================================
# 13. Print
# ==================================================

print(
    "\n========== UNIVERSAL TREND RANKING =========="
)


print(
    result[
        [
            "Trend",
            "Web_Growth",
            "Search_Score",
            "Visual_Score",
            "Media_Score",
            "TrendPulse_Score",
            "Fast_Rising_Score",
            "Overall_Rank",
            "Fast_Rising_Rank",
            "Stage"
        ]
    ].to_string(
        index=False
    )
)


# ==================================================
# 14. Save
# ==================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


# Also overwrite the old score file
# so 06_brand_recommendation.py
# and app.old.py keep working.

result.to_csv(
    LEGACY_OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)

print(
    "\nUpdated existing dashboard file:"
)

print(
    LEGACY_OUTPUT_FILE
)