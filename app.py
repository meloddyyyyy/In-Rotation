import json
from pathlib import Path

import pandas as pd
import streamlit as st


# =========================================================
# 1. PAGE SETTINGS
# =========================================================

st.set_page_config(
    page_title="In Rotation",
    page_icon="♡",
    layout="wide"
)


# =========================================================
# 2. FASHION EDITORIAL STYLE
# =========================================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600&family=DM+Sans:wght@300;400;500;600&family=Instrument+Serif:ital@0;1&display=swap');


    /* -----------------------------------------
       GLOBAL
    ----------------------------------------- */

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
    }


    .stApp {
        background:
            linear-gradient(
                180deg,
                #FFF9F7 0%,
                #FFFDFC 48%,
                #FAF6F2 100%
            );

        color: #30282B;
    }


    .block-container {
        max-width: 1180px;
        padding-top: 3.5rem;
        padding-bottom: 5rem;
    }


    /* -----------------------------------------
       HEADINGS
    ----------------------------------------- */

    h1 {
        font-family: 'Instrument Serif', serif !important;
        font-weight: 400 !important;
        letter-spacing: -1.5px !important;
        color: #30282B !important;
    }


    h2 {
        font-family: 'Instrument Serif', serif !important;
        font-weight: 400 !important;
        color: #30282B !important;
        letter-spacing: -0.5px;
    }


    h3 {
        font-family: 'Instrument Serif', serif !important;
        font-weight: 400 !important;
        color: #47393E !important;
    }


    p {
        color: #665B5F;
        line-height: 1.65;
    }


    /* -----------------------------------------
       TABS
    ----------------------------------------- */

    button[data-baseweb="tab"] {
        font-family: 'DM Sans', sans-serif;
        font-size: 0.9rem;
        letter-spacing: 0.02em;
    }


    /* -----------------------------------------
       METRICS
    ----------------------------------------- */

    div[data-testid="stMetric"] {

        background:
            rgba(
                255,
                253,
                252,
                0.88
            );

        border:
            1px solid
            #EADDDD;

        border-radius:
            22px;

        padding:
            22px 24px;

        box-shadow:
            0 8px 30px
            rgba(
                91,
                65,
                73,
                0.05
            );
    }


    div[data-testid="stMetricLabel"] {

        font-size:
            0.72rem;

        text-transform:
            uppercase;

        letter-spacing:
            0.12em;

        color:
            #9A858B;
    }


    div[data-testid="stMetricValue"] {

        font-family:
            'Instrument Serif',
            serif;

        color:
            #4A343C;

        font-size:
            2.2rem;
    }


    /* -----------------------------------------
       TABLES
    ----------------------------------------- */

    div[data-testid="stDataFrame"] {

        border:
            1px solid
            #E9DDDC;

        border-radius:
            18px;

        overflow:
            hidden;
    }


    /* -----------------------------------------
       SELECT BOX
    ----------------------------------------- */

    div[data-baseweb="select"] > div {

        background:
            #FFFDFC;

        border-color:
            #E5D6D9;

        border-radius:
            14px;
    }


    /* -----------------------------------------
       DIVIDERS
    ----------------------------------------- */

    hr {

        border:
            none !important;

        height:
            1px !important;

        background:
            linear-gradient(
                90deg,
                transparent,
                #DFCBCD,
                transparent
            ) !important;

        margin:
            2.5rem 0 !important;
    }


    /* -----------------------------------------
       ALERTS
    ----------------------------------------- */

    div[data-testid="stAlert"] {

        border-radius:
            18px;

        border:
            1px solid
            rgba(
                120,
                80,
                90,
                0.10
            );
    }


    /* -----------------------------------------
       CUSTOM BRAND CLASSES
    ----------------------------------------- */

    .ir-eyebrow {

        font-family:
            'Caveat',
            cursive;

        color:
            #A9677B;

        font-size:
            1.45rem;

        margin-bottom:
            0.2rem;
    }


    .ir-hero-title {

        font-family:
            'Instrument Serif',
            serif;

        font-size:
            5.4rem;

        line-height:
            0.9;

        letter-spacing:
            -0.045em;

        color:
            #33272C;

        margin:
            0;
    }


    .ir-hero-subtitle {

        font-family:
            'Instrument Serif',
            serif;

        font-style:
            italic;

        font-size:
            2rem;

        color:
            #8A6C75;

        margin-top:
            0.7rem;
    }


    .ir-description {

        max-width:
            700px;

        font-family:
            'DM Sans',
            sans-serif;

        font-size:
            1rem;

        color:
            #77686D;

        line-height:
            1.75;

        margin-top:
            1.4rem;
    }


    .ir-pill {

        display:
            inline-block;

        padding:
            7px 14px;

        border-radius:
            999px;

        background:
            #F2DDE3;

        color:
            #754B58;

        font-size:
            0.72rem;

        letter-spacing:
            0.08em;

        text-transform:
            uppercase;

        margin-right:
            6px;

        margin-top:
            8px;
    }


    .ir-note {

        font-family:
            'Caveat',
            cursive;

        font-size:
            1.35rem;

        color:
            #A16878;

        margin-bottom:
            -8px;
    }


    .ir-verdict {

        font-family:
            'Instrument Serif',
            serif;

        font-style:
            italic;

        font-size:
            3rem;

        color:
            #704755;

        line-height:
            1;
    }


    .ir-small {

        font-size:
            0.82rem;

        color:
            #9A858B;

        letter-spacing:
            0.02em;
    }


    /* Hide default Streamlit chrome */

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    </style>
    """,

    unsafe_allow_html=True
)


# =========================================================
# 3. PATHS
# =========================================================

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


# =========================================================
# 4. LOAD DATA
# =========================================================

@st.cache_data
def load_data():

    verdict_df = pd.read_csv(
        VERDICT_FILE
    )

    web_df = pd.read_csv(
        WEB_FILE
    )

    image_df = pd.read_csv(
        IMAGE_FILE
    )

    return (
        verdict_df,
        web_df,
        image_df
    )


df, web_df, image_df = load_data()


# =========================================================
# 5. NORMALIZE TIME
# =========================================================

def normalize_time(dataframe):

    dataframe = dataframe.copy()

    if "Time" not in dataframe.columns:

        dataframe = dataframe.rename(
            columns={
                dataframe.columns[0]:
                    "Time"
            }
        )

    dataframe["Time"] = pd.to_datetime(
        dataframe["Time"],
        errors="coerce"
    )

    dataframe = dataframe.dropna(
        subset=[
            "Time"
        ]
    )

    dataframe = dataframe.sort_values(
        "Time"
    )

    return dataframe


web_df = normalize_time(
    web_df
)

image_df = normalize_time(
    image_df
)


# =========================================================
# 6. PIPELINE STATUS
# =========================================================

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

        timestamp = pd.to_datetime(
            timestamp
        )

        last_updated = timestamp.strftime(
            "%b %d, %Y"
        )


# =========================================================
# 7. HELPERS
# =========================================================

def format_growth(value):

    if pd.isna(value):
        return "No data"

    return f"{value:+.1f}%"


def format_score(value):

    if pd.isna(value):
        return "No data"

    return f"{value:.0f}/100"


def trend_title(value):

    return str(value).title()


def available_columns(
    dataframe,
    columns
):

    return [
        column
        for column in columns
        if column in dataframe.columns
    ]


def display_verdict(verdict):

    mapping = {

        "EARLY":
            "ahead of the curve",

        "HOT":
            "having a moment",

        "STILL IN":
            "still in ♡",

        "PEAKING":
            "everywhere right now",

        "COOLING":
            "quietly fading",

        "WATCH":
            "one to watch"
    }

    return mapping.get(
        verdict,
        str(verdict).lower()
    )


# =========================================================
# 8. HERO
# =========================================================

st.markdown(
    """
    <div class="ir-eyebrow">
        trend notes ♡
    </div>

    <div class="ir-hero-title">
        In Rotation
    </div>

    <div class="ir-hero-subtitle">
        what's rising, what's staying, what's quietly fading.
    </div>

    <div class="ir-description">
        A fashion trend intelligence project tracking
        search behavior, visual interest and media momentum
        to understand what's entering the rotation,
        what's still having a moment,
        and what's slowly fading out.
    </div>

    <br>

    <span class="ir-pill">
        Search
    </span>

    <span class="ir-pill">
        Visual
    </span>

    <span class="ir-pill">
        Media
    </span>
    """,

    unsafe_allow_html=True
)


st.caption(
    f"Updated {last_updated} · "
    f"{len(df)} trends monitored · "
    "Rankings reflect the current In Rotation fashion universe."
)


st.divider()


# =========================================================
# 9. NAVIGATION
# =========================================================

explore_tab, check_tab = st.tabs(
    [
        "Explore the rotation",
        "Check a trend"
    ]
)


# =========================================================
# 10. EXPLORE
# =========================================================

with explore_tab:

    # -----------------------------------------------------
    # CURRENT SNAPSHOT
    # -----------------------------------------------------

    st.markdown(
        """
        <div class="ir-note">
            a little snapshot of fashion right now ♡
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "In rotation right now"
    )


    col1, col2, col3, col4 = st.columns(
        4
    )


    with col1:

        st.metric(
            "Trends Watched",
            len(df)
        )


    with col2:

        high_evidence_count = (
            df["Evidence_Level"]
            .eq("High")
            .sum()
        )

        st.metric(
            "High Evidence",
            high_evidence_count
        )


    with col3:

        rising_count = (
            df["Web_Growth"]
            .gt(0)
            .sum()
        )

        st.metric(
            "Search Rising",
            rising_count
        )


    with col4:

        cooling_count = (
            df["Consumer_Verdict"]
            .eq("COOLING")
            .sum()
        )

        st.metric(
            "Fading",
            cooling_count
        )


    st.divider()


    # =====================================================
    # 11. RISING
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            the things everyone's starting to notice →
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "♡ New to the rotation"
    )

    st.caption(
        "The fastest-growing trends across our monitored fashion universe."
    )


    rising = df.copy()


    if "Ranking_Status" in rising.columns:

        eligible = rising[
            rising["Ranking_Status"]
            == "Eligible"
        ]

        if not eligible.empty:

            rising = eligible


    rising = (
        rising[
            rising["Web_Growth"]
            .notna()
        ]
        .sort_values(
            "Web_Growth",
            ascending=False
        )
        .head(5)
    )


    if rising.empty:

        st.info(
            "Nothing is clearly breaking out right now."
        )

    else:

        for rank, (_, row) in enumerate(
            rising.iterrows(),
            start=1
        ):

            col1, col2, col3, col4 = st.columns(
                [
                    3.5,
                    2,
                    2,
                    2
                ]
            )


            with col1:

                st.markdown(
                    f"### #{rank} "
                    f"{trend_title(row['Trend'])}"
                )


            with col2:

                st.metric(
                    "4W Search",
                    format_growth(
                        row["Web_Growth"]
                    )
                )


            with col3:

                st.write(
                    "**Where it's at**"
                )

                st.write(
                    display_verdict(
                        row[
                            "Consumer_Verdict"
                        ]
                    )
                )


            with col4:

                st.write(
                    "**Evidence**"
                )

                st.write(
                    row[
                        "Evidence_Level"
                    ]
                )


            st.divider()


    # =====================================================
    # 12. EARLY
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            maybe you're seeing it before everyone else...
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "Ahead of the curve"
    )


    early = (
        df[
            df["Consumer_Verdict"]
            == "EARLY"
        ]
        .sort_values(
            "TrendPulse_Score",
            ascending=False
        )
    )


    if early.empty:

        st.info(
            "No convincing early signals right now."
        )

    else:

        early_display = early.copy()

        early_display[
            "Rotation Score"
        ] = early_display[
            "TrendPulse_Score"
        ]

        early_columns = available_columns(
            early_display,
            [
                "Trend",
                "Rotation Score",
                "Web_Growth",
                "Image_Growth",
                "Evidence_Level"
            ]
        )


        st.dataframe(
            early_display[
                early_columns
            ],
            hide_index=True,
            use_container_width=True
        )


    st.divider()


    # =====================================================
    # 13. STILL IN
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            yes, we're still wearing these ♡
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "Still in rotation"
    )


    still_in = (
        df[
            df["Consumer_Verdict"]
            .isin(
                [
                    "HOT",
                    "STILL IN"
                ]
            )
        ]
        .sort_values(
            "TrendPulse_Score",
            ascending=False
        )
    )


    if still_in.empty:

        st.info(
            "Nothing currently falls into this category."
        )

    else:

        still_display = still_in.copy()

        still_display[
            "Rotation Score"
        ] = still_display[
            "TrendPulse_Score"
        ]


        still_display[
            "Status"
        ] = still_display[
            "Consumer_Verdict"
        ].apply(
            display_verdict
        )


        still_columns = available_columns(
            still_display,
            [
                "Trend",
                "Status",
                "Buy_Timing",
                "Rotation Score",
                "Evidence_Level"
            ]
        )


        st.dataframe(
            still_display[
                still_columns
            ],
            hide_index=True,
            use_container_width=True
        )


    st.divider()


    # =====================================================
    # 14. PEAKING
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            maybe don't pay the trend premium...
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "Leaving the rotation?"
    )


    peaking = (
        df[
            df["Consumer_Verdict"]
            == "PEAKING"
        ]
        .sort_values(
            "TrendPulse_Score",
            ascending=False
        )
    )


    if peaking.empty:

        st.info(
            "Nothing is clearly peaking right now."
        )

    else:

        peaking_columns = available_columns(
            peaking,
            [
                "Trend",
                "Buy_Timing",
                "Web_Growth",
                "Image_Growth",
                "Evidence_Level"
            ]
        )


        st.dataframe(
            peaking[
                peaking_columns
            ],
            hide_index=True,
            use_container_width=True
        )


    st.divider()


    # =====================================================
    # 15. COOLING
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            still cute — just not necessarily trending ♡
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "Quietly fading"
    )


    cooling = (
        df[
            df["Consumer_Verdict"]
            == "COOLING"
        ]
        .sort_values(
            "Web_Growth",
            ascending=True
        )
    )


    if cooling.empty:

        st.info(
            "Nothing is clearly fading right now."
        )

    else:

        cooling_columns = available_columns(
            cooling,
            [
                "Trend",
                "Buy_Timing",
                "Web_Growth",
                "Trend_Risk",
                "Evidence_Level"
            ]
        )


        st.dataframe(
            cooling[
                cooling_columns
            ],
            hide_index=True,
            use_container_width=True
        )


# =========================================================
# 16. CHECK A TREND
# =========================================================

with check_tab:

    st.markdown(
        """
        <div class="ir-note">
            still in, or already on the way out?
        </div>
        """,
        unsafe_allow_html=True
    )

    st.header(
        "Check the rotation"
    )


    st.write(
        """
        Choose a trend to see whether it's entering the rotation,
        still holding on, or starting to fade.
        """
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


    st.divider()


    # =====================================================
    # 17. TREND VERDICT
    # =====================================================

    st.title(
        trend_title(
            trend
        )
    )


    st.markdown(
        f"""
        <div class="ir-verdict">
            {display_verdict(selected["Consumer_Verdict"])}
        </div>
        """,
        unsafe_allow_html=True
    )


    st.markdown(
        f"### {selected['Buy_Timing']}"
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        st.metric(
            "Rotation Score",
            format_score(
                selected[
                    "TrendPulse_Score"
                ]
            )
        )


    with col2:

        st.metric(
            "Trend Risk",
            selected[
                "Trend_Risk"
            ]
        )


    with col3:

        st.metric(
            "Evidence",
            selected[
                "Evidence_Level"
            ]
        )


    # =====================================================
    # 18. EXPLANATION
    # =====================================================

    st.divider()


    st.markdown(
        """
        <div class="ir-note">
            what we're seeing...
        </div>
        """,
        unsafe_allow_html=True
    )


    st.header(
        "Why?"
    )


    if "Consumer_Explanation" in selected.index:

        st.write(
            selected[
                "Consumer_Explanation"
            ]
        )


    if "Evidence_Caution" in selected.index:

        caution = selected[
            "Evidence_Caution"
        ]


        if selected[
            "Evidence_Level"
        ] == "High":

            st.success(
                caution
            )

        else:

            st.warning(
                caution
            )


    # =====================================================
    # 19. MOMENTUM
    # =====================================================

    st.header(
        "The signals"
    )


    col1, col2, col3 = st.columns(
        3
    )


    with col1:

        st.metric(
            "Web Search · 4W",
            format_growth(
                selected[
                    "Web_Growth"
                ]
            )
        )


    with col2:

        st.metric(
            "Visual Search · 4W",
            format_growth(
                selected[
                    "Image_Growth"
                ]
            )
        )


    with col3:

        st.metric(
            "Media Momentum",
            format_score(
                selected[
                    "Media_Score"
                ]
            )
        )


    # =====================================================
    # 20. WEB SEARCH CHART
    # =====================================================

    st.divider()


    st.markdown(
        """
        <div class="ir-note">
            are people still searching for it?
        </div>
        """,
        unsafe_allow_html=True
    )


    st.header(
        "Search interest"
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


    else:

        st.info(
            "No Web Search history available."
        )


    # =====================================================
    # 21. IMAGE SEARCH CHART
    # =====================================================

    st.markdown(
        """
        <div class="ir-note">
            are we still looking at it? ♡
        </div>
        """,
        unsafe_allow_html=True
    )


    st.header(
        "Visual interest"
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


    else:

        st.info(
            "No Image Search history available."
        )


    # =====================================================
    # 22. INTERPRETATION
    # =====================================================

    st.divider()


    with st.expander(
        "How In Rotation reads a trend"
    ):

        st.markdown(
            """
### ahead of the curve
The trend is beginning to show positive momentum but has
not fully entered the mainstream.

### having a moment
Several signals indicate strong current acceleration.

### still in ♡
The trend is already established but remains relevant.

### everywhere right now
The trend is still highly visible, but recent momentum
is beginning to weaken.

### quietly fading
Multiple signals indicate declining consumer interest.

### Evidence

**High**  
Multiple signals and sufficient underlying data support
the verdict.

**Medium**  
The trend has usable evidence, but some signals are mixed
or limited.

**Low**  
The result should be interpreted carefully because the
underlying search or media base is small.

### Rotation Score

The Rotation Score is In Rotation's combined momentum
indicator based on search, visual and media signals.

The score is calculated from the existing backend
`TrendPulse_Score`; only the consumer-facing name has changed.

In Rotation measures trend momentum within its monitored
fashion universe. It does not decide whether something is
personally stylish or whether you should stop wearing
something you love.
            """
        )
