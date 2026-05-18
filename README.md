# NISHAAN Autonomous Agent

Autonomous crisis intelligence backend for the **NISHAAN** system — deployed as a Vercel serverless function.

## What it does

Every minute (via an external cron manager triggering the serverless function), the agent:
1. **Fetches signals** — weather (OpenWeatherMap), social media (simulated), traffic (simulated)
2. **Fuses & classifies** — Groups by neighborhood, classifies via Groq LLM (llama-3.1-8b)
3. **Verifies** — Checks for false alarms with field inspector simulation
4. **Allocates resources** — Dispatches ambulances, rescue teams, police, etc.
5. **Simulates actions** — Estimates response times and side effects
6. **Writes to Firestore** — Crises, alerts, agent traces
7. **Links missing persons** — Matches unlinked missing person reports to nearby active crises

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/run` | GET | Runs one agent cycle (triggered externally) |
| `/api/health` | GET | Health check |

## Deployment (Vercel)

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/nishaan-agent.git
git push -u origin main
```

### 2. Connect to Vercel
- Go to [vercel.com](https://vercel.com) → Import Git Repository
- Select the `nishaan-agent` repo

### 3. Set Environment Variables
In Vercel Dashboard → Settings → Environment Variables, add:

| Variable | Description |
|---|---|
| `OPENWEATHERMAP_API_KEY` | OpenWeatherMap API key |
| `GROQ_API_KEY` | Groq API key for LLM classification |
| `FIREBASE_SERVICE_ACCOUNT_BASE64` | Base64-encoded Firebase service account JSON |

#### Generate the Firebase base64 key:
```bash
# PowerShell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("serviceAccountKey.json"))

# Or Python
python -c "import base64; print(base64.b64encode(open('serviceAccountKey.json','rb').read()).decode())"
```

### 4. Setup Free 1-Minute Cron Trigger (External)
Since Vercel Hobby accounts restrict native cron jobs to once per day, use a free external service like **[cron-job.org](https://cron-job.org/)**:
1. Create a free account at [cron-job.org](https://cron-job.org/).
2. Click **Create Cronjob**.
3. Set the Title to `Nishaan Agent Loop`.
4. Set the URL to your deployed Vercel endpoint: `https://your-project.vercel.app/api/run`.
5. Under **Schedule**, choose **Every 1 minute** (or any interval you prefer).
6. Click **Create**. It will now trigger your serverless agent live every minute completely for free!

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Fill in your API keys

# Run locally (one-shot)
python -c "from api.run import agent_loop; print(agent_loop())"
```

## Architecture

```
api/
├── run.py              ← Serverless entry point (Vercel function)
└── health.py           ← Health check

agent/
├── signal_fuser.py     ← Combines weather + social + traffic
├── crisis_classifier.py ← LLM-based crisis classification (Groq)
├── resource_allocator.py ← Resource dispatch logic
├── action_simulator.py  ← Response simulation
└── stakeholder_notifier.py ← Message generation

signals/
├── weather_signal.py   ← OpenWeatherMap fetcher
├── social_signal.py    ← Simulated social media reports
└── traffic_signal.py   ← Simulated traffic data

firestore/
└── writer.py           ← Firestore CRUD operations
```
