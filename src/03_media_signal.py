import pandas as pd
import feedparser
import requests
import time

from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime, timezone


# ==================================================
# 1. Project paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"

TREND_MASTER_FILE = (
    DATA_DIR
    / "trend_master.csv"
)

OUTPUT_FILE = (
    PROCESSED_DIR
    / "media_signal.csv"
)


# ==================================================
# 2. Load monitored trend universe
# ==================================================

trend_master = pd.read_csv(
    TREND_MASTER_FILE
)


monitor_df = trend_master[
    trend_master["Status"].isin(
        [
            "Active",
            "Watch"
        ]
    )
].copy()


monitor_df = monitor_df[
    monitor_df["Trend"].notna()
].copy()


TRENDS = (
    monitor_df["Trend"]
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)


print(
    f"\nMonitoring media for {len(TRENDS)} trends."
)


# ==================================================
# 3. Google News RSS fetch
# ==================================================

def fetch_feed(trend):

    query = quote_plus(
        f'"{trend}" fashion'
    )

    url = (
        "https://news.google.com/rss/search?"
        f"q={query}"
        "&hl=en-US"
        "&gl=US"
        "&ceid=US:en"
    )

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()

            return feedparser.parse(
                response.content
            )

        except requests.RequestException as error:

            print(
                f"Attempt {attempt + 1} failed "
                f"for {trend}: {error}"
            )

            time.sleep(
                2 * (attempt + 1)
            )

    return None


# ==================================================
# 4. Calculate media signal
# ==================================================

def get_media_signal(trend):

    feed = fetch_feed(
        trend
    )

    if feed is None:

        return {
            "Trend": trend,
            "Media_Current_7D": None,
            "Media_Previous_7D": None,
            "Media_30D": None,
            "Media_Momentum_Index": None,
            "Media_Data_Status": "Fetch Failed"
        }


    today = datetime.now(
        timezone.utc
    )


    current_7d = 0
    previous_7d = 0
    current_30d = 0


    # Prevent duplicate Google News entries
    seen_articles = set()


    for article in feed.entries:

        if not hasattr(
            article,
            "published_parsed"
        ):
            continue


        published = datetime(
            *article.published_parsed[:6],
            tzinfo=timezone.utc
        )


        age_days = (
            today
            - published
        ).days


        if age_days < 0:
            continue


        title = (
            getattr(
                article,
                "title",
                ""
            )
            .lower()
            .strip()
        )


        link = getattr(
            article,
            "link",
            ""
        )


        article_key = (
            title,
            link
        )


        if article_key in seen_articles:
            continue


        seen_articles.add(
            article_key
        )


        if age_days < 7:

            current_7d += 1


        elif age_days < 14:

            previous_7d += 1


        if age_days < 30:

            current_30d += 1


    # ==================================================
    # Stable media momentum
    # ==================================================

    total = (
        current_7d
        + previous_7d
    )


    if total == 0:

        momentum_index = 50.0

        status = "Low Signal"


    else:

        symmetric_change = (
            200
            * (
                current_7d
                - previous_7d
            )
            / total
        )


        momentum_index = (
            symmetric_change
            + 200
        ) / 4


        momentum_index = round(
            momentum_index,
            2
        )


        status = "Valid"


    return {

        "Trend":
            trend,

        "Media_Current_7D":
            current_7d,

        "Media_Previous_7D":
            previous_7d,

        "Media_30D":
            current_30d,

        "Media_Momentum_Index":
            momentum_index,

        "Media_Data_Status":
            status
    }


# ==================================================
# 5. Run all trends
# ==================================================

results = []


for number, trend in enumerate(
    TRENDS,
    start=1
):

    print(
        f"\n[{number}/{len(TRENDS)}] "
        f"Checking: {trend}"
    )


    result = get_media_signal(
        trend
    )


    results.append(
        result
    )


    # Avoid hammering Google News
    time.sleep(
        1
    )


media = pd.DataFrame(
    results
)


# ==================================================
# 6. Rank media momentum
# ==================================================

media[
    "Media_Rank"
] = (
    media[
        "Media_Momentum_Index"
    ]
    .rank(
        method="min",
        ascending=False
    )
    .astype(
        "Int64"
    )
)


media = media.sort_values(
    "Media_Momentum_Index",
    ascending=False,
    na_position="last"
)


# ==================================================
# 7. Display
# ==================================================

print(
    "\n========== MEDIA SIGNAL: ALL TRENDS =========="
)


print(
    media[
        [
            "Media_Rank",
            "Trend",
            "Media_Current_7D",
            "Media_Previous_7D",
            "Media_30D",
            "Media_Momentum_Index",
            "Media_Data_Status"
        ]
    ]
    .to_string(
        index=False
    )
)


# ==================================================
# 8. Save
# ==================================================

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


media.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "\nSaved:"
)

print(
    OUTPUT_FILE
)