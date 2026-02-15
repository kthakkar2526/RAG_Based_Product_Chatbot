from datetime import datetime
import os
import numpy as np
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from contextlib import contextmanager


DB_CONFIG = {
    'dbname': os.getenv('POSTGRES_DB', 'notes_db'),
    'user': os.getenv('POSTGRES_USER', 'app_user'),
    'password': os.getenv('POSTGRES_PASSWORD'),
}

CLOUD_SQL_CONNECTION_NAME = os.getenv('CLOUD_SQL_CONNECTION_NAME')
if CLOUD_SQL_CONNECTION_NAME:
    DB_CONFIG['host'] = f'/cloudsql/{CLOUD_SQL_CONNECTION_NAME}'
else:
    DB_CONFIG['host'] = os.getenv('POSTGRES_HOST', 'localhost')
    DB_CONFIG['port'] = int(os.getenv('POSTGRES_PORT', 5433))

_connection_pool = None

def get_connection_pool():
    """Get or create a connection pool."""
    global _connection_pool
    if _connection_pool is None:
        try:
            _connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                **DB_CONFIG
            )
            print("PostgreSQL connection pool created")
        except Exception as e:
            print(f"Error creating connection pool: {e}")
            raise
    return _connection_pool

_vector_registered = False

@contextmanager
def get_db_connection():
    """Context manager to get a database connection from the pool."""
    global _vector_registered
    pool = get_connection_pool()
    connection = None
    try:
        connection = pool.getconn()
        if _vector_registered:
            register_vector(connection)
        yield connection
        connection.commit()
    except Exception as e:
        if connection:
            connection.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        if connection:
            pool.putconn(connection)


def init_db():
    """Create all tables if they don't exist. Must be called before other DB operations."""
    global _vector_registered
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.commit()

    # Now that vector extension exists, enable registration for future connections
    _vector_registered = True

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machines (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manuals (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                manual_type VARCHAR(50),
                source_url TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_manuals (
                machine_id INT REFERENCES machines(id),
                manual_id INT REFERENCES manuals(id),
                PRIMARY KEY (machine_id, manual_id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                text TEXT NOT NULL,
                embedding vector(384),
                machine_id INT REFERENCES machines(id),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manual_chunks (
                id SERIAL PRIMARY KEY,
                manual_id INT REFERENCES manuals(id),
                chunk_text TEXT NOT NULL,
                page_number INT,
                section_title VARCHAR(255),
                chunk_type VARCHAR(50) DEFAULT 'text',
                embedding vector(384),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        # Add machine_id to notes if it doesn't exist (for existing DBs)
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'notes' AND column_name = 'machine_id'
                ) THEN
                    ALTER TABLE notes ADD COLUMN machine_id INT REFERENCES machines(id);
                END IF;
            END $$;
        """)

        conn.commit()
        cursor.close()
        print("Database tables initialized")


# --- Machine operations ---

def get_machines():
    """Retrieve all machines for dropdown."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, description FROM machines ORDER BY name;")
        machines = cursor.fetchall()
        cursor.close()
        return machines


def create_machine(name: str, description: str = None):
    """Create a machine, return its id. If it exists, return existing id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO machines (name, description) VALUES (%s, %s)
               ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
               RETURNING id;""",
            (name, description)
        )
        machine_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return machine_id


# --- Manual operations ---

def create_manual(title: str, manual_type: str = None, source_url: str = None):
    """Create a manual record, return its id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO manuals (title, manual_type, source_url)
               VALUES (%s, %s, %s) RETURNING id;""",
            (title, manual_type, source_url)
        )
        manual_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return manual_id


def link_machine_manual(machine_id: int, manual_id: int):
    """Link a machine to a manual (many-to-many)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO machine_manuals (machine_id, manual_id)
               VALUES (%s, %s) ON CONFLICT DO NOTHING;""",
            (machine_id, manual_id)
        )
        conn.commit()
        cursor.close()


def save_manual_chunk(manual_id: int, chunk_text: str, embedding: list,
                      page_number: int = None, section_title: str = None,
                      chunk_type: str = 'text'):
    """Save a manual chunk with its embedding."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        embedding_array = np.array(embedding)
        cursor.execute(
            """INSERT INTO manual_chunks
               (manual_id, chunk_text, page_number, section_title, chunk_type, embedding)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;""",
            (manual_id, chunk_text, page_number, section_title, chunk_type, embedding_array)
        )
        chunk_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return chunk_id


def delete_chunks_by_manual(manual_id: int):
    """Delete all chunks for a manual (for re-ingestion)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM manual_chunks WHERE manual_id = %s;", (manual_id,))
        conn.commit()
        cursor.close()


# --- Note operations ---

def save_note(text: str, embedding: list, machine_id: int = None) -> int:
    """Save a note and its embedding to the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        embedding_array = np.array(embedding)
        cursor.execute(
            """INSERT INTO notes (text, embedding, machine_id)
               VALUES (%s, %s, %s) RETURNING id;""",
            (text, embedding_array, machine_id)
        )
        note_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        print(f"Note saved with ID: {note_id}")
        return note_id


def get_all_notes():
    """Retrieve all notes from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, text, created_at FROM notes ORDER BY created_at DESC;")
        notes = cursor.fetchall()
        cursor.close()
        return notes


def search_similar_notes(query_embedding: list, top_k: int = 5, machine_id: int = None):
    """Find similar notes. If machine_id given, filter to that machine + unassigned notes."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        embedding_array = np.array(query_embedding)

        if machine_id is not None:
            query = """
            SELECT id, text, created_at,
                   (1 - (embedding <=> %s)) AS similarity
            FROM notes
            WHERE embedding IS NOT NULL
              AND (machine_id = %s OR machine_id IS NULL)
            ORDER BY embedding <=> %s
            LIMIT %s;
            """
            cursor.execute(query, (embedding_array, machine_id, embedding_array, top_k))
        else:
            query = """
            SELECT id, text, created_at,
                   (1 - (embedding <=> %s)) AS similarity
            FROM notes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT %s;
            """
            cursor.execute(query, (embedding_array, embedding_array, top_k))

        results = cursor.fetchall()
        cursor.close()
        return results


def search_similar_chunks(query_embedding: list, top_k: int = 5, machine_id: int = None):
    """Find similar manual chunks. If machine_id given, filter to that machine's manuals."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        embedding_array = np.array(query_embedding)

        if machine_id is not None:
            query = """
            SELECT mc.id, mc.chunk_text, mc.page_number, mc.section_title,
                   mc.chunk_type, m.title AS manual_title, m.manual_type,
                   (1 - (mc.embedding <=> %s)) AS similarity
            FROM manual_chunks mc
            JOIN manuals m ON mc.manual_id = m.id
            JOIN machine_manuals mm ON m.id = mm.manual_id
            WHERE mc.embedding IS NOT NULL
              AND mm.machine_id = %s
            ORDER BY mc.embedding <=> %s
            LIMIT %s;
            """
            cursor.execute(query, (embedding_array, machine_id, embedding_array, top_k))
        else:
            query = """
            SELECT mc.id, mc.chunk_text, mc.page_number, mc.section_title,
                   mc.chunk_type, m.title AS manual_title, m.manual_type,
                   (1 - (mc.embedding <=> %s)) AS similarity
            FROM manual_chunks mc
            JOIN manuals m ON mc.manual_id = m.id
            WHERE mc.embedding IS NOT NULL
            ORDER BY mc.embedding <=> %s
            LIMIT %s;
            """
            cursor.execute(query, (embedding_array, embedding_array, top_k))

        results = cursor.fetchall()
        cursor.close()
        return results


def get_all_notes_for_bm25(machine_id: int = None):
    """Retrieve notes for BM25 indexing, optionally filtered by machine."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if machine_id is not None:
            cursor.execute(
                "SELECT id, text, created_at FROM notes WHERE machine_id = %s OR machine_id IS NULL ORDER BY id;",
                (machine_id,)
            )
        else:
            cursor.execute("SELECT id, text, created_at FROM notes ORDER BY id;")
        notes = cursor.fetchall()
        cursor.close()
        return notes


def get_all_chunks_for_bm25(machine_id: int = None):
    """Retrieve manual chunks for BM25 indexing, optionally filtered by machine."""
    with get_db_connection() as conn:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if machine_id is not None:
            query = """
            SELECT mc.id, mc.chunk_text, mc.page_number, mc.section_title,
                   mc.chunk_type, m.title AS manual_title, m.manual_type
            FROM manual_chunks mc
            JOIN manuals m ON mc.manual_id = m.id
            JOIN machine_manuals mm ON m.id = mm.manual_id
            WHERE mm.machine_id = %s
            ORDER BY mc.id;
            """
            cursor.execute(query, (machine_id,))
        else:
            query = """
            SELECT mc.id, mc.chunk_text, mc.page_number, mc.section_title,
                   mc.chunk_type, m.title AS manual_title, m.manual_type
            FROM manual_chunks mc
            JOIN manuals m ON mc.manual_id = m.id
            ORDER BY mc.id;
            """
            cursor.execute(query)
        chunks = cursor.fetchall()
        cursor.close()
        return chunks