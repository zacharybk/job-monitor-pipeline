# job-monitor-pipeline

Automated job scraper and scorer. Scrapes hundreds of company career pages, fetches full job descriptions, and uses Claude AI to score each role against your personal profile. Results land in a Supabase database you can query or display on a job board.

## How It Works

Four phases run on a cron schedule (2x/day by default):

1. **Scrape** — Hits all sources in `job_sources.json` using Playwright. Stores every job in Supabase and tracks seen URLs so subsequent runs only process new postings.
2. **Filter** — Marks jobs relevant based on title/location rules you configure. Non-matching roles (engineering, marketing, HR, non-US) are excluded before any expensive operations run.
3. **Enrich** — Fetches the full job description text for each relevant job.
4. **Score** — Sends each JD + your profile to Claude Haiku. Returns a 0–10 match score and one-sentence reasoning.

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/zacharybk/job-monitor-pipeline
cd job-monitor-pipeline
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
ANTHROPIC_API_KEY=your_anthropic_key
```

### 3. Set up Supabase

Create a free project at [supabase.com](https://supabase.com), then run `schema_v2.sql` in the SQL editor.

### 4. Create your profile

```bash
cp profile.example.md profile.md
```

Edit `profile.md` — this is what the AI scores jobs against. Be specific about your background, target roles, and what makes a strong fit.

### 5. Configure filters

Open `pipeline/config.py` and adjust `INCLUDE_TITLE_KEYWORDS`, `EXCLUDE_TITLE_KEYWORDS`, and location filters to match the roles you're targeting.

### 6. Configure sources

Edit `job_sources.json` to add or remove companies. Each source needs a `name`, `url`, and `type` (`ashby`, `greenhouse`, `lever`, `vc_job_board`, `career_page`).

### 7. Run locally

```bash
python -m pipeline.run
```

First run will be slow — it scrapes everything, enriches all relevant jobs, and scores them. Subsequent runs only process new postings.

### 8. Deploy to DigitalOcean

Create a $6/mo Ubuntu 24.04 droplet, update `SERVER=` in `deploy.sh`, then:

```bash
bash deploy.sh
```

Cron runs at 10am and 4pm EST by default.

## Adding Sources

Add entries to `job_sources.json`:

```json
{
  "name": "Company Name",
  "url": "https://jobs.ashbyhq.com/company-slug",
  "type": "ashby"
}
```

Supported types: `ashby`, `greenhouse`, `lever`, `vc_job_board`, `career_page`, `workatastartup`

## Supabase Schema

Jobs are stored with title, company, location, URL, work type, full description, match score, and match reasoning. The `seen_jobs` table tracks processed URLs so re-runs are fast.

## Reusing for Your Own Search

This pipeline is profile-agnostic. Swap `profile.md` for your own background, adjust the keyword filters in `config.py`, point `.env` at your own Supabase project, and run. The sources list in `job_sources.json` covers ~500 companies — add or remove as needed.
