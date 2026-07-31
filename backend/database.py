"""
SQLite database for caching professor data locally.
Enables fast filtering without hitting the RMP API on every search.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "better_rmp.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS schools (
            id TEXT PRIMARY KEY,
            legacy_id INTEGER,
            name TEXT NOT NULL,
            city TEXT,
            state TEXT,
            bootstrapped_at TEXT
        );

        CREATE TABLE IF NOT EXISTS professors (
            id TEXT PRIMARY KEY,
            legacy_id INTEGER,
            school_id TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            department TEXT,
            avg_rating REAL,
            avg_difficulty REAL,
            num_ratings INTEGER DEFAULT 0,
            would_take_again_percent REAL,
            tags TEXT,  -- JSON array of {tagName, tagCount}
            courses TEXT,  -- JSON array of course codes from ratings
            rmp_link TEXT,
            updated_at TEXT,
            FOREIGN KEY (school_id) REFERENCES schools(id)
        );

        CREATE INDEX IF NOT EXISTS idx_professors_school ON professors(school_id);
        CREATE INDEX IF NOT EXISTS idx_professors_department ON professors(department);
        CREATE INDEX IF NOT EXISTS idx_professors_rating ON professors(avg_rating);
        CREATE INDEX IF NOT EXISTS idx_professors_difficulty ON professors(avg_difficulty);
        CREATE INDEX IF NOT EXISTS idx_professors_name ON professors(last_name, first_name);
    """)
    conn.commit()
    conn.close()


def upsert_school(school: dict):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO schools (id, legacy_id, name, city, state)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name=excluded.name, city=excluded.city, state=excluded.state
        """,
        (school["id"], school.get("legacyId"), school["name"],
         school.get("city"), school.get("state")),
    )
    conn.commit()
    conn.close()


def mark_school_bootstrapped(school_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE schools SET bootstrapped_at = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), school_id),
    )
    conn.commit()
    conn.close()


def is_school_bootstrapped(school_id: str) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT bootstrapped_at FROM schools WHERE id = ?", (school_id,)
    ).fetchone()
    conn.close()
    return row is not None and row["bootstrapped_at"] is not None


def upsert_professor(prof: dict, school_id: str):
    conn = get_connection()
    legacy_id = prof.get("legacyId")
    rmp_link = f"https://www.ratemyprofessors.com/professor/{legacy_id}" if legacy_id else None

    conn.execute(
        """
        INSERT INTO professors (id, legacy_id, school_id, first_name, last_name,
            department, avg_rating, avg_difficulty, num_ratings,
            would_take_again_percent, rmp_link, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            first_name=excluded.first_name, last_name=excluded.last_name,
            department=excluded.department, avg_rating=excluded.avg_rating,
            avg_difficulty=excluded.avg_difficulty, num_ratings=excluded.num_ratings,
            would_take_again_percent=excluded.would_take_again_percent,
            rmp_link=excluded.rmp_link, updated_at=excluded.updated_at
        """,
        (
            prof["id"], legacy_id, school_id,
            prof.get("firstName", ""), prof.get("lastName", ""),
            prof.get("department"), prof.get("avgRating"),
            prof.get("avgDifficulty"), prof.get("numRatings", 0),
            prof.get("wouldTakeAgainPercent"),
            rmp_link,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def upsert_professors_bulk(professors: list[dict], school_id: str):
    conn = get_connection()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for prof in professors:
        legacy_id = prof.get("legacyId")
        rmp_link = f"https://www.ratemyprofessors.com/professor/{legacy_id}" if legacy_id else None
        rows.append((
            prof["id"], legacy_id, school_id,
            prof.get("firstName", ""), prof.get("lastName", ""),
            prof.get("department"), prof.get("avgRating"),
            prof.get("avgDifficulty"), prof.get("numRatings", 0),
            prof.get("wouldTakeAgainPercent"),
            rmp_link, now,
        ))

    conn.executemany(
        """
        INSERT INTO professors (id, legacy_id, school_id, first_name, last_name,
            department, avg_rating, avg_difficulty, num_ratings,
            would_take_again_percent, rmp_link, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            first_name=excluded.first_name, last_name=excluded.last_name,
            department=excluded.department, avg_rating=excluded.avg_rating,
            avg_difficulty=excluded.avg_difficulty, num_ratings=excluded.num_ratings,
            would_take_again_percent=excluded.would_take_again_percent,
            rmp_link=excluded.rmp_link, updated_at=excluded.updated_at
        """,
        rows,
    )
    conn.commit()
    conn.close()


def update_professor_tags_and_courses(professor_id: str, tags: list[dict], courses: list[str]):
    conn = get_connection()
    conn.execute(
        "UPDATE professors SET tags = ?, courses = ? WHERE id = ?",
        (json.dumps(tags), json.dumps(courses), professor_id),
    )
    conn.commit()
    conn.close()


def search_professors(
    school_id: str,
    q: Optional[str] = None,
    department: Optional[str] = None,
    min_rating: Optional[float] = None,
    max_difficulty: Optional[float] = None,
    min_would_take_again: Optional[float] = None,
    min_num_ratings: Optional[int] = None,
    tag: Optional[str] = None,
    course: Optional[str] = None,
    sort_by: str = "avg_rating",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Search and filter professors. Returns (results, total_count)."""
    conn = get_connection()
    conditions = ["school_id = ?"]
    params: list = [school_id]

    if q:
        conditions.append("(first_name || ' ' || last_name LIKE ? OR last_name || ', ' || first_name LIKE ?)")
        pattern = f"%{q}%"
        params.extend([pattern, pattern])

    if department:
        conditions.append("department = ?")
        params.append(department)

    if min_rating is not None:
        conditions.append("avg_rating >= ?")
        params.append(min_rating)

    if max_difficulty is not None:
        conditions.append("avg_difficulty <= ?")
        params.append(max_difficulty)

    if min_would_take_again is not None:
        conditions.append("would_take_again_percent >= ?")
        params.append(min_would_take_again)

    if min_num_ratings is not None:
        conditions.append("num_ratings >= ?")
        params.append(min_num_ratings)

    if tag:
        conditions.append("tags LIKE ?")
        params.append(f'%"{tag}"%')

    if course:
        conditions.append("courses LIKE ?")
        params.append(f'%"{course}"%')

    where_clause = " AND ".join(conditions)

    # Validate sort_by to prevent SQL injection
    valid_sort_columns = {
        "avg_rating", "avg_difficulty", "num_ratings",
        "would_take_again_percent", "last_name", "first_name", "department",
    }
    if sort_by not in valid_sort_columns:
        sort_by = "avg_rating"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    # Count total
    count_row = conn.execute(
        f"SELECT COUNT(*) as cnt FROM professors WHERE {where_clause}", params
    ).fetchone()
    total = count_row["cnt"]

    # Fetch page
    rows = conn.execute(
        f"""
        SELECT * FROM professors
        WHERE {where_clause}
        ORDER BY {sort_by} {sort_order}
        LIMIT ? OFFSET ?
        """,
        params + [limit, offset],
    ).fetchall()

    conn.close()

    results = []
    for row in rows:
        prof = dict(row)
        # Parse JSON fields
        if prof.get("tags"):
            prof["tags"] = json.loads(prof["tags"])
        else:
            prof["tags"] = []
        if prof.get("courses"):
            prof["courses"] = json.loads(prof["courses"])
        else:
            prof["courses"] = []
        results.append(prof)

    return results, total


def get_departments(school_id: str) -> list[str]:
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT DISTINCT department FROM professors
        WHERE school_id = ? AND department IS NOT NULL
        ORDER BY department
        """,
        (school_id,),
    ).fetchall()
    conn.close()
    return [row["department"] for row in rows]


def get_all_tags(school_id: str) -> list[str]:
    """Get all unique tags used by professors at a school."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT tags FROM professors WHERE school_id = ? AND tags IS NOT NULL",
        (school_id,),
    ).fetchall()
    conn.close()

    tag_set = set()
    for row in rows:
        try:
            tags = json.loads(row["tags"])
            for t in tags:
                if isinstance(t, dict) and t.get("tagName"):
                    tag_set.add(t["tagName"])
        except (json.JSONDecodeError, TypeError):
            pass
    return sorted(tag_set)


def get_school(school_id: str) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM schools WHERE id = ?", (school_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_schools() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM schools ORDER BY name").fetchall()
    conn.close()
    return [dict(row) for row in rows]
