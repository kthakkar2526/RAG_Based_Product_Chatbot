"""
Seed realistic worker notes for each machine.
These mimic actual shop floor notes written by machinists.

Usage:
    cd backend
    python3 -m scripts.seed_notes
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from rag.db import init_db, save_note, get_db_connection
from rag.vector_store import generate_embedding, load_bm25_index

# Machine name -> list of realistic worker notes
NOTES = {
    "Haas VF-2": [
        "Spindle warmup taking longer than usual on VF-2. Ran 20 min warmup program at 6000 RPM before first job. Vibration settled down after warmup. Need to keep doing this every morning especially in winter.",
        "Changed tool 12 endmill on VF-2 today. Was getting chatter on aluminum 6061 parts. Switched from 3 flute to 2 flute 1/2 inch endmill at 8000 RPM 60 IPM and chatter went away. Surface finish much better now.",
        "Coolant concentration on VF-2 was down to 4 percent. Mixed new batch to 7 percent. Also cleaned out the chip conveyor, was getting jammed with long stringy chips from the steel job last week.",
        "VF-2 threw alarm 108 overload on Y axis during heavy roughing cut in 4140 steel. Reduced depth of cut from 0.250 to 0.150 and feed from 40 IPM to 25 IPM. Ran fine after that. Need to be careful with heavy cuts on this machine.",
        "Set up new fixture on VF-2 for the bracket job order 4521. Used Mitee Bite clamps in T-slots. Indicated vise to within 0.0003. First article passed inspection all dims within tolerance.",
    ],
    "Haas VF-5": [
        "VF-5 making grinding noise from spindle area at high RPM above 8000. Runs fine below that. Told supervisor, might need spindle bearings checked soon. Using lower RPM for now on aluminum jobs.",
        "Big titanium job on VF-5 today. Running Ti-6Al-4V at 200 SFM with carbide endmill. Coolant through spindle really helps with chip evacuation. Getting good tool life about 45 minutes per insert.",
        "Probing cycle on VF-5 was off by 0.002 in Z. Re-calibrated the Renishaw probe using ring gauge. Now reading within 0.0005. Should check probe calibration weekly.",
        "Chip conveyor on VF-5 broke again, chain came off the sprocket. Maintenance fixed it but this is the third time this month. Might need new chain assembly.",
    ],
    "Haas UMC-750": [
        "UMC-750 5 axis job for aerospace bracket. Set DWOS dynamic work offset setting for each fixture position. Getting good repeatability within 0.001 across all 5 faces. Key is making sure trunnion is clean before loading.",
        "Crashed tool on UMC-750 during simultaneous 5 axis move. Tool path was too close to fixture on the B axis rotation. Added 0.5 inch extra clearance in CAM and re-posted. Always simulate 5 axis jobs before running.",
        "Thermal growth issue on UMC-750 after running for 4 hours straight. Z axis shifted about 0.0015. Started running thermal comp cycle between batches. Also letting machine warm up 30 minutes before precision work.",
        "UMC-750 trunnion table making clicking sound when rotating A axis. Cleaned debris from table surface and re-seated the fixture. Sound went away. Keep trunnion table clean between setups.",
    ],
    "Haas ST-20Y": [
        "Set up ST-20Y for shaft job today. Live tooling Y axis milling a keyway on 4340 steel shaft. Used 3/8 endmill at 3000 RPM. Key is making sure tailstock pressure is right, set to 300 PSI for this diameter.",
        "Bar feeder on ST-20Y jamming on 2 inch cold rolled bar stock. Adjusted the pusher finger tension and channel width. Also chamfered the bar ends before loading. Running smooth now.",
        "ST-20Y chuck jaw marks on finished parts. Switched from hard jaws to pie jaws with bore matched to part OD. No more jaw marks. Also reduced chuck pressure from 200 to 150 PSI since parts are thin wall.",
        "Turned down a batch of stainless 316 bushings on ST-20Y. Tool wear was bad, going through inserts every 20 parts. Switched to coated carbide CNMG insert with chipbreaker for stainless. Now getting 60 parts per insert. Use 400 SFM and 0.008 IPR feed.",
        "Coolant nozzle on ST-20Y was pointing wrong direction after last setup change. Chips were wrapping around the part. Re-aimed coolant directly at cutting zone and increased pressure. Clean cuts now no bird nesting.",
    ],
    "UR10e": [
        "Programmed UR10e for machine tending on VF-2 today. Pick from conveyor, load into vise, close vise, cycle start, wait for part done signal, open vise, unload to outfeed. Cycle time 45 seconds for load unload.",
        "UR10e gripper losing grip on oily parts coming out of the lathe. Added rubber pads to gripper fingers and increased grip force from 60 to 80 percent. Holding parts securely now even with coolant on them.",
        "Safety fence light curtain on UR10e cell triggered false alarm twice today. Cleaned the sensor lenses, there was coolant mist buildup. Also adjusted sensitivity setting. No false trips since cleaning.",
        "UR10e waypoint drifting after pallet change. Re-taught the pick and place positions using the teach pendant. Key is to set the TCP tool center point accurately for the gripper. Used the 4 point method for TCP calibration.",
        "Ran UR10e lights out for first time last night. Loaded 50 blanks on input conveyor. Came in to find 48 finished parts on output. 2 parts were rejected by the UR10e because the gripper force feedback detected they were out of spec size. System works well.",
    ],
    "Ingersoll Rand R11i": [
        "R11i compressor oil level was low on Monday morning check. Added about half a quart of Ultra Plus synthetic oil. Need to check weekly, seems to be consuming more oil lately. Might have a small leak at the separator.",
        "Air dryer on R11i not draining properly. Condensate drain valve was clogged. Cleaned the auto drain and tested manual drain. Water coming out clear now. Check drain weekly especially in humid months.",
        "R11i throwing high temperature alarm during afternoon heat. Ambient temp in compressor room was 95F. Opened the ventilation louvers more and cleaned the cooler fins with compressed air. Temp came down to normal range.",
        "Changed air filter on R11i at 2000 hours per maintenance schedule. Old filter was pretty dirty, lots of dust from the grinding area. Might need to change more frequently, every 1500 hours given our shop dust.",
    ],
    "Mitutoyo SJ-210": [
        "SJ-210 giving inconsistent Ra readings on ground surfaces. Calibrated with the precision specimen and now reading correctly. Need to calibrate at start of every shift, not just when it seems off.",
        "Used SJ-210 to verify surface finish on the aerospace bracket job. Customer spec is 32 Ra max. Getting 16-20 Ra with current endmill. Documented readings for each part in the quality log.",
        "SJ-210 stylus tip looks worn, readings trending higher than expected. Ordered replacement stylus. In the meantime comparing readings with the shop CMM surface finish probe to make sure we are still within spec.",
    ],
}


def main():
    print("=" * 60)
    print("Seeding Worker Notes")
    print("=" * 60)

    init_db()

    # Get machine IDs
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM machines;")
        machine_map = {name: mid for mid, name in cursor.fetchall()}
        cursor.close()

    print(f"Found {len(machine_map)} machines\n")

    total = 0
    for machine_name, notes in NOTES.items():
        machine_id = machine_map.get(machine_name)
        if not machine_id:
            print(f"  SKIP: Machine '{machine_name}' not found in DB")
            continue

        print(f"  {machine_name} (id={machine_id}): {len(notes)} notes")
        for note_text in notes:
            embedding = generate_embedding(note_text)
            save_note(note_text, embedding, machine_id=machine_id)
            total += 1

    print(f"\nDone! {total} notes inserted.")

    print("\nRebuilding BM25 index...")
    load_bm25_index()
    print("BM25 index rebuilt.")


if __name__ == "__main__":
    main()
