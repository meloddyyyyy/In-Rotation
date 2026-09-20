import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

CORE_PIPELINE = [
    "12_google_trends_collector.py",
    "01_search_signals.py",
    "02_trend_stage.py",
    "03_media_signal.py",
    "04_signal_integration.py",
    "5_universal_scoring.py",
    "11_consumer_verdict.py",
    "13_reliability_filter.py",
]

CANDIDATE_PIPELINE = [
    "17_candidate_pool.py",
    "18_candidate_editorial_collector.py",
    "15_candidate_google_collector.py",
    "19_candidate_visual_collector.py",
    "14_candidate_validation.py",
    "16_candidate_ranker.py",
]


def run_step(script_name, step_number, total_steps, fatal=True):
    script_path = SRC_DIR / script_name
    if not script_path.exists():
        message = f"Cannot find: {script_path}"
        if fatal:
            raise FileNotFoundError(message)
        print(f"\nWARNING: {message}")
        return False

    print("\n" + "=" * 60)
    print(f"STEP {step_number}/{total_steps}: {script_name}")
    print("=" * 60)

    result = subprocess.run([sys.executable, str(script_path)], cwd=BASE_DIR)
    if result.returncode != 0:
        message = f"{script_name} failed with exit code {result.returncode}"
        if fatal:
            raise RuntimeError(message)
        print(f"\nWARNING: {message}")
        return False

    print(f"\n✓ {script_name} completed.")
    return True


def main():
    start_time = datetime.now()
    print("\n############################################")
    print("IN ROTATION DATA PIPELINE")
    print("############################################")

    for i, script in enumerate(CORE_PIPELINE, start=1):
        run_step(script, i, len(CORE_PIPELINE), fatal=True)

    print("\nCore production pipeline completed successfully.")

    candidate_results = {}
    for i, script in enumerate(CANDIDATE_PIPELINE, start=1):
        candidate_results[script] = run_step(
            script,
            i,
            len(CANDIDATE_PIPELINE),
            fatal=False,
        )

    reliability_file = PROCESSED_DIR / "consumer_trend_verdicts_reliable.csv"
    trend_count = 0
    if reliability_file.exists() and reliability_file.stat().st_size > 0:
        try:
            trend_count = len(pd.read_csv(reliability_file))
        except pd.errors.EmptyDataError:
            trend_count = 0

    end_time = datetime.now()
    status = {
        "status": "success",
        "last_successful_update": end_time.isoformat(),
        "trend_count": trend_count,
        "duration_seconds": round((end_time - start_time).total_seconds(), 2),
        "candidate_pipeline": candidate_results,
    }

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DIR / "pipeline_status.json", "w", encoding="utf-8") as file:
        json.dump(status, file, indent=2)

    print("\n" + "=" * 60)
    print("IN ROTATION UPDATE COMPLETE")
    print("=" * 60)
    print(f"\nProduction trends updated: {trend_count}")
    print("Candidate intelligence is experimental and non-blocking.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\n" + "!" * 60)
        print("PIPELINE STOPPED")
        print("!" * 60)
        print(f"\nError:\n{error}")
        sys.exit(1)
