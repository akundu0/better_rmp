"""Direct client for the RateMyProfessors GraphQL API.
No API key required — uses the public auth token embedded in RMP's frontend.
Includes retry logic with exponential backoff and structured logging.
"""

import asyncio
import base64
import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger("better_rmp.rmp_client")

RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
RMP_AUTH_TOKEN = base64.b64encode(b"test:test").decode()

HEADERS = {
    "Authorization": f"Basic {RMP_AUTH_TOKEN}",
    "Content-Type": "application/json",
    "User-Agent": "BetterRMP/1.0",
}

MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds
_MIN_INTERVAL = 0.5  # rate limit: max 2 requests/sec
_last_request_time = 0.0


class RMPError(Exception):
    """Base exception for RMP client errors."""


class RMPGraphQLError(RMPError):
    """The RMP GraphQL API returned an errors array."""


class RMPConnectionError(RMPError):
    """Could not connect to the RMP API."""


class RMPRateLimitError(RMPError):
    """RMP rate-limited our request."""


async def _rate_limited_post(client: httpx.AsyncClient, payload: dict) -> dict:
    global _last_request_time
    now = time.monotonic()
    wait = _MIN_INTERVAL - (now - _last_request_time)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_request_time = time.monotonic()

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await client.post(
                RMP_GRAPHQL_URL, json=payload, headers=HEADERS, timeout=30.0
            )

            if resp.status_code == 429:
                backoff = BASE_BACKOFF * (2 ** (attempt - 1))
                logger.warning("RMP rate limited (429), retrying in %.1fs (attempt %d/%d)", backoff, attempt, MAX_RETRIES)
                await asyncio.sleep(backoff)
                continue

            resp.raise_for_status()
            data = resp.json()

            if "errors" in data:
                raise RMPGraphQLError(f"RMP GraphQL error: {data['errors']}")

            return data

        except httpx.TimeoutException as e:
            last_exc = e
            backoff = BASE_BACKOFF * (2 ** (attempt - 1))
            logger.warning("RMP request timed out, retrying in %.1fs (attempt %d/%d)", backoff, attempt, MAX_RETRIES)
            await asyncio.sleep(backoff)

        except httpx.ConnectError as e:
            last_exc = e
            backoff = BASE_BACKOFF * (2 ** (attempt - 1))
            logger.warning("RMP connection error: %s, retrying in %.1fs (attempt %d/%d)", str(e)[:100], backoff, attempt, MAX_RETRIES)
            await asyncio.sleep(backoff)

        except (httpx.HTTPStatusError, RMPGraphQLError):
            raise

    raise RMPConnectionError(f"Failed to reach RMP after {MAX_RETRIES} attempts: {last_exc}")


# ── Search schools ────────────────────────────────────────────────────────────

SEARCH_SCHOOLS_QUERY = """
query SearchSchoolsQuery($query: SchoolSearchQuery!) {
  newSearch {
    schools(query: $query) {
      edges {
        node {
          id
          legacyId
          name
          city
          state
        }
      }
    }
  }
}
"""


async def search_schools(query: str) -> list[dict]:
    async with httpx.AsyncClient(verify=False) as client:
        payload = {
            "query": SEARCH_SCHOOLS_QUERY,
            "variables": {"query": {"text": query}},
        }
        data = await _rate_limited_post(client, payload)
        edges = data["data"]["newSearch"]["schools"]["edges"]
        return [edge["node"] for edge in edges]


# ── Search professors at a school ────────────────────────────────────────────

SEARCH_PROFESSORS_QUERY = """
query SearchTeachersQuery($query: TeacherSearchQuery!, $cursor: String) {
  newSearch {
    teachers(query: $query, first: 1000, after: $cursor) {
      edges {
        cursor
        node {
          id
          legacyId
          firstName
          lastName
          department
          avgRating
          avgDifficulty
          numRatings
          wouldTakeAgainPercent
          school {
            id
            legacyId
            name
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


async def search_professors_at_school(
    school_id: str, query: str = "", cursor: Optional[str] = None
) -> tuple[list[dict], Optional[str]]:
    """Search professors at a school. Returns (professors, next_cursor)."""
    async with httpx.AsyncClient(verify=False) as client:
        variables: dict = {
            "query": {"text": query, "schoolID": school_id},
        }
        if cursor:
            variables["cursor"] = cursor
        payload = {
            "query": SEARCH_PROFESSORS_QUERY,
            "variables": variables,
        }
        data = await _rate_limited_post(client, payload)
        teachers = data["data"]["newSearch"]["teachers"]
        edges = teachers["edges"]
        page_info = teachers["pageInfo"]
        professors = [edge["node"] for edge in edges]
        next_cursor = page_info["endCursor"] if page_info["hasNextPage"] else None
        return professors, next_cursor


async def get_all_professors_at_school(school_id: str) -> list[dict]:
    """Fetch ALL professors at a school by paginating through search results.
    Uses an empty query string to match all professors.
    """
    all_professors = []
    cursor = None
    page = 0

    async with httpx.AsyncClient(verify=False) as client:
        while True:
            page += 1
            variables: dict = {"query": {"text": "", "schoolID": school_id}}
            if cursor:
                variables["cursor"] = cursor

            payload = {
                "query": SEARCH_PROFESSORS_QUERY,
                "variables": variables,
            }
            data = await _rate_limited_post(client, payload)
            teachers = data["data"]["newSearch"]["teachers"]
            edges = teachers["edges"]
            page_info = teachers["pageInfo"]

            professors = [edge["node"] for edge in edges]
            all_professors.extend(professors)
            logger.info("Page %d: fetched %d professors (total: %d)", page, len(professors), len(all_professors))

            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    return all_professors


# ── Get professor detail with ratings ─────────────────────────────────────────

PROFESSOR_DETAIL_QUERY = """
query ProfessorDetailQuery($id: ID!) {
  node(id: $id) {
    ... on Teacher {
      id
      legacyId
      firstName
      lastName
      department
      avgRating
      avgDifficulty
      numRatings
      wouldTakeAgainPercent
      teacherRatingTags {
        tagName
        tagCount
      }
      school {
        id
        legacyId
        name
      }
      ratings(first: 20) {
        edges {
          node {
            id
            legacyId
            class
            comment
            clarityRating
            difficultyRating
            date
            grade
            helpfulRating
            isForCredit
            isForOnlineClass
            attendanceMandatory
            ratingTags
            textbookUse
            wouldTakeAgain
            thumbsUpTotal
            thumbsDownTotal
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""


async def get_professor_detail(professor_id: str) -> Optional[dict]:
    """Fetch full professor detail including recent ratings."""
    async with httpx.AsyncClient(verify=False) as client:
        payload = {
            "query": PROFESSOR_DETAIL_QUERY,
            "variables": {"id": professor_id},
        }
        data = await _rate_limited_post(client, payload)
        return data["data"]["node"]


PROFESSOR_RATINGS_PAGE_QUERY = """
query ProfessorRatingsQuery($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on Teacher {
      ratings(first: 20, after: $cursor) {
        edges {
          node {
            id
            legacyId
            class
            comment
            clarityRating
            difficultyRating
            date
            grade
            helpfulRating
            isForCredit
            isForOnlineClass
            attendanceMandatory
            ratingTags
            textbookUse
            wouldTakeAgain
            thumbsUpTotal
            thumbsDownTotal
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
  }
}
"""


async def get_all_ratings(professor_id: str) -> list[dict]:
    """Fetch ALL ratings for a professor by paginating."""
    all_ratings = []
    cursor = None

    async with httpx.AsyncClient(verify=False) as client:
        while True:
            variables: dict = {"id": professor_id}
            if cursor:
                variables["cursor"] = cursor

            payload = {
                "query": PROFESSOR_RATINGS_PAGE_QUERY,
                "variables": variables,
            }
            data = await _rate_limited_post(client, payload)
            node = data["data"]["node"]
            if not node or "ratings" not in node:
                break

            ratings_data = node["ratings"]
            edges = ratings_data["edges"]
            page_info = ratings_data["pageInfo"]

            ratings = [edge["node"] for edge in edges]
            all_ratings.extend(ratings)

            if not page_info["hasNextPage"]:
                break
            cursor = page_info["endCursor"]

    return all_ratings
