import pandas as pd
from pathlib import Path


# ==============================
# 1. Paths
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

OUTPUT_FILE = DATA_DIR / "trend_master.csv"


# ==============================
# 2. Initial trend universe
# ==============================

trends = [

    # Footwear
    {
        "Trend_ID": "T001",
        "Trend": "ballet flats",
        "Category": "Footwear",
        "Search_Term": "ballet flats",
        "Status": "Active",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T002",
        "Trend": "kitten heels",
        "Category": "Footwear",
        "Search_Term": "kitten heels",
        "Status": "Active",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T003",
        "Trend": "mary jane shoes",
        "Category": "Footwear",
        "Search_Term": "mary jane shoes",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T004",
        "Trend": "slingback heels",
        "Category": "Footwear",
        "Search_Term": "slingback heels",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    # Apparel
    {
        "Trend_ID": "T005",
        "Trend": "capri pants",
        "Category": "Apparel",
        "Search_Term": "capri pants",
        "Status": "Active",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T006",
        "Trend": "peplum top",
        "Category": "Apparel",
        "Search_Term": "peplum top",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T007",
        "Trend": "bermuda shorts",
        "Category": "Apparel",
        "Search_Term": "bermuda shorts",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T008",
        "Trend": "bubble skirt",
        "Category": "Apparel",
        "Search_Term": "bubble skirt",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T009",
        "Trend": "lace top",
        "Category": "Apparel",
        "Search_Term": "lace top",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T010",
        "Trend": "polka dot dress",
        "Category": "Apparel",
        "Search_Term": "polka dot dress",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    # Bags
    {
        "Trend_ID": "T011",
        "Trend": "east west bag",
        "Category": "Bags",
        "Search_Term": "east west bag",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T012",
        "Trend": "clutch bag",
        "Category": "Bags",
        "Search_Term": "clutch bag",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T013",
        "Trend": "suede bag",
        "Category": "Bags",
        "Search_Term": "suede bag",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T014",
        "Trend": "bowling bag",
        "Category": "Bags",
        "Search_Term": "bowling bag",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    # Jewelry
    {
        "Trend_ID": "T015",
        "Trend": "statement jewelry",
        "Category": "Jewelry",
        "Search_Term": "statement jewelry",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T016",
        "Trend": "pendant necklace",
        "Category": "Jewelry",
        "Search_Term": "pendant necklace",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T017",
        "Trend": "charm necklace",
        "Category": "Jewelry",
        "Search_Term": "charm necklace",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T018",
        "Trend": "silver jewelry",
        "Category": "Jewelry",
        "Search_Term": "silver jewelry",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    # Color / Material
    {
        "Trend_ID": "T019",
        "Trend": "butter yellow",
        "Category": "Color",
        "Search_Term": "butter yellow fashion",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    },

    {
        "Trend_ID": "T020",
        "Trend": "metallic accessories",
        "Category": "Accessories",
        "Search_Term": "metallic accessories",
        "Status": "Watch",
        "Discovery_Source": "Manual Seed",
        "Added_Time": "2026-08-24"
    }
]


# ==============================
# 3. Create DataFrame
# ==============================

df = pd.DataFrame(trends)


# ==============================
# 4. Save
# ==============================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


print(
    "========== TREND MASTER =========="
)

print(
    df.to_string(index=False)
)


print("\nSaved:")
print(OUTPUT_FILE)