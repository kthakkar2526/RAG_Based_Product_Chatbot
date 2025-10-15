import pandas as pd
from rag.db import save_note_to_db
from rag.vector_store import add_note_to_chroma

# Path to your exported Excel file
EXCEL_PATH = "data/notes.xlsx"

def import_notes():
    df = pd.read_excel(EXCEL_PATH)

    for _, row in df.iterrows():
        note_id = int(row["note_id"])
        text = str(row["text"]).strip()

        if not text:
            continue

        print(f"📝 Importing note {note_id}...")

        # Save to MySQL
        db_id = save_note_to_db(text)

        # Save to Chroma
        add_note_to_chroma(db_id, text)

    print("All notes imported successfully!")

if __name__ == "__main__":
    import_notes()