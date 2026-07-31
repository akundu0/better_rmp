"""Tests for the FastAPI endpoints using TestClient."""

import json
import os
import tempfile
from unittest import mock

import pytest
from fastapi.testclient import TestClient

# Patch DB before importing the app
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()

import backend.database as db
db.DB_PATH = _tmp_db.name

from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    """Fresh database for each test."""
    if os.path.exists(_tmp_db.name):
        os.unlink(_tmp_db.name)
    db.DB_PATH = _tmp_db.name
    db.init_db()
    yield
    if os.path.exists(_tmp_db.name):
        os.unlink(_tmp_db.name)


def _seed_school_with_professors():
    """Seed a bootstrapped school with sample professors."""
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test University", "city": "Boston", "state": "MA"})
    db.mark_school_bootstrapped("S1")
    profs = [
        {"id": "P1", "legacyId": 101, "firstName": "Alice", "lastName": "Smith",
         "department": "Computer Science", "avgRating": 4.8, "avgDifficulty": 2.0,
         "numRatings": 50, "wouldTakeAgainPercent": 95.0},
        {"id": "P2", "legacyId": 102, "firstName": "Bob", "lastName": "Jones",
         "department": "Mathematics", "avgRating": 3.2, "avgDifficulty": 4.5,
         "numRatings": 10, "wouldTakeAgainPercent": 40.0},
        {"id": "P3", "legacyId": 103, "firstName": "Carol", "lastName": "White",
         "department": "Computer Science", "avgRating": 4.0, "avgDifficulty": 3.0,
         "numRatings": 25, "wouldTakeAgainPercent": 70.0},
    ]
    db.upsert_professors_bulk(profs, "S1")


# ── GET /api/schools ──────────────────────────────────────────────────────────

def test_get_saved_schools_empty():
    resp = client.get("/api/schools")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_saved_schools_with_data():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni", "city": "Boston", "state": "MA"})
    db.mark_school_bootstrapped("S1")
    resp = client.get("/api/schools")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Test Uni"


# ── GET /api/schools/{school_id}/departments ──────────────────────────────────

def test_get_departments():
    _seed_school_with_professors()
    resp = client.get("/api/schools/S1/departments")
    assert resp.status_code == 200
    departments = resp.json()
    assert "Computer Science" in departments
    assert "Mathematics" in departments


def test_get_departments_empty():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    resp = client.get("/api/schools/S1/departments")
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /api/schools/{school_id}/tags ─────────────────────────────────────────

def test_get_tags_empty():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    resp = client.get("/api/schools/S1/tags")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_tags_with_data():
    _seed_school_with_professors()
    db.update_professor_tags_and_courses("P1", [{"tagName": "Caring", "tagCount": 5}], [])
    resp = client.get("/api/schools/S1/tags")
    assert resp.status_code == 200
    assert "Caring" in resp.json()


# ── GET /api/professors/search ────────────────────────────────────────────────

def test_search_requires_school_id():
    resp = client.get("/api/professors/search")
    assert resp.status_code == 422  # Missing required param


def test_search_rejects_non_bootstrapped_school():
    db.upsert_school({"id": "S1", "legacyId": 1, "name": "Test Uni"})
    resp = client.get("/api/professors/search?school_id=S1")
    assert resp.status_code == 400
    assert "not bootstrapped" in resp.json()["detail"].lower()


def test_search_returns_all():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    assert len(data["results"]) == 3


def test_search_by_name():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&q=Alice")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["first_name"] == "Alice"


def test_search_by_department():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&department=Computer+Science")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_search_with_min_rating():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&min_rating=4.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for prof in data["results"]:
        assert prof["avg_rating"] >= 4.0


def test_search_with_max_difficulty():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&max_difficulty=3.0")
    assert resp.status_code == 200
    data = resp.json()
    for prof in data["results"]:
        assert prof["avg_difficulty"] <= 3.0


def test_search_with_min_would_take_again():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&min_would_take_again=70")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_search_with_min_num_ratings():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&min_num_ratings=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


def test_search_combined_filters():
    _seed_school_with_professors()
    resp = client.get(
        "/api/professors/search?school_id=S1&department=Computer+Science&min_rating=4.5"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["results"][0]["first_name"] == "Alice"


def test_search_sort_by_rating_asc():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&sort_by=avg_rating&sort_order=asc")
    assert resp.status_code == 200
    ratings = [p["avg_rating"] for p in resp.json()["results"]]
    assert ratings == sorted(ratings)


def test_search_sort_by_difficulty_desc():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&sort_by=avg_difficulty&sort_order=desc")
    assert resp.status_code == 200
    diffs = [p["avg_difficulty"] for p in resp.json()["results"]]
    assert diffs == sorted(diffs, reverse=True)


def test_search_pagination():
    _seed_school_with_professors()
    resp1 = client.get("/api/professors/search?school_id=S1&limit=2&offset=0")
    resp2 = client.get("/api/professors/search?school_id=S1&limit=2&offset=2")
    data1 = resp1.json()
    data2 = resp2.json()
    assert data1["total"] == 3
    assert len(data1["results"]) == 2
    assert len(data2["results"]) == 1
    ids1 = {p["id"] for p in data1["results"]}
    ids2 = {p["id"] for p in data2["results"]}
    assert ids1.isdisjoint(ids2)


def test_search_response_shape():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&limit=1")
    data = resp.json()
    assert "results" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    prof = data["results"][0]
    assert "id" in prof
    assert "first_name" in prof
    assert "last_name" in prof
    assert "department" in prof
    assert "avg_rating" in prof
    assert "avg_difficulty" in prof
    assert "num_ratings" in prof
    assert "would_take_again_percent" in prof
    assert "tags" in prof
    assert "courses" in prof
    assert "rmp_link" in prof


def test_search_rating_validation():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&min_rating=6.0")
    assert resp.status_code == 422  # Validation error: rating > 5


def test_search_difficulty_validation():
    _seed_school_with_professors()
    resp = client.get("/api/professors/search?school_id=S1&max_difficulty=-1")
    assert resp.status_code == 422
