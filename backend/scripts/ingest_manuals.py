"""
Manual ingestion script.

Pre-configured with machines and their manual mappings.
Place PDF files in backend/manuals/ and run this script:

    cd backend
    python -m scripts.ingest_manuals

Or with specific options:
    python -m scripts.ingest_manuals --no-images    # Skip Gemini image descriptions
    python -m scripts.ingest_manuals --manual "Haas Mill Operator's Manual (NGC)"  # Ingest one manual only
"""

import sys
import os
import argparse
from pathlib import Path

# Add backend to path so we can import rag modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from rag.db import init_db, create_machine, create_manual, link_machine_manual, get_db_connection
from rag.pdf_ingestion import process_pdf

# ============================================================
# CONFIGURATION: Machines and their manual mappings
# ============================================================

MACHINES = [
    {"name": "Haas VF-2", "description": "Vertical CNC mill (workhorse, general purpose)"},
    {"name": "Haas VF-5", "description": "Vertical CNC mill (bigger envelope / heavier work)"},
    {"name": "Haas UMC-750", "description": "5-axis CNC mill (high-mix complexity)"},
    {"name": "Haas ST-20Y", "description": "CNC turning center (shafts, bushings)"},
    {"name": "UR10e", "description": "Universal Robots UR10e collaborative robot"},
    {"name": "Ingersoll Rand R11i", "description": "Rotary screw compressor (shop air)"},
    {"name": "Mitutoyo SJ-210", "description": "Portable surface roughness tester"},
]

MANUALS = [
    {
        "title": "Haas Mill Operator's Manual (NGC)",
        "type": "operator",
        "file": "manuals/haas-mill-ngc-operator-2024.pdf",
        "source_url": "https://www.haascnc.com/content/dam/haascnc/en/service/manual/operator/english---mill-ngc---operator%27s-manual---2024.pdf",
        "machines": ["Haas VF-2", "Haas VF-5", "Haas UMC-750"],
    },
    {
        "title": "Haas NGC Troubleshooting Manual",
        "type": "troubleshooting",
        "file": "manuals/haas-ngc-troubleshooting.pdf",
        "source_url": "https://www.manualslib.com/manual/1951551/Haas-Ngc.html",
        "machines": ["Haas VF-2", "Haas VF-5", "Haas UMC-750", "Haas ST-20Y"],
    },
    {
        "title": "UMC-Series Operator's Manual Supplement",
        "type": "supplement",
        "file": "manuals/haas-umc-supplement-2018.pdf",
        "source_url": "https://www.haascnc.com/content/dam/haascnc/en/service/manual/supplement/english---umc-operator%27s-manual-supplement---2018.pdf",
        "machines": ["Haas UMC-750"],
    },
    {
        "title": "Haas Lathe Operator's Manual (NGC)",
        "type": "operator",
        "file": "manuals/haas-lathe-ngc-operator-2024.pdf",
        "source_url": "https://www.haascnc.com/content/dam/haascnc/en/service/manual/operator/english---lathe-ngc---operator%27s-manual---2024.pdf",
        "machines": ["Haas ST-20Y"],
    },
    {
        "title": "UR10e User Manual",
        "type": "operator",
        "file": "manuals/ur10e-user-manual.pdf",
        "source_url": "https://s3-eu-west-1.amazonaws.com/ur-support-site/41237/UR10e_User_Manual_en_Global.pdf",
        "machines": ["UR10e"],
    },
    {
        "title": "Universal Robots e-Series Service Manual",
        "type": "troubleshooting",
        "file": "manuals/ur-eseries-service-manual.pdf",
        "source_url": "https://www.universal-robots.com/manuals/EN/PDF/SW5_19/service-manual_e-series/e-Series_Service_Manual_en.pdf",
        "machines": ["UR10e"],
    },
    {
        "title": "Ingersoll Rand R4-11i Maintenance Information",
        "type": "troubleshooting",
        "file": "manuals/ingersoll-rand-r4-11i-maintenance.pdf",
        "source_url": "https://www.portlandcompressor.com/docs/compressors/Ingersoll-Rand-R4-11i-Product-Maintenance-Information.pdf",
        "machines": ["Ingersoll Rand R11i"],
    },
    {
        "title": "Mitutoyo Surftest SJ-210 Product Document",
        "type": "operator",
        "file": "manuals/mitutoyo-sj210.pdf",
        "source_url": "https://www.mitutoyo.com/webfoo/wp-content/uploads/Surftest_SJ210.pdf",
        "machines": ["Mitutoyo SJ-210"],
    },
]


def main():
    parser = argparse.ArgumentParser(description="Ingest machine manuals into the RAG database")
    parser.add_argument("--no-images", action="store_true", help="Skip Gemini image descriptions")
    parser.add_argument("--manual", type=str, help="Only ingest a specific manual by title")
    args = parser.parse_args()

    print("=" * 60)
    print("Manual Ingestion Pipeline")
    print("=" * 60)

    # Initialize DB tables
    print("\n1. Initializing database tables...")
    init_db()

    # Create machines
    print("\n2. Creating machines...")
    machine_ids = {}
    for machine in MACHINES:
        mid = create_machine(machine["name"], machine["description"])
        machine_ids[machine["name"]] = mid
        print(f"   {machine['name']} -> id={mid}")

    # Filter manuals if --manual flag used
    manuals_to_process = MANUALS
    if args.manual:
        manuals_to_process = [m for m in MANUALS if m["title"] == args.manual]
        if not manuals_to_process:
            print(f"\nError: Manual '{args.manual}' not found in configuration.")
            print("Available manuals:")
            for m in MANUALS:
                print(f"  - {m['title']}")
            sys.exit(1)

    # Process each manual
    print(f"\n3. Processing {len(manuals_to_process)} manual(s)...")
    total_chunks = 0

    for manual_config in manuals_to_process:
        pdf_path = backend_dir / manual_config["file"]

        print(f"\n--- {manual_config['title']} ---")

        if not pdf_path.exists():
            print(f"   SKIPPED: PDF not found at {pdf_path}")
            print(f"   Download from: {manual_config.get('source_url', 'N/A')}")
            continue

        # Create manual record
        manual_id = create_manual(
            title=manual_config["title"],
            manual_type=manual_config["type"],
            source_url=manual_config.get("source_url"),
        )
        print(f"   Manual record id={manual_id}")

        # Link to machines
        for machine_name in manual_config["machines"]:
            if machine_name in machine_ids:
                link_machine_manual(machine_ids[machine_name], manual_id)
                print(f"   Linked to: {machine_name}")

        # Process the PDF
        chunks = process_pdf(
            pdf_path=str(pdf_path),
            manual_id=manual_id,
            describe_images=not args.no_images,
        )
        total_chunks += chunks

    print(f"\n{'=' * 60}")
    print(f"Done! Total chunks created: {total_chunks}")
    print(f"{'=' * 60}")

    # Rebuild BM25 index
    print("\n4. Rebuilding BM25 index...")
    from rag.vector_store import load_bm25_index
    load_bm25_index()
    print("BM25 index rebuilt.")


if __name__ == "__main__":
    main()
