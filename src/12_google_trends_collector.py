import os
import time
from pathlib import Path

import pandas as pd
from pytrends_modern import TrendReq

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
TREND_MASTER_FILE = DATA_DIR / "trend_master.csv"
WEB_OUTPUT_FILE = RAW_DIR / "auto_google_web.csv"
IMAGE_OUTPUT_FILE = RAW_DIR / "auto_google_image.csv"

GEO = "US"
TIMEFRAME = "today 12-m"
BATCH_SIZE = 5
REQUEST_DELAY = 4
MAX_RETRIES = 3

trend_master = pd.read_csv(TREND_MASTER_FILE)
required_columns = ["Trend", "Search_Term", "Status"]
for column in required_columns:
    if column not in trend_master.columns:
        raise ValueError(f"trend_master.csv is missing column: {column}")

monitor_df = trend_master[
    trend_master["Status"].isin(["Active", "Watch"])
].copy()
monitor_df = monitor_df[monitor_df["Search_Term"].notna()].copy()
monitor_df["Search_Term"] = monitor_df["Search_Term"].astype(str).str.strip()
monitor_df["Trend"] = monitor_df["Trend"].astype(str).str.strip()
monitor_df = monitor_df[monitor_df["Search_Term"] != ""].drop_duplicates("Search_Term")

term_to_trend = dict(zip(monitor_df["Search_Term"], monitor_df["Trend"]))
search_terms = list(term_to_trend.keys())


def create_batches(items, batch_size):
    return [items[i : i + batch_size] for i in range(0, len(items), batch_size)]


batches = create_batches(search_terms, BATCH_SIZE)
client = TrendReq(
    hl="en-US",
    tz=360,
    timeout=(10, 30),
    retries=2,
    backoff_factor=0.5,
)


def fetch_batch(keywords, search_type):
    gprop = "" if search_type == "web" else "images"
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client.build_payload(
                kw_list=keywords,
                timeframe=TIMEFRAME,
                geo=GEO,
                gprop=gprop,
            )
            data = client.interest_over_time()
            if data is None or data.empty:
                return None
            if "isPartial" in data.columns:
                data = data.drop(columns=["isPartial"])
            data = data.reset_index()
            data = data.rename(columns={data.columns[0]: "Time"})
            data["Time"] = pd.to_datetime(data["Time"], errors="coerce")
            data = data.dropna(subset=["Time"])
            return data
        except Exception as error:
            print(f"Attempt {attempt}/{MAX_RETRIES} failed: {error}")
            if attempt < MAX_RETRIES:
                time.sleep(attempt * 8)
    return None


def collect_all(search_type):
    all_batches = []
    for batch_number, batch in enumerate(batches, start=1):
        print(f"\n{search_type.upper()} BATCH {batch_number}/{len(batches)}: {batch}")
        batch_data = fetch_batch(batch, search_type)
        if batch_data is None:
            print("Skipping failed/empty batch.")
            continue

        rename_map = {term: term_to_trend[term] for term in batch if term in term_to_trend}
        batch_data = batch_data.rename(columns=rename_map)
        all_batches.append(batch_data)
        time.sleep(REQUEST_DELAY)

    if not all_batches:
        return pd.DataFrame()

    merged = all_batches[0]
    for batch_data in all_batches[1:]:
        merged = pd.merge(merged, batch_data, on="Time", how="outer")
    return merged.sort_values("Time").reset_index(drop=True)


def validate_frame(df, expected_trends):
    if df is None or df.empty:
        return False, "dataframe is empty"
    if "Time" not in df.columns:
        return False, "missing Time column"

    trend_columns = [column for column in df.columns if column != "Time"]
    if not trend_columns:
        return False, "no trend columns"

    usable = df[trend_columns].apply(pd.to_numeric, errors="coerce")
    if usable.dropna(how="all").empty:
        return False, "no usable trend rows"

    missing_trends = set(expected_trends) - set(trend_columns)
    if missing_trends:
        return False, f"missing expected trends: {sorted(missing_trends)}"

    return True, "ok"


def atomic_save(df, output_file, expected_trends):
    valid, reason = validate_frame(df, expected_trends)
    if not valid:
        print(f"WARNING: not replacing {output_file.name}: {reason}")
        if output_file.exists() and output_file.stat().st_size > 0:
            print("Keeping previous good CSV.")
            return False
        raise RuntimeError(
            f"No valid previous file exists for {output_file.name}; collection failed: {reason}"
        )

    output_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = output_file.with_suffix(output_file.suffix + ".tmp")
    df.to_csv(temp_file, index=False)

    try:
        check = pd.read_csv(temp_file)
        valid, reason = validate_frame(check, expected_trends)
        if not valid:
            raise RuntimeError(f"temporary CSV failed validation: {reason}")
        os.replace(temp_file, output_file)
    finally:
        if temp_file.exists():
            temp_file.unlink(missing_ok=True)

    print(f"Saved valid data: {output_file}")
    return True


print(f"\nMonitoring {len(search_terms)} production trends.")
web_data = collect_all("web")
print("\nWaiting before Image Search...")
time.sleep(8)
image_data = collect_all("image")

expected_trends = list(term_to_trend.values())
atomic_save(web_data, WEB_OUTPUT_FILE, expected_trends)
atomic_save(image_data, IMAGE_OUTPUT_FILE, expected_trends)

print("\n========== COLLECTION COMPLETE ==========")
print(f"Web trends collected: {len(web_data.columns) - 1 if not web_data.empty else 0}")
print(f"Image trends collected: {len(image_data.columns) - 1 if not image_data.empty else 0}")
