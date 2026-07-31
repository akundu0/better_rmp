"""Tests for the database layer."""

import json
import os
import tempfile
from unittest import mock

import pytest

# Patch DB_PATH before importing database module
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()

with mock.patch.dict(os.environ, {}):
    import backend.database as db
    db.DB_PATH = _tmp_db.name


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh database for each test."""
    # Remove old DB and reinitialize
    if os.path.exists(_tmp_db.name):
        os.unlink(_tmp_db.name)
    db.DB_PATH = _tmp_db.name
    db.init_db()
    yield
    if os.path.exists(_tmp_db.name):
        os.unlink(_tmp_db.name)


# ── School operations ─────────────────────────────────────────────────────────

def test_upsert_and_get_school():
    school = {"id": "S1", "legacyId": 100, "name": "Test University", "city": "Boston", "state": "MA"}
    db.upsert_school(school)

    result = db.get_school("S1")
    assert result is not None
    assert result["name"] == "Test University"
    assert result["city"] == "Boston"
    assert result["state"] == "MA"


def test_get_school_not_found():
    result = db.get_school("nonexistent")
    assert result is None


def test_is_school_bootstrapped_false():
    school = {"id": "S1", "legacyId": 100, "name": "Test Uni"}
    db.upsert_school(school)
    assert db.is_school_bootstrapped("S1") is False


def test_mark_school_bootstrapped():
    school = {"id": "S1", "legacyId": 100, "name": "Test Uni"}
    db.upsert_school(school)
    db.mark_school_bootstrapped("S1")
    assert db.is_school_bootstrapped("S1") is True


def test_get_all_schools():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Alpha Uni"})
    db.upsert_school({"id": "S2", "legacyId": 2, "name": "Beta Uni"})
    schools = db.get_all_schools()
    assert len(schools) == 2
    assert schools[0]["name"] == "Alpha Uni"
    assert schools[1]["name"] == "Beta Uni"


# ── Professor operations ──────────────────────────────────────────────────────

SAMPLE_PROF = {
    "id": "P1",
    "legacyId": 12345,
    "firstName": "John",
    "lastName": "Doe",
    "department": "Computer Science",
    "avgRating": 4.5,
    "avgDifficulty": 2.3,
    "numRatings": 42,
    "wouldTakeAgainPercent": 92.0,
}


def _setup_school_and_prof():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    db.mark_school_bootstrapped("S1")
    db.upsert_professor(SAMPLE_PROF, "S1")


def test_upsert_professor():
    _setup_school_and_prof()
    results, total = db.search_professors("S1")
    assert total == 1
    assert results[0]["first_name"] == "John"
    assert results[0]["last_name"] == "Doe"
    assert results[0]["rmp_link"] == "https://www.ratemyprofessors.com/professor/12345"


def test_upsert_professors_bulk():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    db.mark_school_bootstrapped("S1")
    profs = [
        {**SAMPLE_PROF, "id": f"P{i}", "legacyId": i, "firstName": f"Prof{i}"}
        for i in range(10)
    ]
    db.upsert_professors_bulk(profs, "S1")
    results, total = db.search_professors("S1")
    assert total == 10


def test_upsert_professor_updates_on_conflict():
    _setup_school_and_prof()
    updated = {**SAMPLE_PROF, "avgRating": 3.0}
    db.upsert_professor(updated, "S1")
    results, _ = db.search_professors("S1")
    assert len(results) == 1
    assert results[0]["avg_rating"] == 3.0


# ── Search & filter ───────────────────────────────────────────────────────────

def _setup_multiple_profs():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    db.mark_school_bootstrapped("S1")
    profs = [
        {"id": "P1", "legacyId": 1, "firstName": "Alice", "lastName": "Smith",
         "department": "Computer Science", "avgRating": 4.8, "avgDifficulty": 2.0,
         "numRatings": 50, "wouldTakeAgainPercent": 95.0},
        {"id": "P2", "legacyId": 2, "firstName": "Bob", "lastName": "Jones",
         "department": "Mathematics", "avgRating": 3.2, "avgDifficulty": 4.5,
         "numRatings": 10, "wouldTakeAgainPercent": 40.0},
        {"id": "P3", "legacyId": 3, "firstName": "Carol", "lastName": "White",
         "department": "Computer Science", "avgRating": 4.0, "avgDifficulty": 3.0,
         "numRatings": 25, "wouldTakeAgainPercent": 70.0},
        {"id": "P4", "legacyId": 4, "firstName": "Dave", "lastName": "Brown",
         "department": "Physics", "avgRating": 2.5, "avgDifficulty": 4.8,
         "numRatings": 5, "wouldTakeAgainPercent": 20.0},
    ]
    db.upsert_professors_bulk(profs, "S1")


def test_search_by_name():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", q="Alice")
    assert total == 1
    assert results[0]["first_name"] == "Alice"


def test_search_by_department():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", department="Computer Science")
    assert total == 2


def test_filter_min_rating():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", min_rating=4.0)
    assert total == 2
    assert all(r["avg_rating"] >= 4.0 for r in results)


def test_filter_max_difficulty():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", max_difficulty=3.0)
    assert total == 2
    assert all(r["avg_difficulty"] <= 3.0 for r in results)


def test_filter_min_would_take_again():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", min_would_take_again=70.0)
    assert total == 2


def test_filter_min_num_ratings():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", min_num_ratings=20)
    assert total == 2


def test_combined_filters():
    _setup_multiple_profs()
    results, total = db.search_professors(
        "S1", department="Computer Science", min_rating=4.5
    )
    assert total == 1
    assert results[0]["first_name"] == "Alice"


def test_sort_by_rating_desc():
    _setup_multiple_profs()
    results, _ = db.search_professors("S1", sort_by="avg_rating", sort_order="desc")
    ratings = [r["avg_rating"] for r in results]
    assert ratings == sorted(ratings, reverse=True)


def test_sort_by_rating_asc():
    _setup_multiple_profs()
    results, _ = db.search_professors("S1", sort_by="avg_rating", sort_order="asc")
    ratings = [r["avg_rating"] for r in results]
    assert ratings == sorted(ratings)


def test_sort_by_difficulty():
    _setup_multiple_profs()
    results, _ = db.search_professors("S1", sort_by="avg_difficulty", sort_order="desc")
    diffs = [r["avg_difficulty"] for r in results]
    assert diffs == sorted(diffs, reverse=True)


def test_pagination():
    _setup_multiple_profs()
    results, total = db.search_professors("S1", limit=2, offset=0)
    assert total == 4
    assert len(results) == 2

    results2, total2 = db.search_professors("S1", limit=2, offset=2)
    assert total2 == 4
    assert len(results2) == 2

    # Pages should have different professors
    ids1 = {r["id"] for r in results}
    ids2 = {r["id"] for r in results2}
    assert ids1.isdisjoint(ids2)


def test_invalid_sort_column_defaults_to_rating():
    _setup_multiple_profs()
    # Should not raise — falls back to avg_rating
    results, _ = db.search_professors("S1", sort_by="DROP TABLE;--")
    assert len(results) == 4


# ── Tags & courses ────────────────────────────────────────────────────────────

def test_update_and_search_tags():
    _setup_school_and_prof()
    tags = [{"tagName": "Amazing lectures", "tagCount": 10}, {"tagName": "Tough grader", "tagCount": 5}]
    db.update_professor_tags_and_courses("P1", tags, ["CS101", "CS201"])

    results, _ = db.search_professors("S1", tag="Amazing lectures")
    assert len(results) == 1

    results, _ = db.search_professors("S1", tag="Nonexistent")
    assert len(results) == 0


def test_update_and_search_courses():
    _setup_school_and_prof()
    db.update_professor_tags_and_courses("P1", [], ["CS101", "CS201"])

    results, _ = db.search_professors("S1", course="CS101")
    assert len(results) == 1


def test_get_departments():
    _setup_multiple_profs()
    departments = db.get_departments("S1")
    assert "Computer Science" in departments
    assert "Mathematics" in departments
    assert "Physics" in departments


def test_get_all_tags():
    _setup_school_and_prof()
    tags = [{"tagName": "Caring", "tagCount": 3}, {"tagName": "Tough", "tagCount": 2}]
    db.update_professor_tags_and_courses("P1", tags, [])
    all_tags = db.get_all_tags("S1")
    assert "Caring" in all_tags
    assert "Tough" in all_tags


def test_tags_parsed_in_search_results():
    _setup_school_and_prof()
    tags = [{"tagName": "Caring", "tagCount": 3}]
    db.update_professor_tags_and_courses("P1", tags, ["CS101"])

    results, _ = db.search_professors("S1")
    prof = results[0]
    assert isinstance(prof["tags"], list)
    assert prof["tags"][0]["tagName"] == "Caring"
    assert isinstance(prof["courses"], list)
    assert "CS101" in prof["courses"]
