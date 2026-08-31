import pandas as pd
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


TREND_STAGE_FILE = (
    PROCESSED_DIR
    / "trend_stage_results.csv"
)


MEDIA_FILE = (
    PROCESSED_DIR
    / "media_signal.csv"
)


OUTPUT_FILE = (
    PROCESSED_DIR
    / "integrated_trend_signals.csv"
)


# ==================================================
# 2. Load data
# ==================================================

trend_stage = pd.read_csv(
    TREND_STAGE_FILE
)


media = pd.read_csv(
    MEDIA_FILE
)


print(
    "\nTrend Stage rows:",
    len(trend_stage)
)

print(
    "Media rows:",
    len(media)
)


# ==================================================
# 3. Merge Search + Media
# ==================================================

integrated = pd.merge(
    trend_stage,
    media,
    on="Trend",
    how="left"
)


# ==================================================
# 4. Media direction
# ==================================================

def get_media_direction(value):

    if pd.isna(value):
        return "No Data"

    if value >= 60:
        return "Rising"

    if value <= 40:
        return "Falling"

    return "Stable"


integrated[
    "Media_Direction"
] = (
    integrated[
        "Media_Momentum_Index"
    ]
    .apply(
        get_media_direction
    )
)


# ==================================================
# 5. Media signal strength
# ==================================================

def get_media_strength(row):

    volume = row[
        "Media_30D"
    ]

    status = row[
        "Media_Data_Status"
    ]

    if status == "Fetch Failed":
        return "No Data"

    if pd.isna(volume):
        return "No Data"

    if volume >= 20:
        return "Strong"

    if volume >= 8:
        return "Medium"

    if volume > 0:
        return "Low"

    return "Very Low"


integrated[
    "Media_Strength"
] = (
    integrated.apply(
        get_media_strength,
        axis=1
    )
)


# ==================================================
# 6. Cross-signal direction
# ==================================================

def get_signal_pattern(row):

    web = row[
        "Web_Growth"
    ]

    image = row[
        "Image_Growth"
    ]

    media = row[
        "Media_Momentum_Index"
    ]


    signals = []


    # Web
    if pd.notna(web):

        if web >= 5:
            signals.append("Web ↑")

        elif web <= -5:
            signals.append("Web ↓")

        else:
            signals.append("Web →")


    # Image
    if pd.notna(image):

        if image >= 5:
            signals.append("Image ↑")

        elif image <= -5:
            signals.append("Image ↓")

        else:
            signals.append("Image →")


    # Media
    if pd.notna(media):

        if media >= 60:
            signals.append("Media ↑")

        elif media <= 40:
            signals.append("Media ↓")

        else:
            signals.append("Media →")


    return " | ".join(
        signals
    )


integrated[
    "Signal_Pattern"
] = (
    integrated.apply(
        get_signal_pattern,
        axis=1
    )
)


# ==================================================
# 7. Display columns
# ==================================================

display_columns = [

    "Trend",

    "Current_Interest",

    "Web_Growth",

    "Image_Growth",

    "Web_12W_Slope",

    "Image_12W_Slope",

    "Stage",

    "Confidence",

    "Media_Current_7D",

    "Media_Previous_7D",

    "Media_30D",

    "Media_Momentum_Index",

    "Media_Direction",

    "Media_Strength",

    "Signal_Pattern"
]


# Only keep columns that actually exist
display_columns = [

    column

    for column in display_columns

    if column in integrated.columns
]


# ==================================================
# 8. Display
# ==================================================

print(
    "\n========== INTEGRATED TREND SIGNALS =========="
)


print(
    integrated[
        display_columns
    ]
    .to_string(
        index=False
    )
)


# ==================================================
# 9. Save
# ==================================================

integrated.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)


print(
    "\nNumber of integrated trends:"
)

print(
    len(integrated)
)