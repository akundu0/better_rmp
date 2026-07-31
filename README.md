# Better RMP

A Chrome extension with advanced search and filtering for Rate My Professors. Unlike RMP's name-only search, Better RMP lets you filter professors by department, rating, difficulty, "would take again" percentage, tags, and more.

## Features

- **Advanced Filtering** — Filter by department, minimum rating, max difficulty, "would take again" %, minimum number of reviews, and professor tags
- **Sortable Results** — Sort by rating, difficulty, number of reviews, take-again %, or name
- **Professor Detail View** — See full ratings, reviews, grades, course codes, and tags
- **School Selector** — Search any US university on RMP; data is cached locally for instant filtering
- **Fast Local Search** — Professor data is bootstrapped into SQLite for sub-millisecond queries
- **Chrome Extension** — Access from your browser toolbar; works alongside your school's registration page

## Architecture

```
Chrome Extension (React + Vite + Tailwind)
        │
        ▼
  FastAPI Backend (Python)
        │
        ├── RMP GraphQL API (real-time professor detail + ratings)
        └── SQLite (cached professor index for fast filtering)
```

## Quick Start

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### 2. Start the Extension (Development)

```bash
cd extension
npm install
npm run dev
```

Open `http://localhost:5173` in your browser to use the web version during development.

### 3. Load as Chrome Extension

```bash
cd extension
npm run build
```

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked" and select the `extension/dist` folder
4. Click the extension icon in your toolbar

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

## Disclaimer

This project uses RateMyProfessors' public GraphQL API. It is unofficial and may break if RMP changes their API. Use responsibly and respect rate limits.