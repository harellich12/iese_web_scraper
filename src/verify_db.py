import sqlite3
import os

DB_PATH = "data/faculty.db"

def check_db():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Professors ---")
    cursor.execute("SELECT name, title, department FROM professors LIMIT 10")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
    
    print("\n--- Industries ---")
    cursor.execute("SELECT name FROM industries")
    rows = cursor.fetchall()
    for row in rows:
        print(row)

    print("\n--- Professor Industries ---")
    cursor.execute("""
        SELECT p.name, i.name 
        FROM professors p 
        JOIN professor_industries pi ON p.id = pi.professor_id 
        JOIN industries i ON i.id = pi.industry_id
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"{row[0]} -> {row[1]}")

    conn.close()

if __name__ == "__main__":
    check_db()
