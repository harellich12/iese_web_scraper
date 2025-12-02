import sqlite3
import os

DB_PATH = "data/faculty.db"

def review_industries():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("--- Professor Industries Review ---")
    cursor.execute("""
        SELECT p.name, i.name 
        FROM professors p 
        JOIN professor_industries pi ON p.id = pi.professor_id 
        JOIN industries i ON i.id = pi.industry_id
        ORDER BY p.name
    """)
    rows = cursor.fetchall()
    
    prof_industries = {}
    for prof, ind in rows:
        if prof not in prof_industries:
            prof_industries[prof] = []
        prof_industries[prof].append(ind)
        
    for prof, inds in prof_industries.items():
        print(f"{prof}: {', '.join(inds)}")

    print("\n--- Industry Distribution ---")
    cursor.execute("""
        SELECT i.name, COUNT(pi.professor_id) as count
        FROM industries i
        JOIN professor_industries pi ON i.id = pi.industry_id
        GROUP BY i.name
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    for ind, count in rows:
        print(f"{ind}: {count}")

    conn.close()

if __name__ == "__main__":
    review_industries()
