import streamlit as st
import pandas as pd
import json
from pathlib import Path


# ==================================================
# 1. Page setup
# ==================================================

st.set_page_config(
    page_title="TrendPulse",
    page_icon="📈",
    layout="wide"
)


# ==================================================
# 2. Paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)

VERDICT_FILE = (
    PROCESSED_DIR
    / "consumer_trend_verdicts_reliable.csv"
)

WEB_FILE = (
    PROCESSED_DIR
    / "web_search_clean.csv"
)

IMAGE_FILE = (
    PROCESSED_DIR
    / "image_search_clean.csv"
)

STATUS_FILE = (
    PROCESSED_DIR
    / "pipeline_status.json"
)


# ==================================================
# 3. Load data
# ==================================================

df = pd.read_csv(
    VERDICT_FILE
)

web_df = pd.read_csv(
    WEB_FILE
)

image_df = pd.read_csv(
    IMAGE_FILE
)


# ==================================================
# 4. Normalize Time
# ==================================================

def normalize_time(df):

    df = df.copy()

    if "Time" not in df.columns:

        df = df.rename(
            columns={
                df.columns[0]: "Time"
            }
        )

    df["Time"] = pd.to_datetime(
        df["Time"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["Time"]
    )

    return df.sort_values(
        "Time"
    )


web_df = normalize_time(
    web_df
)

image_df = normalize_time(
    image_df
)


# ==================================================
# 5. Pipeline status
# ==================================================

last_updated = "Unknown"

if STATUS_FILE.exists():

    with open(
        STATUS_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        status = json.load(
            file
        )

    timestamp = status.get(
        "last_successful_update"
    )

    if timestamp:

        parsed_time = pd.to_datetime(
            timestamp
        )

        last_updated = parsed_time.strftime(
            "%b %d, %Y"
        )


# ==================================================
# 6. Header
# ==================================================

st.title(
    "TrendPulse"
)

st.subheader(
    "Is it still trending?"
)

st.write(
    """
    Track fashion trends across consumer search,
    visual discovery and media attention —
    and see whether a trend is early, hot,
    peaking or cooling.
    """
)

st.caption(
    f"Updated {last_updated} · "
    f"{len(df)} trends monitored · "
    "Rankings are within the current TrendPulse fashion universe."
)


# ==================================================
# 7. Tabs
# ==================================================

overview_tab, checker_tab = st.tabs(
    [
        "Explore Trends",
        "Check a Trend"
    ]
)


# ==================================================
# 8. OVERVIEW TAB
# ==================================================

with overview_tab:

    # ----------------------------------------------
    # Market overview metrics
    # ----------------------------------------------

    col1, col2, col3 = st.columns(
        3
    )

    with col1:

        st.metric(
            "Trends Monitored",
            len(df)
        )


    with col2:

        high_evidence = (
            df["Evidence_Level"]
            == "High"
        ).sum()

        st.metric(
            "High-Evidence Trends",
            high_evidence
        )


    with col3:

        rising_count = (
            df["Web_Growth"]
            > 0
        ).sum()

        st.metric(
            "Search Momentum Rising",
            rising_count
        )


    st.divider()


    # ==================================================
    # 9. Rising Now
    # ==================================================

    st.header(
        "🔥 Rising Now"
    )

    st.caption(
        "Fastest recent search growth among trends "
        "with usable evidence."
    )


    rising = df[
        (
            df["Ranking_Status"]
            == "Eligible"
        )
        &
        (
            df["Web_Growth"]
            .notna()
        )
    ].copy()


    rising = rising.sort_values(
        "Web_Growth",
        ascending=False
    ).head(5)


    for rank, (_, row) in enumerate(
        rising.iterrows(),
        start=1
    ):

        col1, col2, col3, col4 = st.columns(
            [
                4,
                2,
                2,
                2
            ]
        )

        with col1:

            st.markdown(
                f"**#{rank} {row['Trend'].title()}**"
            )

        with col2:

            st.write(
                f"{row['Web_Growth']:+.1f}% search"
            )

        with col3:

            st.write(
                row["Consumer_Verdict"]
            )

        with col4:

            st.write(
                f"{row['Evidence_Level']} evidence"
            )


    st.divider()


    # ==================================================
    # 10. Early signals
    # ==================================================

    st.header(
        "🌱 Early Signals"
    )

    early = df[
        df["Consumer_Verdict"]
        == "EARLY"
    ].sort_values(
        "TrendPulse_Score",
        ascending=False
    )


    if early.empty:

        st.write(
            "No high-confidence early signals detected right now."
        )

    else:

        st.dataframe(
            early[
                [
                    "Trend",
                    "TrendPulse_Score",
                    "Web_Growth",
                    "Evidence_Level"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )


    # ==================================================
    # 11. Still in
    # ==================================================

    st.header(
        "✅ Still In"
    )

    still_in = df[
        df["Consumer_Verdict"]
        .isin(
            [
                "HOT",
                "STILL IN"
            ]
        )
    ].sort_values(
        "TrendPulse_Score",
        ascending=False
    )


    if still_in.empty:

        st.write(
            "No trends currently classified here."
        )

    else:

        st.dataframe(
            still_in[
                [
                    "Trend",
                    "Consumer_Verdict",
                    "Buy_Timing",
                    "TrendPulse_Score",
                    "Evidence_Level"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )


    # ==================================================
    # 12. Peaking
    # ==================================================

    st.header(
        "⚠️ Peaking"
    )

    peaking = df[
        df["Consumer_Verdict"]
        == "PEAKING"
    ].sort_values(
        "TrendPulse_Score",
        ascending=False
    )


    if peaking.empty:

        st.write(
            "No monitored trends are clearly peaking right now."
        )

    else:

        st.dataframe(
            peaking[
                [
                    "Trend",
                    "Buy_Timing",
                    "Web_Growth",
                    "Image_Growth",
                    "Evidence_Level"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )


    # ==================================================
    # 13. Cooling
    # ==================================================

    st.header(
        "📉 Cooling"
    )

    cooling = df[
        df["Consumer_Verdict"]
        == "COOLING"
    ].sort_values(
        "Web_Growth",
        ascending=True
    )


    if cooling.empty:

        st.write(
            "No clearly cooling trends detected."
        )

    else:

        st.dataframe(
            cooling[
                [
                    "Trend",
                    "Buy_Timing",
                    "Web_Growth",
                    "Trend_Risk",
                    "Evidence_Level"
                ]
            ],
            hide_index=True,
            use_container_width=True
        )


# ==================================================
# 14. TREND CHECKER TAB
# ==================================================

with checker_tab:

    st.header(
        "Check a Trend"
    )


    trend = st.selectbox(
        "Choose a trend",
        sorted(
            df["Trend"]
            .dropna()
            .tolist()
        )
    )


    selected = (
        df[
            df["Trend"]
            == trend
        ]
        .iloc[0]
    )


    # ==================================================
    # 15. Main consumer verdict
    # ==================================================

    st.title(
        trend.title()
    )


    st.markdown(
        f"## {selected['Consumer_Verdict']}"
    )


    st.markdown(
        f"### {selected['Buy_Timing']}"
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        st.metric(
            "TrendPulse",
            f"{selected['TrendPulse_Score']:.0f}/100"
        )


    with col2:

        st.metric(
            "Trend Risk",
            selected["Trend_Risk"]
        )


    with col3:

        st.metric(
            "Evidence",
            selected["Evidence_Level"]
        )


    # ==================================================
    # 16. Plain-English explanation
    # ==================================================

    st.divider()

    st.header(
        "What the signals say"
    )


    st.write(
        selected[
            "Consumer_Explanation"
        ]
    )


    if (
        selected["Evidence_Level"]
        != "High"
    ):

        st.warning(
            selected[
                "Evidence_Caution"
            ]
        )

    else:

        st.success(
            selected[
                "Evidence_Caution"
            ]
        )


    # ==================================================
    # 17. Signal metrics
    # ==================================================

    st.header(
        "Momentum"
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        st.metric(
            "Web Search · 4W",
            (
                f"{selected['Web_Growth']:+.1f}%"
                if pd.notna(
                    selected["Web_Growth"]
                )
                else "No data"
            )
        )


    with col2:

        st.metric(
            "Image Search · 4W",
            (
                f"{selected['Image_Growth']:+.1f}%"
                if pd.notna(
                    selected["Image_Growth"]
                )
                else "No data"
            )
        )


    with col3:

        st.metric(
            "Media Momentum",
            (
                f"{selected['Media_Score']:.0f}/100"
                if pd.notna(
                    selected["Media_Score"]
                )
                else "No data"
            )
        )


    # ==================================================
    # 18. Web chart
    # ==================================================

    st.divider()

    st.header(
        "Search Interest"
    )


    if trend in web_df.columns:

        web_chart = (
            web_df[
                [
                    "Time",
                    trend
                ]
            ]
            .dropna()
            .set_index(
                "Time"
            )
        )

        st.line_chart(
            web_chart,
            height=320
        )


    # ==================================================
    # 19. Image chart
    # ==================================================

    st.header(
        "Visual Interest"
    )


    if trend in image_df.columns:

        image_chart = (
            image_df[
                [
                    "Time",
                    trend
                ]
            ]
            .dropna()
            .set_index(
                "Time"
            )
        )

        st.line_chart(
            image_chart,
            height=320
        )


    # ==================================================
    # 20. Methodology
    # ==================================================

    st.divider()


    with st.expander(
        "How should I interpret this?"
    ):

        st.markdown(
            """
**EARLY**  
A trend is showing early positive momentum but has not fully matured.

**HOT**  
Multiple signals suggest strong current acceleration.

**STILL IN**  
The trend is already established but remains relevant.

**PEAKING**  
The trend is still visible, but momentum is beginning to weaken.

**COOLING**  
Multiple signals indicate declining interest.

**Evidence Level**  
Measures how much underlying search, visual and media evidence supports the verdict.

TrendPulse does not determine whether you personally should like or buy an item. It estimates trend momentum from the monitored data.
            """
        )