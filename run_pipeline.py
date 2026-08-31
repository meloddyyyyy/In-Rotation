import subprocess
import sys
import json

from pathlib import Path
from datetime import datetime

import pandas as pd


# ==================================================
# 1. Paths
# ==================================================

BASE_DIR = Path(
    __file__
).resolve().parent

SRC_DIR = (
    BASE_DIR
    / "src"
)

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
)


# ==================================================
# 2. Pipeline order
# ==================================================

PIPELINE = [

    "12_google_trends_collector.py",

    "01_search_signals.py",

    "02_trend_stage.py",

    "03_media_signal.py",

    "04_signal_integration.py",

    "5_universal_scoring.py",

    "11_consumer_verdict.py",

    "13_reliability_filter.py"

]


# ==================================================
# 3. Run one step
# ==================================================

def run_step(
    script_name,
    step_number,
    total_steps
):

    script_path = (
        SRC_DIR
        / script_name
    )


    if not script_path.exists():

        raise FileNotFoundError(
            f"Cannot find: {script_path}"
        )


    print(
        "\n"
        + "=" * 60
    )

    print(
        f"STEP {step_number}/{total_steps}"
    )

    print(
        script_name
    )

    print(
        "=" * 60
    )


    result = subprocess.run(
        [
            sys.executable,
            str(script_path)
        ],
        cwd=BASE_DIR
    )


    if result.returncode != 0:

        raise RuntimeError(
            f"{script_name} failed "
            f"with exit code "
            f"{result.returncode}"
        )


    print(
        f"\n✓ {script_name} completed."
    )


# ==================================================
# 4. Run pipeline
# ==================================================

def main():

    start_time = datetime.now()


    print(
        "\n"
        "############################################"
    )

    print(
        "TRENDPULSE DATA PIPELINE"
    )

    print(
        "############################################"
    )


    total_steps = len(
        PIPELINE
    )


    for step_number, script_name in enumerate(
        PIPELINE,
        start=1
    ):

        run_step(
            script_name,
            step_number,
            total_steps
        )


    # ==================================================
    # 5. Count monitored trends
    # ==================================================

    reliability_file = (
        PROCESSED_DIR
        / "consumer_trend_verdicts_reliable.csv"
    )


    if reliability_file.exists():

        final_df = pd.read_csv(
            reliability_file
        )

        trend_count = len(
            final_df
        )

    else:

        trend_count = 0


    # ==================================================
    # 6. Save pipeline status
    # ==================================================

    end_time = datetime.now()


    status = {

        "status":
            "success",

        "last_successful_update":
            end_time.isoformat(),

        "trend_count":
            trend_count,

        "duration_seconds":
            round(
                (
                    end_time
                    - start_time
                ).total_seconds(),
                2
            )
    }


    status_file = (
        PROCESSED_DIR
        / "pipeline_status.json"
    )


    with open(
        status_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            status,
            file,
            indent=2
        )


    print(
        "\n"
        + "=" * 60
    )

    print(
        "TRENDPULSE UPDATE COMPLETE"
    )

    print(
        "=" * 60
    )


    print(
        f"\nTrends updated: {trend_count}"
    )


    print(
        "Last updated:"
    )

    print(
        end_time.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )


    print(
        "\nDashboard data is ready."
    )


# ==================================================
# 7. Start
# ==================================================

if __name__ == "__main__":

    try:

        main()

    except Exception as error:

        print(
            "\n"
            + "!" * 60
        )

        print(
            "PIPELINE STOPPED"
        )

        print(
            "!" * 60
        )

        print(
            "\nError:"
        )

        print(
            error
        )

        sys.exit(
            1
        )