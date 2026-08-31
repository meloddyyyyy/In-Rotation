import pandas as pd
import time

from pathlib import Path
from pytrends_modern import TrendReq


# ==================================================
# 1. Project paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"

TREND_MASTER_FILE = (
    DATA_DIR
    / "trend_master.csv"
)

WEB_OUTPUT_FILE = (
    RAW_DIR
    / "auto_google_web.csv"
)

IMAGE_OUTPUT_FILE = (
    RAW_DIR
    / "auto_google_image.csv"
)


# ==================================================
# 2. Google Trends settings
# ==================================================

GEO = "US"

TIMEFRAME = "today 12-m"

# Google Trends allows max 5 terms
# per request.
BATCH_SIZE = 5

# Pause between requests to reduce
# rate-limit problems.
REQUEST_DELAY = 4

MAX_RETRIES = 3


# ==================================================
# 3. Load trend universe
# ==================================================

trend_master = pd.read_csv(
    TREND_MASTER_FILE
)


required_columns = [
    "Trend",
    "Search_Term",
    "Status"
]


for column in required_columns:

    if column not in trend_master.columns:

        raise ValueError(
            f"trend_master.csv is missing column: {column}"
        )


# Monitor both Active and Watch trends
monitor_df = trend_master[
    trend_master["Status"]
    .isin(
        [
            "Active",
            "Watch"
        ]
    )
].copy()


# Remove empty search terms
monitor_df = monitor_df[
    monitor_df["Search_Term"]
    .notna()
].copy()


monitor_df["Search_Term"] = (
    monitor_df["Search_Term"]
    .astype(str)
    .str.strip()
)


monitor_df["Trend"] = (
    monitor_df["Trend"]
    .astype(str)
    .str.strip()
)


# Remove blank rows
monitor_df = monitor_df[
    monitor_df["Search_Term"] != ""
].copy()


# Remove duplicated search terms
monitor_df = (
    monitor_df
    .drop_duplicates(
        subset=[
            "Search_Term"
        ]
    )
)


# ==================================================
# 4. Search-term mapping
# ==================================================

# Example:
#
# "butter yellow fashion"
# ->
# "butter yellow"

term_to_trend = dict(
    zip(
        monitor_df["Search_Term"],
        monitor_df["Trend"]
    )
)


search_terms = list(
    term_to_trend.keys()
)


print(
    "\n========== TREND UNIVERSE =========="
)

print(
    f"Monitoring {len(search_terms)} trends."
)


for number, term in enumerate(
    search_terms,
    start=1
):

    print(
        f"{number}. {term}"
    )


# ==================================================
# 5. Create batches
# ==================================================

def create_batches(
    items,
    batch_size
):

    return [

        items[
            i:i + batch_size
        ]

        for i in range(
            0,
            len(items),
            batch_size
        )
    ]


batches = create_batches(
    search_terms,
    BATCH_SIZE
)


print(
    f"\nCreated {len(batches)} Google Trends batches."
)


# ==================================================
# 6. Google Trends client
# ==================================================

pytrends = TrendReq(
    hl="en-US",
    tz=360,
    timeout=(10, 30),
    retries=2,
    backoff_factor=0.5
)


# ==================================================
# 7. Fetch one batch
# ==================================================

def fetch_batch(
    keywords,
    search_type
):

    if search_type == "web":

        gprop = ""

    elif search_type == "image":

        gprop = "images"

    else:

        raise ValueError(
            "search_type must be 'web' or 'image'"
        )


    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            print(
                f"\nFetching {search_type.upper()}:"
            )

            print(
                keywords
            )


            pytrends.build_payload(
                kw_list=keywords,
                timeframe=TIMEFRAME,
                geo=GEO,
                gprop=gprop
            )


            data = (
                pytrends
                .interest_over_time()
            )


            if data is None:

                print(
                    "Google returned None."
                )

                return None


            if data.empty:

                print(
                    "Google returned an empty DataFrame."
                )

                return None


            # Remove metadata column
            if "isPartial" in data.columns:

                data = data.drop(
                    columns=[
                        "isPartial"
                    ]
                )


            data = (
                data
                .reset_index()
            )


            # Whatever Google calls the
            # first column, normalize it to Time.
            data = data.rename(
                columns={
                    data.columns[0]:
                    "Time"
                }
            )


            data["Time"] = pd.to_datetime(
                data["Time"],
                errors="coerce"
            )


            data = data.dropna(
                subset=[
                    "Time"
                ]
            )


            return data


        except Exception as error:

            print(
                f"\nAttempt {attempt}/{MAX_RETRIES} failed:"
            )

            print(
                type(error).__name__
            )

            print(
                error
            )


            if attempt < MAX_RETRIES:

                wait_time = (
                    attempt
                    * 8
                )

                print(
                    f"Waiting {wait_time} seconds before retry..."
                )

                time.sleep(
                    wait_time
                )


    print(
        "\nBatch failed after all retries."
    )

    return None


# ==================================================
# 8. Collect all batches
# ==================================================

def collect_all(
    search_type
):

    all_batches = []


    for batch_number, batch in enumerate(
        batches,
        start=1
    ):

        print(
            "\n=========================================="
        )

        print(
            f"{search_type.upper()} "
            f"BATCH {batch_number}/{len(batches)}"
        )

        print(
            "=========================================="
        )


        batch_data = fetch_batch(
            batch,
            search_type
        )


        if batch_data is None:

            print(
                "Skipping this batch."
            )

            continue


        # Rename Google search term
        # into our canonical trend name.
        rename_map = {

            term:
            term_to_trend[term]

            for term in batch

            if term in term_to_trend
        }


        batch_data = (
            batch_data
            .rename(
                columns=rename_map
            )
        )


        all_batches.append(
            batch_data
        )


        print(
            f"Batch {batch_number} collected successfully."
        )


        time.sleep(
            REQUEST_DELAY
        )


    # No successful batches
    if len(all_batches) == 0:

        return pd.DataFrame()


    # ----------------------------------------------
    # Merge batches by Time
    # ----------------------------------------------

    merged = all_batches[0]


    for batch_data in all_batches[1:]:

        merged = pd.merge(
            merged,
            batch_data,
            on="Time",
            how="outer"
        )


    merged = (
        merged
        .sort_values(
            "Time"
        )
        .reset_index(
            drop=True
        )
    )


    return merged


# ==================================================
# 9. Collect Web Search
# ==================================================

print(
    "\n\n##########################################"
)

print(
    "STARTING WEB SEARCH COLLECTION"
)

print(
    "##########################################"
)


web_data = collect_all(
    "web"
)


# ==================================================
# 10. Pause before Image Search
# ==================================================

print(
    "\nWaiting before Image Search..."
)

time.sleep(
    8
)


# ==================================================
# 11. Collect Image Search
# ==================================================

print(
    "\n\n##########################################"
)

print(
    "STARTING IMAGE SEARCH COLLECTION"
)

print(
    "##########################################"
)


image_data = collect_all(
    "image"
)


# ==================================================
# 12. Save
# ==================================================

RAW_DIR.mkdir(
    parents=True,
    exist_ok=True
)


web_data.to_csv(
    WEB_OUTPUT_FILE,
    index=False
)


image_data.to_csv(
    IMAGE_OUTPUT_FILE,
    index=False
)


# ==================================================
# 13. Collection summary
# ==================================================

print(
    "\n\n========== COLLECTION COMPLETE =========="
)


if web_data.empty:

    print(
        "\nWEB SEARCH:"
    )

    print(
        "No Web Search data collected."
    )

else:

    print(
        "\nWEB SEARCH:"
    )

    print(
        f"{len(web_data.columns) - 1} trends collected."
    )

    print(
        "Columns:"
    )

    print(
        web_data.columns.tolist()
    )


if image_data.empty:

    print(
        "\nIMAGE SEARCH:"
    )

    print(
        "No Image Search data collected."
    )

else:

    print(
        "\nIMAGE SEARCH:"
    )

    print(
        f"{len(image_data.columns) - 1} trends collected."
    )

    print(
        "Columns:"
    )

    print(
        image_data.columns.tolist()
    )


print(
    "\nSaved Web data:"
)

print(
    WEB_OUTPUT_FILE
)


print(
    "\nSaved Image data:"
)

print(
    IMAGE_OUTPUT_FILE
)