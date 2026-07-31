"""
Better RMP — FastAPI backend.
Provides search/filter endpoints over cached RMP professor data.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import database as db
from . import rmp_client
from .rmp_client import RMPError, RMPConnectionError, RMPGraphQLError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("better_rmp.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Better RMP API")
    db.init_db()
    yield
    logger.info("Shutting down Better RMP API")


app = FastAPI(
    title="Better RMP API",
    description="Advanced search and filtering for Rate My Professors",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chrome extension needs this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ────────────────────────────────────────────────

@app.exception_handler(RMPConnectionError)
async def rmp_connection_error_handler(request: Request, exc: RMPConnectionError):
    logger.error("RMP connection error: %s", str(exc))
    return JSONResponse(
        status_code=502,
        content={"detail": "Rate My Professors is currently unreachable. Please try again later."},
    )


@app.exception_handler(RMPGraphQLError)
async def rmp_graphql_error_handler(request: Request, exc: RMPGraphQLError):
    logger.error("RMP GraphQL error: %s", str(exc))
    return JSONResponse(
        status_code=502,
        content={"detail": "Rate My Professors returned an unexpected error."},
    )


@app.exception_handler(RMPError)
async def rmp_error_handler(request: Request, exc: RMPError):
    logger.error("RMP error: %s", str(exc))
    return JSONResponse(
        status_code=502,
        content={"detail": f"Rate My Professors error: {str(exc)}"},
    )


# ── Pydantic models ──────────────────────────────────────────────────────────

class SchoolResult(BaseModel):
    id: str
    legacy_id: Optional[int] = None
    name: str
    city: Optional[str] = None
    state: Optional[str] = None


class ProfessorResult(BaseModel):
    id: str
    legacy_id: Optional[int] = None
    school_id: str
    first_name: str
    last_name: str
    department: Optional[str] = None
    avg_rating: Optional[float] = None
    avg_difficulty: Optional[float] = None
    num_ratings: int = 0
    would_take_again_percent: Optional[float] = None
    tags: list = []
    courses: list = []
    rmp_link: Optional[str] = None


class SearchResponse(BaseModel):
    results: list[ProfessorResult]
    total: int
    limit: int
    offset: int


class BootstrapStatus(BaseModel):
    school_id: str
    school_name: str
    status: str
    professor_count: int = 0


class RatingResult(BaseModel):
    id: Optional[str] = None
    legacy_id: Optional[int] = None
    course: Optional[str] = None
    comment: Optional[str] = None
    clarity_rating: Optional[float] = None
    difficulty_rating: Optional[float] = None
    helpful_rating: Optional[float] = None
    date: Optional[str] = None
    grade: Optional[str] = None
    is_for_credit: Optional[bool] = None
    is_online: Optional[bool] = None
    attendance_mandatory: Optional[str] = None
    rating_tags: Optional[str] = None
    would_take_again: Optional[int] = None
    thumbs_up: int = 0
    thumbs_down: int = 0


class ProfessorDetail(BaseModel):
    id: str
    legacy_id: Optional[int] = None
    first_name: str
    last_name: str
    department: Optional[str] = None
    avg_rating: Optional[float] = None
    avg_difficulty: Optional[float] = None
    num_ratings: int = 0
    would_take_again_percent: Optional[float] = None
    tags: list = []
    rmp_link: Optional[str] = None
    school_name: Optional[str] = None
    ratings: list[RatingResult] = []


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/schools/search", response_model=list[SchoolResult])
async def search_schools(q: str = Query(..., min_length=2)):
    """Search for schools by name on RMP."""
    schools = await rmp_client.search_schools(q)
    results = []
    for s in schools:
        results.append(SchoolResult(
            id=s["id"],
            legacy_id=s.get("legacyId"),
            name=s["name"],
            city=s.get("city"),
            state=s.get("state"),
        ))
    return results


@app.post("/api/schools/{school_id}/bootstrap", response_model=BootstrapStatus)
async def bootstrap_school(school_id: str):
    """Fetch all professors for a school from RMP and cache them locally.
    This may take a while for large schools.
    """
    # First, check if already bootstrapped
    if db.is_school_bootstrapped(school_id):
        school = db.get_school(school_id)
        profs, total = db.search_professors(school_id, limit=0)
        return BootstrapStatus(
            school_id=school_id,
            school_name=school["name"] if school else "Unknown",
            status="already_bootstrapped",
            professor_count=total,
        )

    # Fetch all professors from RMP
    try:
        professors = await rmp_client.get_all_professors_at_school(school_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from RMP: {str(e)}")

    if not professors:
        raise HTTPException(status_code=404, detail="No professors found for this school")

    # Save school info from first professor's school data
    first_prof = professors[0]
    school_data = first_prof.get("school", {})
    db.upsert_school({
        "id": school_id,
        "legacyId": school_data.get("legacyId"),
        "name": school_data.get("name", "Unknown"),
    })

    # Bulk insert professors
    db.upsert_professors_bulk(professors, school_id)
    db.mark_school_bootstrapped(school_id)

    return BootstrapStatus(
        school_id=school_id,
        school_name=school_data.get("name", "Unknown"),
        status="bootstrapped",
        professor_count=len(professors),
    )


@app.get("/api/schools/{school_id}/departments", response_model=list[str])
async def get_departments(school_id: str):
    """Get all unique departments at a school."""
    return db.get_departments(school_id)


@app.get("/api/schools/{school_id}/tags", response_model=list[str])
async def get_tags(school_id: str):
    """Get all unique professor tags at a school."""
    return db.get_all_tags(school_id)


@app.get("/api/schools", response_model=list[SchoolResult])
async def get_saved_schools():
    """Get all schools that have been bootstrapped."""
    schools = db.get_all_schools()
    return [
        SchoolResult(
            id=s["id"],
            legacy_id=s.get("legacy_id"),
            name=s["name"],
            city=s.get("city"),
            state=s.get("state"),
        )
        for s in schools
        if s.get("bootstrapped_at")
    ]


@app.get("/api/professors/search", response_model=SearchResponse)
async def search_professors(
    school_id: str = Query(...),
    q: Optional[str] = Query(None, description="Name search"),
    department: Optional[str] = Query(None),
    min_rating: Optional[float] = Query(None, ge=0, le=5),
    max_difficulty: Optional[float] = Query(None, ge=0, le=5),
    min_would_take_again: Optional[float] = Query(None, ge=0, le=100),
    min_num_ratings: Optional[int] = Query(None, ge=0),
    tag: Optional[str] = Query(None),
    course: Optional[str] = Query(None),
    sort_by: str = Query("avg_rating"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Search and filter professors with advanced criteria."""
    if not db.is_school_bootstrapped(school_id):
        raise HTTPException(
            status_code=400,
            detail="School not bootstrapped yet. Call POST /api/schools/{school_id}/bootstrap first.",
        )

    results, total = db.search_professors(
        school_id=school_id,
        q=q,
        department=department,
        min_rating=min_rating,
        max_difficulty=max_difficulty,
        min_would_take_again=min_would_take_again,
        min_num_ratings=min_num_ratings,
        tag=tag,
        course=course,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset,
    )

    professor_results = [
        ProfessorResult(
            id=p["id"],
            legacy_id=p.get("legacy_id"),
            school_id=p["school_id"],
            first_name=p["first_name"],
            last_name=p["last_name"],
            department=p.get("department"),
            avg_rating=p.get("avg_rating"),
            avg_difficulty=p.get("avg_difficulty"),
            num_ratings=p.get("num_ratings", 0),
            would_take_again_percent=p.get("would_take_again_percent"),
            tags=p.get("tags", []),
            courses=p.get("courses", []),
            rmp_link=p.get("rmp_link"),
        )
        for p in results
    ]

    return SearchResponse(
        results=professor_results,
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/professors/{professor_id}", response_model=ProfessorDetail)
async def get_professor_detail(professor_id: str):
    """Get full professor detail including ratings from RMP."""
    try:
        detail = await rmp_client.get_professor_detail(professor_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from RMP: {str(e)}")

    if not detail:
        raise HTTPException(status_code=404, detail="Professor not found")

    legacy_id = detail.get("legacyId")
    rmp_link = f"https://www.ratemyprofessors.com/professor/{legacy_id}" if legacy_id else None

    tags = []
    if detail.get("teacherRatingTags"):
        tags = [
            {"tagName": t["tagName"], "tagCount": t["tagCount"]}
            for t in detail["teacherRatingTags"]
            if t.get("tagCount", 0) > 0
        ]

    # Update tags in local DB
    courses_from_ratings = set()
    ratings = []
    if detail.get("ratings") and detail["ratings"].get("edges"):
        for edge in detail["ratings"]["edges"]:
            r = edge["node"]
            if r.get("class"):
                courses_from_ratings.add(r["class"])
            ratings.append(RatingResult(
                id=r.get("id"),
                legacy_id=r.get("legacyId"),
                course=r.get("class"),
                comment=r.get("comment"),
                clarity_rating=r.get("clarityRating"),
                difficulty_rating=r.get("difficultyRating"),
                helpful_rating=r.get("helpfulRating"),
                date=r.get("date"),
                grade=r.get("grade"),
                is_for_credit=r.get("isForCredit"),
                is_online=r.get("isForOnlineClass"),
                attendance_mandatory=r.get("attendanceMandatory"),
                rating_tags=r.get("ratingTags"),
                would_take_again=r.get("wouldTakeAgain"),
                thumbs_up=r.get("thumbsUpTotal", 0),
                thumbs_down=r.get("thumbsDownTotal", 0),
            ))

    # Update local cache with tags and courses
    db.update_professor_tags_and_courses(
        professor_id, tags, list(courses_from_ratings)
    )

    school_name = None
    if detail.get("school"):
        school_name = detail["school"].get("name")

    return ProfessorDetail(
        id=detail["id"],
        legacy_id=legacy_id,
        first_name=detail.get("firstName", ""),
        last_name=detail.get("lastName", ""),
        department=detail.get("department"),
        avg_rating=detail.get("avgRating"),
        avg_difficulty=detail.get("avgDifficulty"),
        num_ratings=detail.get("numRatings", 0),
        would_take_again_percent=detail.get("wouldTakeAgainPercent"),
        tags=tags,
        rmp_link=rmp_link,
        school_name=school_name,
        ratings=ratings,
    )


@app.get("/api/professors/{professor_id}/ratings", response_model=list[RatingResult])
async def get_all_professor_ratings(professor_id: str):
    """Fetch ALL ratings for a professor (paginated from RMP)."""
    try:
        raw_ratings = await rmp_client.get_all_ratings(professor_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch from RMP: {str(e)}")

    return [
        RatingResult(
            id=r.get("id"),
            legacy_id=r.get("legacyId"),
            course=r.get("class"),
            comment=r.get("comment"),
            clarity_rating=r.get("clarityRating"),
            difficulty_rating=r.get("difficultyRating"),
            helpful_rating=r.get("helpfulRating"),
            date=r.get("date"),
            grade=r.get("grade"),
            is_for_credit=r.get("isForCredit"),
            is_online=r.get("isForOnlineClass"),
            attendance_mandatory=r.get("attendanceMandatory"),
            rating_tags=r.get("ratingTags"),
            would_take_again=r.get("wouldTakeAgain"),
            thumbs_up=r.get("thumbsUpTotal", 0),
            thumbs_down=r.get("thumbsDownTotal", 0),
        )
        for r in raw_ratings
    ]
