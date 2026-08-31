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

VERDICT_FILE = (
    PROCESSED_DIR
    / "consumer_trend_verdicts.csv"
)

SEARCH_FILE = (
    PROCESSED_DIR
    / "search_signal_summary.csv"
)

MEDIA_FILE = (
    PROCESSED_DIR
    / "media_signal.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "consumer_trend_verdicts_reliable.csv"
)


# ==================================================
# 2. Load data
# ==================================================

verdict = pd.read_csv(
    VERDICT_FILE
)

search = pd.read_csv(
    SEARCH_FILE
)

media = pd.read_csv(
    MEDIA_FILE
)


# ==================================================
# 3. Select reliability fields
# ==================================================

search_fields = search[
    [
        "Trend",

        "Web_Recent_4W",
        "Web_Previous_4W",
        "Web_Data_Status",

        "Image_Recent_4W",
        "Image_Previous_4W",
        "Image_Data_Status"
    ]
].copy()


media_fields = media[
    [
        "Trend",
        "Media_Current_7D",
        "Media_Previous_7D",
        "Media_30D",
        "Media_Data_Status"
    ]
].copy()


# ==================================================
# 4. Merge
# ==================================================

df = pd.merge(
    verdict,
    search_fields,
    on="Trend",
    how="left"
)


df = pd.merge(
    df,
    media_fields,
    on="Trend",
    how="left"
)


# ==================================================
# 5. Reliability calculation
# ==================================================

def calculate_reliability(row):

    score = 0

    cautions = []


    # ------------------------------------------------
    # A. Web data quality — max 20
    # ------------------------------------------------

    if row["Web_Data_Status"] == "Valid":

        score += 20

    else:

        cautions.append(
            "web search signal is limited"
        )


    # ------------------------------------------------
    # B. Image data quality — max 15
    # ------------------------------------------------

    if row["Image_Data_Status"] == "Valid":

        score += 15

    else:

        cautions.append(
            "image-search signal is limited"
        )


    # ------------------------------------------------
    # C. Web search base — max 20
    # ------------------------------------------------

    web_values = [
        row["Web_Recent_4W"],
        row["Web_Previous_4W"]
    ]


    valid_web_values = [
        value
        for value in web_values
        if pd.notna(value)
    ]


    if len(valid_web_values) > 0:

        web_base = sum(
            valid_web_values
        ) / len(
            valid_web_values
        )

    else:

        web_base = 0


    if web_base >= 20:

        score += 20

    elif web_base >= 8:

        score += 15

    elif web_base >= 3:

        score += 8

    else:

        score += 2

        cautions.append(
            "search growth is based on a very small base"
        )


    # ------------------------------------------------
    # D. Image search base — max 10
    # ------------------------------------------------

    image_values = [
        row["Image_Recent_4W"],
        row["Image_Previous_4W"]
    ]


    valid_image_values = [
        value
        for value in image_values
        if pd.notna(value)
    ]


    if len(valid_image_values) > 0:

        image_base = sum(
            valid_image_values
        ) / len(
            valid_image_values
        )

    else:

        image_base = 0


    if image_base >= 10:

        score += 10

    elif image_base >= 3:

        score += 7

    elif image_base > 0:

        score += 3

        cautions.append(
            "visual signal has a small base"
        )

    else:

        cautions.append(
            "visual search signal is extremely limited"
        )


    # ------------------------------------------------
    # E. Media evidence — max 20
    # ------------------------------------------------

    media_status = row[
        "Media_Data_Status"
    ]

    media_volume = row[
        "Media_30D"
    ]


    if media_status == "Fetch Failed":

        cautions.append(
            "media data could not be retrieved"
        )

    elif pd.isna(media_volume):

        cautions.append(
            "media evidence is unavailable"
        )

    elif media_volume >= 20:

        score += 20

    elif media_volume >= 8:

        score += 15

    elif media_volume >= 3:

        score += 10

    elif media_volume > 0:

        score += 5

        cautions.append(
            "media evidence is limited"
        )

    else:

        score += 3

        cautions.append(
            "little recent media evidence"
        )


    # ------------------------------------------------
    # F. Cross-signal agreement — max 15
    # ------------------------------------------------

    agreement = row[
        "Signal_Agreement"
    ]


    if agreement == "Strong":

        score += 15

    elif agreement == "Mixed":

        score += 8

        cautions.append(
            "search, visual and media signals disagree"
        )

    else:

        score += 3

        cautions.append(
            "not enough signals agree"
        )


    # ------------------------------------------------
    # G. Detect low-base growth explosion
    # ------------------------------------------------

    web_growth = row[
        "Web_Growth"
    ]


    if (
        pd.notna(web_growth)
        and abs(web_growth) >= 20
        and web_base < 5
    ):

        cautions.append(
            "large percentage change may be amplified by low search volume"
        )


    image_growth = row[
        "Image_Growth"
    ]


    if (
        pd.notna(image_growth)
        and abs(image_growth) >= 20
        and image_base < 5
    ):

        cautions.append(
            "large image-search change may be amplified by low volume"
        )


    # ------------------------------------------------
    # H. Evidence label
    # ------------------------------------------------

    if score >= 75:

        level = "High"

    elif score >= 50:

        level = "Medium"

    else:

        level = "Low"


    if len(cautions) == 0:

        caution_text = (
            "Signals have relatively strong supporting evidence."
        )

    else:

        caution_text = "; ".join(
            dict.fromkeys(
                cautions
            )
        )


    return pd.Series(
        {
            "Evidence_Score":
                score,

            "Evidence_Level":
                level,

            "Evidence_Caution":
                caution_text,

            "Web_Base":
                round(
                    web_base,
                    2
                ),

            "Image_Base":
                round(
                    image_base,
                    2
                )
        }
    )


reliability = df.apply(
    calculate_reliability,
    axis=1
)


df = pd.concat(
    [
        df,
        reliability
    ],
    axis=1
)


# ==================================================
# 6. Ranking eligibility
# ==================================================

def ranking_eligibility(row):

    if (
        row["Evidence_Level"]
        == "Low"
    ):

        return "Use With Caution"


    if (
        row["Web_Data_Status"]
        != "Valid"
    ):

        return "Use With Caution"


    return "Eligible"


df[
    "Ranking_Status"
] = df.apply(
    ranking_eligibility,
    axis=1
)


# ==================================================
# 7. Sort
# ==================================================

df = df.sort_values(
    [
        "Evidence_Score",
        "TrendPulse_Score"
    ],
    ascending=[
        False,
        False
    ]
)


# ==================================================
# 8. Display
# ==================================================

display_columns = [

    "Trend",

    "Consumer_Verdict",

    "TrendPulse_Score",

    "Web_Growth",

    "Evidence_Score",

    "Evidence_Level",

    "Ranking_Status",

    "Evidence_Caution"
]


print(
    "\n========== RELIABILITY CHECK =========="
)


print(
    df[
        display_columns
    ].to_string(
        index=False
    )
)


# ==================================================
# 9. Save
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