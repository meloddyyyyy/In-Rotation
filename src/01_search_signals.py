import pandas as pd
from pathlib import Path


def load_google_trends_csv(path, label):

    path = Path(path)

    if not path.exists():

        raise FileNotFoundError(
            f"{label} file is missing: {path}\n"
            "Run src/12_google_trends_collector.py first. "
            "If collection failed, restore the last good CSV "
            "instead of reading an empty extract."
        )

    if path.stat().st_size == 0:

        raise ValueError(
            f"{label} file is empty (0 bytes): {path}\n"
            "A failed Google Trends collection likely overwrote it. "
            "Do not call pd.read_csv() on this file. "
            "Restore the last non-empty auto_google_*.csv and re-run "
            "12_google_trends_collector.py (it will no longer replace "
            "good history with an empty file)."
        )

    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:

        raise ValueError(
            f"{label} file has no columns to parse: {path}\n"
            "The file exists but is blank. Restore the previous good "
            "CSV and re-run collection. Original pandas error: "
            f"{error}"
        ) from None

    if df.empty:

        raise ValueError(
            f"{label} file parsed but contains no rows: {path}\n"
            "Restore historical Google Trends data before running "
            "search-signal processing."
        )

    if "Time" not in df.columns:

        raise ValueError(
            f"{label} file is missing a Time column: {path}\n"
            f"Found columns: {df.columns.tolist()}"
        )

    trend_columns = [
        column
        for column in df.columns
        if column != "Time"
    ]

    if len(trend_columns) == 0:

        raise ValueError(
            f"{label} file has Time but no trend columns: {path}"
        )

    usable_times = pd.to_datetime(
        df["Time"],
        errors="coerce"
    ).notna()

    if not usable_times.any():

        raise ValueError(
            f"{label} file has no usable Time values: {path}"
        )

    numeric = df.loc[
        usable_times,
        trend_columns
    ].apply(
        pd.to_numeric,
        errors="coerce"
    )

    if not numeric.notna().any().any():

        raise ValueError(
            f"{label} file has no usable numeric trend values: {path}"
        )

    return df


# ==================================================
# 1. Project paths
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RAW_DIR = (
    BASE_DIR
    / "data"
    / "raw"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)


WEB_FILE = (
    RAW_DIR
    / "auto_google_web.csv"
)

IMAGE_FILE = (
    RAW_DIR
    / "auto_google_image.csv"
)


# ==================================================
# 2. Load automatically collected Google Trends data
# ==================================================

web = load_google_trends_csv(
    WEB_FILE,
    "Web Search"
)

image = load_google_trends_csv(
    IMAGE_FILE,
    "Image Search"
)


print(
    "\nWEB COLUMNS:"
)

print(
    web.columns.tolist()
)


print(
    "\nIMAGE COLUMNS:"
)

print(
    image.columns.tolist()
)


# ==================================================
# 3. Clean data
# ==================================================

def clean_trends_data(df):

    df = df.copy()

    # ----------------------------------------------
    # Make sure first column is always Time
    # ----------------------------------------------

    if "Time" not in df.columns:

        df = df.rename(
            columns={
                df.columns[0]:
                "Time"
            }
        )


    # ----------------------------------------------
    # Convert Time into datetime
    # ----------------------------------------------

    df["Time"] = pd.to_datetime(
        df["Time"],
        errors="coerce"
    )


    df = df.dropna(
        subset=[
            "Time"
        ]
    )


    # ----------------------------------------------
    # Convert all trend columns to numeric
    # ----------------------------------------------

    trend_columns = [
        column
        for column in df.columns
        if column != "Time"
    ]


    for column in trend_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )


    # ----------------------------------------------
    # Sort chronologically
    # ----------------------------------------------

    df = (
        df
        .sort_values(
            "Time"
        )
        .reset_index(
            drop=True
        )
    )


    return df


web = clean_trends_data(
    web
)

image = clean_trends_data(
    image
)


# ==================================================
# 4. Remove incomplete current week
# ==================================================

def remove_incomplete_week(df):

    df = df.copy()

    if df.empty:
        return df


    latest_time = (
        df["Time"]
        .max()
    )


    today = (
        pd.Timestamp
        .today()
        .normalize()
    )


    # If Google's latest weekly point
    # has not completed its full 7-day period,
    # remove it.

    if (
        latest_time
        + pd.Timedelta(
            days=7
        )
        > today
    ):

        print(
            "\nRemoving incomplete week:"
        )

        print(
            latest_time
        )

        df = df[
            df["Time"]
            < latest_time
        ]


    return df


web = remove_incomplete_week(
    web
)

image = remove_incomplete_week(
    image
)


print(
    "\nLatest complete Web week:"
)

print(
    web["Time"].max()
)


print(
    "\nLatest complete Image week:"
)

print(
    image["Time"].max()
)


# ==================================================
# 5. Calculate 4-week momentum
# ==================================================

def calculate_momentum(
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
            df[
                [
                    "Time",
                    trend
                ]
            ]
            .dropna(
                subset=[
                    trend
                ]
            )
        )


        # Need at least 8 weeks
        # for Recent 4W vs Previous 4W.

        if len(values) < 8:

            results.append(
                {
                    "Trend":
                        trend,

                    f"{source_name}_Recent_4W":
                        None,

                    f"{source_name}_Previous_4W":
                        None,

                    f"{source_name}_Growth":
                        None,

                    f"{source_name}_Data_Status":
                        "Insufficient Data"
                }
            )

            continue


        recent_4w = (
            values[trend]
            .tail(4)
            .mean()
        )


        previous_4w = (
            values[trend]
            .iloc[-8:-4]
            .mean()
        )


        # ------------------------------------------
        # Percentage growth
        # ------------------------------------------

        if (
            pd.notna(previous_4w)
            and previous_4w > 0
        ):

            growth = (
                (
                    recent_4w
                    - previous_4w
                )
                / previous_4w
            ) * 100

            status = "Valid"


        elif (
            previous_4w == 0
            and recent_4w > 0
        ):

            # New signal appearing from near zero.
            # We don't pretend this has a normal
            # percentage growth rate.

            growth = None

            status = "New Signal"


        else:

            growth = None

            status = "Low Signal"


        results.append(
            {
                "Trend":
                    trend,

                f"{source_name}_Recent_4W":
                    round(
                        recent_4w,
                        2
                    ),

                f"{source_name}_Previous_4W":
                    round(
                        previous_4w,
                        2
                    ),

                f"{source_name}_Growth":
                    (
                        round(
                            growth,
                            2
                        )
                        if growth is not None
                        else None
                    ),

                f"{source_name}_Data_Status":
                    status
            }
        )


    return pd.DataFrame(
        results
    )


web_summary = calculate_momentum(
    web,
    "Web"
)


image_summary = calculate_momentum(
    image,
    "Image"
)


# ==================================================
# 6. Merge Web + Image signals
# ==================================================

summary = pd.merge(
    web_summary,
    image_summary,
    on="Trend",
    how="outer"
)


summary[
    "Visual_Momentum_Gap"
] = (
    summary["Image_Growth"]
    - summary["Web_Growth"]
).round(2)


# ==================================================
# 7. Fastest-rising ranking
# ==================================================

summary[
    "Web_Growth_Rank"
] = (
    summary["Web_Growth"]
    .rank(
        method="min",
        ascending=False
    )
    .astype(
        "Int64"
    )
)


summary[
    "Image_Growth_Rank"
] = (
    summary["Image_Growth"]
    .rank(
        method="min",
        ascending=False
    )
    .astype(
        "Int64"
    )
)


summary = (
    summary
    .sort_values(
        "Web_Growth",
        ascending=False,
        na_position="last"
    )
    .reset_index(
        drop=True
    )
)


# ==================================================
# 8. Display ranking
# ==================================================

print(
    "\n========== FASTEST RISING: WEB SEARCH =========="
)


print(
    summary[
        [
            "Web_Growth_Rank",
            "Trend",
            "Web_Previous_4W",
            "Web_Recent_4W",
            "Web_Growth",
            "Web_Data_Status"
        ]
    ]
    .head(20)
    .to_string(
        index=False
    )
)


print(
    "\n========== IMAGE SEARCH MOMENTUM =========="
)


print(
    summary[
        [
            "Image_Growth_Rank",
            "Trend",
            "Image_Previous_4W",
            "Image_Recent_4W",
            "Image_Growth",
            "Image_Data_Status"
        ]
    ]
    .sort_values(
        "Image_Growth",
        ascending=False,
        na_position="last"
    )
    .head(20)
    .to_string(
        index=False
    )
)


# ==================================================
# 9. Save processed data
# ==================================================

PROCESSED_DIR.mkdir(
    parents=True,
    exist_ok=True
)


web.to_csv(
    PROCESSED_DIR
    / "web_search_clean.csv",
    index=False
)


image.to_csv(
    PROCESSED_DIR
    / "image_search_clean.csv",
    index=False
)


summary.to_csv(
    PROCESSED_DIR
    / "search_signal_summary.csv",
    index=False
)


print(
    "\nFiles saved successfully."
)


print(
    "\nNumber of trends analyzed:"
)

print(
    len(summary)
)
