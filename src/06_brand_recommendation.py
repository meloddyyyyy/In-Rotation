import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "trendpulse_score.csv"
)


OUTPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "brand_recommendations.csv"
)


df = pd.read_csv(INPUT_FILE)


# --------------------------------
# Recommendation logic
# --------------------------------

def generate_opportunity(score, stage, confidence):

    if score >= 70 and stage == "Rebounding":

        return (
            "High Opportunity",
            "Consider launching new products, "
            "campaign content, and influencer activation."
        )


    elif score >= 50:

        return (
            "Medium Opportunity",
            "Monitor trend growth and test "
            "small marketing campaigns."
        )


    elif stage == "Cooling":

        return (
            "Low Opportunity",
            "Avoid aggressive inventory expansion. "
            "Focus on niche audiences."
        )


    else:

        return (
            "Emerging",
            "Collect more data and continue monitoring."
        )



def generate_reason(row):

    reasons = []


    if row["Search_Score"] > 70:
        reasons.append(
            "Strong consumer search interest"
        )

    if row["Visual_Score"] > 70:
        reasons.append(
            "Strong visual discovery momentum"
        )

    if row["Media_Score"] > 50:
        reasons.append(
            "Increasing media attention"
        )

    if len(reasons) == 0:
        reasons.append(
            "Limited momentum signals"
        )


    return "; ".join(reasons)



# Apply recommendation

recommendations = []


for _, row in df.iterrows():

    opportunity, action = generate_opportunity(
        row["TrendPulse_Score"],
        row["Stage"],
        row["Confidence"]
    )


    recommendations.append(
        {
            "Trend": row["Trend"],
            "TrendPulse_Score": row["TrendPulse_Score"],
            "Opportunity": opportunity,
            "Marketing_Action": action,
            "Reason": generate_reason(row),
            "Stage": row["Stage"],
            "Confidence": row["Confidence"]
        }
    )



result = pd.DataFrame(
    recommendations
)


result = result.sort_values(
    "TrendPulse_Score",
    ascending=False
)


print(
    "========== BRAND RECOMMENDATIONS =========="
)


print(
    result.to_string(index=False)
)


result.to_csv(
    OUTPUT_FILE,
    index=False
)


print("\nSaved:")
print(OUTPUT_FILE)