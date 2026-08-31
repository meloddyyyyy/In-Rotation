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


# ==================================================
# 2. Load processed data
# ==================================================

web = pd.read_csv(
    PROCESSED_DIR
    / "web_search_clean.csv"
)

image = pd.read_csv(
    PROCESSED_DIR
    / "image_search_clean.csv"
)

summary = pd.read_csv(
    PROCESSED_DIR
    / "search_signal_summary.csv"
)


# ==================================================
# 3. Safety check: normalize time column
# ==================================================

def ensure_time_column(df):

    df = df.copy()

    if "Time" not in df.columns:

        if "Date" in df.columns:
            df = df.rename(
                columns={
                    "Date": "Time"
                }
            )

        elif "Week" in df.columns:
            df = df.rename(
                columns={
                    "Week": "Time"
                }
            )

        else:
            df = df.rename(
                columns={
                    df.columns[0]:
                    "Time"
                }
            )

    df["Time"] = pd.to_datetime(
        df["Time"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["Time"]
    )

    df = df.sort_values(
        "Time"
    )

    return df


web = ensure_time_column(web)
image = ensure_time_column(image)


# ==================================================
# 4. Calculate normalized 12-week slope
# ==================================================

def calculate_12w_slope(
    df,
    source_name
):

    results = []

    trend_columns = [
        column
        for column in df.columns
        if column != "Time"
    ]

    for trend in trend_columns:

        values = (
            df[trend]
            .tail(12)
            .dropna()
        )

        if (
            len(values) < 8
            or values.mean() == 0
        ):

            normalized_slope = np.nan

        else:

            x = np.arange(
                len(values)
            )

            raw_slope = np.polyfit(
                x,
                values,
                1
            )[0]

            normalized_slope = (
                raw_slope
                / values.mean()
            ) * 100

        results.append(
            {
                "Trend":
                    trend,

                f"{source_name}_12W_Slope":
                    (
                        round(
                            normalized_slope,
                            2
                        )
                        if not np.isnan(
                            normalized_slope
                        )
                        else np.nan
                    )
            }
        )

    return pd.DataFrame(
        results
    )


web_slope = calculate_12w_slope(
    web,
    "Web"
)

image_slope = calculate_12w_slope(
    image,
    "Image"
)


# ==================================================
# 5. Combine features
# ==================================================

features = summary.merge(
    web_slope,
    on="Trend",
    how="left"
)


features = features.merge(
    image_slope,
    on="Trend",
    how="left"
)


features[
    "Current_Interest"
] = (
    features[
        "Web_Recent_4W"
    ]
)


features = features.rename(
    columns={
        "Visual_Gap":
        "Visual_Momentum_Gap"
    }
)


# ==================================================
# 6. Trend Stage
# ==================================================

def classify_stage(row):

    current = row[
        "Current_Interest"
    ]

    growth_4w = row[
        "Web_Growth"
    ]

    slope_12w = row[
        "Web_12W_Slope"
    ]

    if (
        pd.isna(current)
        or pd.isna(growth_4w)
        or pd.isna(slope_12w)
        or current <= 1
    ):

        return "Low Signal"

    if (
        growth_4w >= 8
        and slope_12w >= 0.5
    ):

        return "Accelerating"

    if (
        growth_4w >= 5
        and slope_12w < 0
    ):

        return "Rebounding"

    if (
        growth_4w <= -8
        and slope_12w <= -0.5
    ):

        return "Cooling"

    return "Established"


features[
    "Stage"
] = features.apply(
    classify_stage,
    axis=1
)


# ==================================================
# 7. Confidence
# ==================================================

def calculate_confidence(row):

    values = [
        row["Web_Growth"],
        row["Image_Growth"],
        row["Web_12W_Slope"],
        row["Image_12W_Slope"]
    ]

    if any(
        pd.isna(value)
        for value in values
    ):

        return "Low"

    short_term_agree = (
        (
            row["Web_Growth"]
            >= 0
        )
        ==
        (
            row["Image_Growth"]
            >= 0
        )
    )

    medium_term_agree = (
        (
            row["Web_12W_Slope"]
            >= 0
        )
        ==
        (
            row["Image_12W_Slope"]
            >= 0
        )
    )

    if (
        short_term_agree
        and medium_term_agree
    ):

        return "High"

    if (
        short_term_agree
        or medium_term_agree
    ):

        return "Medium"

    return "Low"


features[
    "Confidence"
] = features.apply(
    calculate_confidence,
    axis=1
)


# ==================================================
# 8. Output columns
# ==================================================

features = features[
    [
        "Trend",
        "Current_Interest",
        "Web_Growth",
        "Image_Growth",
        "Web_12W_Slope",
        "Image_12W_Slope",
        "Visual_Momentum_Gap",
        "Stage",
        "Confidence"
    ]
]


print(
    "\n========== TREND STAGE RESULTS =========="
)

print(
    features.to_string(
        index=False
    )
)


# ==================================================
# 9. Save
# ==================================================

features.to_csv(
    PROCESSED_DIR
    / "trend_features.csv",
    index=False
)


features.to_csv(
    PROCESSED_DIR
    / "trend_stage_results.csv",
    index=False
)


print(
    "\nSaved successfully."
)