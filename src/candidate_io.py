from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DEFAULT_CANDIDATE_PATHS = [
    DATA_DIR / "processed" / "candidate_pool.csv",
    DATA_DIR / "candidate_pool.csv",
    DATA_DIR / "trend_candidates_v2.csv",
]

TREND_COLUMN_NAMES = ("trend", "candidate", "keyword", "term")
CATEGORY_COLUMN_NAMES = ("category", "type", "segment")


def _first_matching_column(df, candidates):
    normalized = {str(column).strip().lower(): column for column in df.columns}
    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]
    return None


def load_candidate_pool(candidate_file=None):
    """Load the freshest available candidate universe into a stable schema."""
    if candidate_file is not None:
        paths = [Path(candidate_file)]
    else:
        paths = DEFAULT_CANDIDATE_PATHS

    selected_path = None
    for path in paths:
        if path.exists() and path.stat().st_size > 0:
            selected_path = path
            break

    if selected_path is None:
        searched = ", ".join(str(path) for path in paths)
        raise FileNotFoundError(
            "No candidate pool found. Expected one of: " + searched
        )

    try:
        raw = pd.read_csv(selected_path)
    except pd.errors.EmptyDataError as error:
        raise RuntimeError(f"Candidate pool is empty: {selected_path}") from error

    if raw.empty:
        raise RuntimeError(f"Candidate pool contains no rows: {selected_path}")

    trend_col = _first_matching_column(raw, TREND_COLUMN_NAMES)
    if trend_col is None:
        raise ValueError(
            f"Candidate pool {selected_path} needs one of these columns: "
            f"{list(TREND_COLUMN_NAMES)}"
        )

    category_col = _first_matching_column(raw, CATEGORY_COLUMN_NAMES)

    result = pd.DataFrame()
    result["Trend"] = (
        raw[trend_col]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    if category_col is not None:
        result["Category"] = raw[category_col].fillna("Unknown").astype(str).str.strip()
    else:
        result["Category"] = "Unknown"

    result = result[
        result["Trend"].notna()
        & (result["Trend"] != "")
        & (result["Trend"] != "nan")
    ]
    result = result.drop_duplicates("Trend").reset_index(drop=True)

    if result.empty:
        raise RuntimeError(f"No usable candidates found in: {selected_path}")

    return result, selected_path
