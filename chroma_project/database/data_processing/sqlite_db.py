import sqlite3
import logging
import os

logging.basicConfig(
    filename="process.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

sql_db_name = os.environ.get("DB_NAME")

class SQLiteDB:
    def __init__(self,db_name=sql_db_name):
        self.db_name = db_name
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            logging.info("Connected to SQLite database: %s", self.db_name)
        except sqlite3.Error as e:
            logging.error("Error connecting to SQLite database: %s", e)
            raise

    def create_tables(self):
        """Create tables for different chunk sizes."""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks_512 (
                    id TEXT PRIMARY KEY,
                    document TEXT,
                    ori_doc_title TEXT,
                    paragraph INTEGER,
                    chunk_size INTEGER,
                    chunk_level INTEGER
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks_256 (
                    id TEXT PRIMARY KEY,
                    document TEXT,
                    ori_doc_title TEXT,
                    paragraph INTEGER,
                    chunk_size INTEGER,
                    chunk_level INTEGER
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS chunks_128 (
                    id TEXT PRIMARY KEY,
                    document TEXT,
                    ori_doc_title TEXT,
                    paragraph INTEGER,
                    chunk_size INTEGER,
                    chunk_level INTEGER
                )
            """)
            self.conn.commit()
            logging.info("Created tables in SQLite database")
        except sqlite3.Error as e:
            logging.error("Error creating tables: %s", e)
            raise

    def insert_chunk(self, table_name, chunk_id, document, ori_doc_title, paragraph, chunk_size, chunk_level):
        """Insert a chunk into the specified table."""
        try:
            self.cursor.execute(f"""
                INSERT INTO {table_name} (id, document, ori_doc_title, paragraph, chunk_size, chunk_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (chunk_id, document, ori_doc_title, paragraph, chunk_size, chunk_level))
            self.conn.commit()
            logging.info("Inserted chunk into table: %s with id: %s", table_name, chunk_id)
        except sqlite3.Error as e:
            logging.error("Error inserting chunk into table %s: %s", table_name, e)
            raise

    def close(self):
        """Close the database connection."""
        try:
            if self.conn:
                self.conn.close()
                logging.info("Closed SQLite database connection")
        except sqlite3.Error as e:
            logging.error("Error closing SQLite database connection: %s", e)
            raise
