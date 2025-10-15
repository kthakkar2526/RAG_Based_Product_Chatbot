import mysql.connector
from datetime import datetime

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="notes_db"
    )

def save_note_to_db(note_text):
    conn = get_connection()
    cursor = conn.cursor()

    query = "INSERT INTO notes (text, created_at) VALUES (%s, %s)"
    cursor.execute(query, (note_text, datetime.now()))

    conn.commit()
    note_id = cursor.lastrowid
    cursor.close()
    conn.close()

    return note_id