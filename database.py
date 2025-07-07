# database.py

import sqlite3
import pandas as pd
import os

DB_FILE = "talent_data.db"
TABLE_NAME = "talent"

def init_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        conn.close()

def save_to_db(df: pd.DataFrame):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql(TABLE_NAME, conn, if_exists='replace', index=False)
    conn.close()

def load_from_db():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM {TABLE_NAME}", conn)
    conn.close()
    return df

def db_table_exists():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

init_db()
