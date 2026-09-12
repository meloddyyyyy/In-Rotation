from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

WEB_FILE = RAW_DIR / "auto_google_web.csv"
IMAGE_FILE = RAW_DIR / "auto_google_image.csv"


def read_valid_trends_csv(path, label):
    if not path.exists():
        raise RuntimeError(
            f"{label} file is missing: {path}. Run 12_google_trends_collector.py first."
        )
    if path.stat().st_size == 0:
        raise RuntimeError(
            f"{label} file is empty: {path}. Re-run 12_google_trends_collector.py; the collector now preserves prior valid files on failed refreshes."
        )
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError as error:
        raise RuntimeError(f"{label} file has no parseable columns: {path}") from error

    if df.empty:
        raise RuntimeError(f"{label} file contains no rows: {path}")
    if "Time" not in df.columns:
        raise RuntimeError(f"{label} file is missing required Time column: {path}")

    trend_columns = [column for column in df.columns if column != "Time"]
    if not trend_columns:
        raise RuntimeError(f"{label} file contains no trend columns: {path}")

    return df


web = read_valid_trends_csv(WEB_FILE, "Web Search")
image = read_valid_trends_csv(IMAGE_FILE, "Image Search")

print("\nWEB COLUMNS:")
print(web.columns.tolist())
print("\nIMAGE COLUMNS:")
print(image.columns.tolist())


def clean_trends_data(df):
    df = df.copy()
    df["Time"] = pd.to_datetime(df["Time"], errors="coerce")
    df = df.dropna(subset=["Time"])
    trend_columns = [column for column in df.columns if column != "Time"]
    for column in trend_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.sort_values("Time").reset_index(drop=True)


def remove_incomplete_week(df):
    df = df.copy()
    if df.empty:
        return df
    latest_time = df["Time"].max()
    today = pd.Timestamp.today().normalize()
    if latest_time + pd.Timedelta(days=7) > today:
        print("\nRemoving incomplete week:")
        print(latest_time)
        df = df[df["Time"] < latest_time]
    return df


web = remove_incomplete_week(clean_trends_data(web))
image = remove_incomplete_week(clean_trends_data(image))

print("\nLatest complete Web week:")
print(web["Time"].max())
print("\nLatest complete Image week:")
print(image["Time"].max())


def calculate_momentum(df, source_name):
    results = []
    trend_columns = [column for column in df.columns if column != "Time"]

    for trend in trend_columns:
        values = df[["Time", trend]].dropna(subset=[trend])
        if len(values) < 8:
            results.append(
                {
                    "Trend": trend,
                    f"{source_name}_Recent_4W": None,
                    f"{source_name}_Previous_4W": None,
                    f"{source_name}_Growth": None,
                    f"{source_name}_Data_Status": "Insufficient Data",
                }
            )
            continue

        recent_4w = values[trend].tail(4).mean()
        previous_4w = values[trend].iloc[-8:-4].mean()

        if pd.notna(previous_4w) and previous_4w > 0:
            growth = ((recent_4w - previous_4w) / previous_4w) * 100
            status = "Valid"
        elif previous_4w == 0 and recent_4w > 0:
            growth = None
            status = "New Signal"
        else:
            growth = None
            status = "Low Signal"

        results.append(
            {
                "Trend": trend,
                f"{source_name}_Recent_4W": round(recent_4w, 2),
                f"{source_name}_Previous_4W": round(previous_4w, 2),
                f"{source_name}_Growth": round(growth, 2) if growth is not None else None,
                f"{source_name}_Data_Status": status,
            }
        )

    return pd.DataFrame(results)


web_summary = calculate_momentum(web, "Web")
image_summary = calculate_momentum(image, "Image")
summary = pd.merge(web_summary, image_summary, on="Trend", how="outer")
summary["Visual_Momentum_Gap"] = (
    summary["Image_Growth"] - summary["Web_Growth"]
).round(2)
summary["Web_Growth_Rank"] = summary["Web_Growth"].rank(
    method="min", ascending=False
).astype("Int64")
summary["Image_Growth_Rank"] = summary["Image_Growth"].rank(
    method="min", ascending=False
).astype("Int64")
summary = summary.sort_values(
    "Web_Growth", ascending=False, na_position="last"
).reset_index(drop=True)

print("\n========== FASTEST RISING: WEB SEARCH ==========")
print(
    summary[
        [
            "Web_Growth_Rank",
            "Trend",
            "Web_Previous_4W",
            "Web_Recent_4W",
            "Web_Growth",
            "Web_Data_Status",
        ]
    ]
    .head(20)
    .to_string(index=False)
)

print("\n========== IMAGE SEARCH MOMENTUM ==========")
print(
    summary[
        [
            "Image_Growth_Rank",
            "Trend",
            "Image_Previous_4W",
            "Image_Recent_4W",
            "Image_Growth",
            "Image_Data_Status",
        ]
    ]
    .sort_values("Image_Growth", ascending=False, na_position="last")
    .head(20)
    .to_string(index=False)
)

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
web.to_csv(PROCESSED_DIR / "web_search_clean.csv", index=False)
image.to_csv(PROCESSED_DIR / "image_search_clean.csv", index=False)
summary.to_csv(PROCESSED_DIR / "search_signal_summary.csv", index=False)

print("\nFiles saved successfully.")
print("\nNumber of trends analyzed:")
print(len(summary))
