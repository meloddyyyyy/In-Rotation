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

INPUT_FILE = (
    PROCESSED_DIR
    / "universal_trend_scores.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "consumer_trend_verdicts.csv"
)


# ==================================================
# 2. Load data
# ==================================================

df = pd.read_csv(
    INPUT_FILE
)


# ==================================================
# 3. Consumer verdict
# ==================================================

def get_verdict(row):

    score = row["TrendPulse_Score"]
    stage = row["Stage"]

    web_growth = row["Web_Growth"]
    image_growth = row["Image_Growth"]

    # Strong medium / short-term momentum
    if (
        stage == "Accelerating"
        and score >= 65
    ):
        return "HOT"

    # Trend has recently returned
    if (
        stage == "Rebounding"
        and score >= 60
    ):
        return "STILL IN"

    # Mature but still reasonably healthy
    if (
        stage == "Established"
        and score >= 55
    ):
        return "STILL IN"

    # Conflicting signs:
    # still visible, but losing momentum
    if (
        score >= 45
        and (
            web_growth < 0
            or image_growth < 0
        )
    ):
        return "PEAKING"

    # Broad decline
    if stage == "Cooling":
        return "COOLING"

    # Low current signal but positive growth
    if (
        score < 55
        and web_growth > 10
    ):
        return "EARLY"

    return "WATCH"


df["Consumer_Verdict"] = (
    df.apply(
        get_verdict,
        axis=1
    )
)


# ==================================================
# 4. Buy timing
# ==================================================

def get_buy_timing(verdict):

    mapping = {

        "EARLY":
            "Early Buy",

        "HOT":
            "Good Time to Buy",

        "STILL IN":
            "Buy Selectively",

        "PEAKING":
            "Avoid Trend Premium",

        "COOLING":
            "Buy Only If You Love It",

        "WATCH":
            "Wait and Watch"
    }

    return mapping.get(
        verdict,
        "Wait and Watch"
    )


df["Buy_Timing"] = (
    df["Consumer_Verdict"]
    .apply(
        get_buy_timing
    )
)


# ==================================================
# 5. Trend risk
# ==================================================

def get_trend_risk(row):

    verdict = row[
        "Consumer_Verdict"
    ]

    agreement = row[
        "Signal_Agreement"
    ]

    if verdict in [
        "COOLING",
        "PEAKING"
    ]:
        return "High"

    if (
        verdict == "HOT"
        and agreement == "Strong"
    ):
        return "Low"

    if (
        verdict == "STILL IN"
        and agreement == "Strong"
    ):
        return "Low"

    return "Medium"


df["Trend_Risk"] = (
    df.apply(
        get_trend_risk,
        axis=1
    )
)


# ==================================================
# 6. Consumer explanation
# ==================================================

def build_explanation(row):

    parts = []

    web = row["Web_Growth"]
    image = row["Image_Growth"]
    media = row["Media_Score"]

    # Search
    if web >= 10:

        parts.append(
            "consumer search is rising"
        )

    elif web <= -10:

        parts.append(
            "consumer search is declining"
        )

    else:

        parts.append(
            "consumer search is relatively stable"
        )

    # Visual
    if image >= 10:

        parts.append(
            "visual discovery is gaining momentum"
        )

    elif image <= -10:

        parts.append(
            "visual discovery is weakening"
        )

    else:

        parts.append(
            "visual interest is relatively stable"
        )

    # Media
    if media >= 60:

        parts.append(
            "media attention remains strong"
        )

    elif media <= 40:

        parts.append(
            "media attention is weakening"
        )

    else:

        parts.append(
            "media attention is mixed"
        )

    return (
        "; ".join(parts)
        + "."
    )


df["Consumer_Explanation"] = (
    df.apply(
        build_explanation,
        axis=1
    )
)


# ==================================================
# 7. Output
# ==================================================

output_columns = [

    "Trend",

    "TrendPulse_Score",

    "Consumer_Verdict",

    "Buy_Timing",

    "Trend_Risk",

    "Stage",

    "Confidence",

    "Signal_Agreement",

    "Web_Growth",

    "Image_Growth",

    "Media_Score",

    "Consumer_Explanation"
]


result = df[
    output_columns
].copy()


result = result.sort_values(
    "TrendPulse_Score",
    ascending=False
)


# ==================================================
# 8. Print
# ==================================================

print(
    "\n========== CONSUMER TREND VERDICTS =========="
)


print(
    result.to_string(
        index=False
    )
)


# ==================================================
# 9. Save
# ==================================================

result.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)