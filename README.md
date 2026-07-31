# Better RMP

A Chrome extension with advanced search and filtering for Rate My Professors. Unlike RMP's name-only search, Better RMP lets you filter professors by department, rating, difficulty, "would take again" percentage, tags, and more.

[![CI](https://github.com/akundu0/better_rmp/actions/workflows/ci.yml/badge.svg)](https://github.com/akundu0/better_rmp/actions/workflows/ci.yml)

## Features

- **Advanced Filtering** — Filter by department, minimum rating, max difficulty, "would take again" %, minimum number of reviews, and professor tags
- **Sortable Results** — Sort by rating, difficulty, number of reviews, take-again %, or name
- **Professor Detail View** — See full ratings, reviews, grades, course codes, and tags
- **School Selector** — Search any US university on RMP; data is cached locally for instant filtering
- **Fast Local Search** — Professor data is bootstrapped into SQLite for sub-millisecond filtered queries
- **Chrome Extension** — Access from your browser toolbar; works alongside your school's registration page
- **Resilient** — Retry logic with exponential backoff, structured logging, and graceful error handling

## Installation

### Chrome / Edge / Chromium

1. Download [better-rmp-v1.0.0.zip](https://github.com/akundu0/better_rmp/releases/latest/download/better-rmp-v1.0.0.zip) from the [latest release](https://github.com/akundu0/better_rmp/releases/latest)
2. Unzip the file
3. Go to `chrome://extensions` and enable **Developer mode** (top right toggle)
4. Click **Load unpacked** and select the unzipped folder
5. The Better RMP icon will appear in your toolbar

### Backend (required)

The extension needs the backend API running locally:

```bash
# Clone the repo
git clone https://github.com/akundu0/better_rmp.git
cd better_rmp

# Install Python dependencies
pip install -r backend/requirements.txt

# Start the API server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Architecture

```
┌───────────────────────────────────────┐
│     Chrome Extension (Popup UI)       │
│     React 19 + TypeScript + Tailwind  │
└──────────────┬────────────────────────┘
               │ HTTP (localhost:8000)
┌──────────────▼────────────────────────┐
│         FastAPI Backend               │
│                                       │
│  ┌─────────────┐  ┌───────────────┐   │
│  │   SQLite    │  │  RMP GraphQL  │   │
│  │  (cached    │  │   API proxy   │   │
│  │  professor  │  │  (real-time   │   │
│  │   index)    │  │   ratings)    │   │
│  └─────────────┘  └───────────────┘   │
└───────────────────────────────────────┘
```

**Data flow:**
1. User selects a school → backend fetches all professors from RMP's GraphQL API and stores them in SQLite
2. User searches/filters → backend queries SQLite (sub-millisecond) and returns results
3. User clicks a professor → backend fetches live detail + ratings from RMP GraphQL

## Development

### Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run with auto-reload
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
python -m pytest backend/tests/ -v
```

### Frontend

```bash
cd extension
npm install
npm run dev      # Dev server at http://localhost:5173
npm run build    # Production build to dist/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/schools/search?q=...` | Search for schools on RMP |
| `GET` | `/api/schools` | List bootstrapped schools |
| `POST` | `/api/schools/{id}/bootstrap` | Fetch & cache all professors for a school |
| `GET` | `/api/schools/{id}/departments` | Get departments at a school |
| `GET` | `/api/schools/{id}/tags` | Get all professor tags at a school |
| `GET` | `/api/professors/search?school_id=...&...` | Search/filter professors |
| `GET` | `/api/professors/{id}` | Get professor detail + recent ratings |
| `GET` | `/api/professors/{id}/ratings` | Get all ratings for a professor |

### Search Parameters

| Param | Type | Description |
|-------|------|-------------|
| `school_id` | string | Required — RMP school ID |
| `q` | string | Name search (partial match) |
| `department` | string | Exact department match |
| `min_rating` | float | Minimum average rating (0-5) |
| `max_difficulty` | float | Maximum difficulty (0-5) |
| `min_would_take_again` | float | Minimum "would take again" % (0-100) |
| `min_num_ratings` | int | Minimum number of reviews |
| `tag` | string | Professor tag filter |
| `sort_by` | string | `avg_rating`, `avg_difficulty`, `num_ratings`, `would_take_again_percent`, `last_name` |
| `sort_order` | string | `asc` or `desc` |

## Tech Stack

- **Frontend**: React 19, TypeScript, Vite 8, Tailwind CSS 4, Lucide Icons
- **Backend**: Python 3.12, FastAPI, SQLite, httpx
- **Data Source**: RateMyProfessors GraphQL API (unofficial, no API key needed)
- **Extension**: Chrome Manifest V3
- **CI/CD**: GitHub Actions (test → build → release)
- **Testing**: pytest (47 tests), React Error Boundaries

## Project Structure

```
better_rmp/
├── backend/
│   ├── main.py          # FastAPI app, endpoints, error handlers
│   ├── database.py      # SQLite layer with indexed queries
│   ├── rmp_client.py    # RMP GraphQL client with retry logic
│   ├── requirements.txt
│   └── tests/
│       ├── test_api.py      # API endpoint tests
│       └── test_database.py # Database layer tests
├── extension/
│   ├── public/
│   │   └── manifest.json    # Chrome Manifest V3
│   ├── src/
│   │   ├── api.ts           # Typed API client
│   │   ├── App.tsx          # Root component with school persistence
│   │   └── components/
│   │       ├── SchoolSelector.tsx   # School search + bootstrap
│   │       ├── SearchView.tsx       # Main search UI + pagination
│   │       ├── FilterPanel.tsx      # Collapsible filter controls
│   │       ├── ProfessorCard.tsx    # Result card with rating badges
│   │       ├── ProfessorDetail.tsx  # Full detail + reviews
│   │       └── ErrorBoundary.tsx    # Graceful error handling
│   └── vite.config.ts
└── .github/workflows/
    ├── ci.yml           # Test + build on push/PR
    └── release.yml      # Build + zip + GitHub Release on tag
```

## Disclaimer

This project uses RateMyProfessors' public GraphQL API. It is unofficial and may break if RMP changes their API. Use responsibly and respect rate limits.

## License

MIT