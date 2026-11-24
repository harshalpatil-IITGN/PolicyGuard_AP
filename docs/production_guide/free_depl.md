# 🚀 Free-Tier Production Deployment Guide ($0 Cost)

> **PolicyGuard AP — Live Deployment Playbook**  
> *Deploying the React Frontend on Vercel and the FastAPI Backend + SQLite ERP Data Layer on Render.*

---

## 📌 Deployment Overview

This deployment strategy allows you to run **PolicyGuard AP live on the internet 24/7 for $0**, without entering a credit card or incurring cloud bills.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             LIVE PUBLIC INTERNET                            │
├────────────────────────────────────────┬────────────────────────────────────┤
│           VERCEL (EDGE CDN)            │         RENDER (CLOUD VM)          │
│    https://policyguard-ap.vercel.app   │ https://policyguard-backend.onrender.com
├────────────────────────────────────────┼────────────────────────────────────┤
│  • React 18 + Vite Production Build    │  • FastAPI + Uvicorn Application   │
│  • Global Edge CDN Caching             │  • Deterministic 3-Way Policy Engine│
│  • Automatic SSL / HTTPS               │  • Multimodal Gemini AI Vision     │
│  • SPA Routing Rewrite Rules           │  • SQLite ERP & Audit Data Layer   │
└────────────────────────────────────────┴────────────────────────────────────┘
                                         ▲
                                         │ Webhook Interactivity
                       ┌─────────────────┴──────────────────┐
                       │          SLACK WORKSPACE           │
                       │ Interactive Decision Block Kit     │
                       └────────────────────────────────────┘
```

---

## 🗄️ How the Backend (`uvicorn`) and `data/` Are Deployed

A common question is: **"How can cloud hosts like Render run our Uvicorn backend and access our local `data/` folder?"**

### 1. Where Does the Data Live?
In PolicyGuard AP, the `data/` directory contains:
- `data/local_erp.db`: The SQLite database containing all 2,028 mock ERP records (invoices, PO lines, goods receipts, material master, approver matrix).
- `data/audit.db`: The immutable SQLite event audit trail.
- `data/uploads/`: Storage for uploaded vendor invoice PDFs and seed CSVs.

Because the `data/` directory is **committed directly to your GitHub repository**, when Render clones `https://github.com/harshalpatil-IITGN/PolicyGuard_AP.git`, the `data/` folder is cloned right alongside the backend code!

### 2. How the Backend Locates `data/`
Our [`backend/config.py`](file:///e:/Hackathons/Supervity/Track_A2__Three_Way_Match/backend/config.py) uses dynamic filesystem resolution:
```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Robust DATA_DIR resolution (supports both root-repo and backend-only deployment)
_custom_data_dir = os.environ.get("DATA_DIR")
if _custom_data_dir:
    DATA_DIR = Path(_custom_data_dir).resolve()
elif (PROJECT_ROOT / "data").exists():
    DATA_DIR = PROJECT_ROOT / "data"
elif (Path(__file__).resolve().parent / "data").exists():
    DATA_DIR = Path(__file__).resolve().parent / "data"
```
Whether Render executes from the root directory or inside `backend/`, it locates `data/local_erp.db` automatically.

### 3. Understanding Ephemeral Disk vs. Persistence
- **Render's Free Web Service provides an ephemeral disk**:
  - The pre-populated data (`local_erp.db` with 213 invoices) is baked into the Git commit and is **100% permanent across all deployments**.
  - New invoice status transitions (e.g. *Parked* $\to$ *Passed*) and new audit log entries written during runtime are saved to the container's disk.
  - If the free-tier service spins down after inactivity, it spins back up with the fresh Git-committed database.
  - **Result:** Your demo data never gets broken or corrupted, and you can reset or re-test scenarios repeatedly.

---

## 🛠️ Step-by-Step Deployment Instructions

### Prerequisites Checklist
- [x] Code pushed to GitHub: `https://github.com/harshalpatil-IITGN/PolicyGuard_AP.git`
- [ ] A free account on [Render.com](https://render.com) (sign up with GitHub)
- [ ] A free account on [Vercel.com](https://vercel.com) (sign up with GitHub)
- [ ] Your Google Gemini API Key and Slack Bot credentials handy

---

### Step 1: Deploy Backend to Render

1. Log in to your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** in the top right corner and select **Web Service**.
3. Choose **Build and deploy from a Git repository** $\to$ Click **Next**.
4. Connect your GitHub account and select repository: `harshalpatil-IITGN/PolicyGuard_AP`.
5. Configure the web service with the following settings:

| Field | Value | Notes |
| :--- | :--- | :--- |
| **Name** | `policyguard-backend` | Sets your URL prefix |
| **Region** | Singapore / Frankfurt / Oregon | Choose closest to you |
| **Branch** | `main` | Default branch |
| **Root Directory** | *(Leave Empty)* | Runs from repository root |
| **Runtime** | `Python 3` | Automatic Python detection |
| **Build Command** | `pip install -r backend/requirements.txt` | Installs FastAPI, Uvicorn, etc. |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` | Uses cloud-assigned port |
| **Instance Type** | **Free** ($0 / month) | 512 MB RAM, 0.1 CPU |

6. Scroll down to **Environment Variables** and add the following keys:

| Key | Value | Purpose |
| :--- | :--- | :--- |
| `ERP_DATA_SOURCE` | `local` | Uses the built-in SQLite database |
| `GEMINI_API_KEY` | `AIzaSy...` | Your Google Gemini AI Studio key |
| `GEMINI_MODEL` | `gemini-flash-lite-latest` | High-speed multimodal model |
| `SLACK_BOT_TOKEN` | `xoxb-...` | Slack Bot OAuth token |
| `SLACK_SIGNING_SECRET` | `...` | Slack signature verification secret |
| `SLACK_CHANNEL_ID` | `C0...` | Target Slack alert channel |
| `BUSINESS_DATE` | `2026-10-09T18:00:00+05:30` | Ashvaka ERP business date |

7. Click **Create Web Service**.
8. Wait 2–3 minutes for the build to finish. Once you see `Application startup complete`, copy your backend URL:
   ```
   https://policyguard-backend.onrender.com
   ```
9. **Verify Health:** Open `https://policyguard-backend.onrender.com/health` in your browser. You should see:
   ```json
   {"status": "ok", "app": "PolicyGuard AP", "business_date": "2026-10-09T18:00:00+05:30"}
   ```

---

### Step 2: Deploy Frontend to Vercel

1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** $\to$ **Project**.
3. Locate `PolicyGuard_AP` under *Import Git Repository* and click **Import**.
4. In the **Configure Project** screen:
   - **Project Name:** `policyguard-ap`
   - **Framework Preset:** `Vite` (Vercel auto-detects this)
   - **Root Directory:** Click **Edit** $\to$ Select `frontend` $\to$ Click **Continue**.
5. Expand **Environment Variables** and add:
   - **Name:** `VITE_API_URL`
   - **Value:** `https://policyguard-backend.onrender.com/api` *(Your Render URL + `/api`)*
6. Click **Deploy**.
7. In ~45 seconds, Vercel will complete the build and show confetti 🎉!
8. Click **Visit** to see your live frontend (e.g. `https://policyguard-ap.vercel.app`).

---

### Step 3: Connect Slack Interactivity (Replace ngrok Permanently)

With your backend live on Render, you no longer need `ngrok` running on your local machine!

1. Open [api.slack.com/apps](https://api.slack.com/apps) $\to$ Select your app (`PolicyGuard AP`).
2. In the left sidebar, click **Interactivity & Shortcuts**.
3. Ensure the toggle is **On**.
4. In the **Request URL** field, replace your old ngrok URL with:
   ```
   https://policyguard-backend.onrender.com/api/slack/interact
   ```
5. Click **Save Changes** at the bottom of the screen.

Now, whenever an invoice is escalated (Story 2) or stopped (Story 3), clicking **Approve**, **Reject**, or **Release** directly from your phone's Slack app will immediately reach your live backend on Render!

---

## ⚡ Free-Tier Nuances & Pro-Tips

### 1. Handling Render's Free-Tier Spin-Down ("Cold Starts")
- **Behavior:** On Render's free tier, if no requests arrive for 15 minutes, the web service spins down into sleep mode to conserve resources.
- **Waking Up:** The next incoming request will take ~30–45 seconds to spin up.
- **Pro-Tip (Keep Alive):** Before a client demonstration, visit `https://policyguard-backend.onrender.com/health` in your browser 1 minute in advance.
- **Automated Keep-Alive:** You can set up a free monitor on [UptimeRobot.com](https://uptimerobot.com) or [cron-job.org](https://cron-job.org) to ping your `/health` endpoint every 10 minutes. This keeps the service 100% warm 24/7 at zero cost!

### 2. Immediate Scenario Resetting
During live presentations, if you want to run Scenario B or C again:
- Use the **↺ Reset to Parked** button on any of the 4 Story cards on the Dashboard.
- Alternatively, make a single PATCH call:
  ```bash
  curl -X PATCH https://policyguard-backend.onrender.com/api/invoices/5105600035/status \
       -H "Content-Type: application/json" \
       -d '{"status": "Parked"}'
  ```

---

## 📋 Verification Checklist

| Test Item | Endpoint / Action | Expected Result |
| :--- | :--- | :--- |
| **Backend Health** | `GET /health` | HTTP 200 `{"status": "ok"}` |
| **ERP Invoice List** | `GET /api/invoices` | HTTP 200 with 213 invoices |
| **Story 1 (Auto-Pass)** | Click *Run Live Match* on Card 1 | Status turns **Passed** (< 1.5s) |
| **Story 2 (Slack HITL)** | Click *Run Live Match* on Card 2 | Status turns **Escalated**, Block Kit card arrives on Slack |
| **Slack Interactive Approval**| Click *Approve* in Slack | Slack card updates, Dashboard status turns **Passed** |
| **Story 3 (Auto-Stop)** | Click *Run Live Match* on Card 3 | Status turns **Stopped** (`CL-1` closed PO defense) |
| **Story 4 (PDF Ingestion)**| Upload `SankalpElectric...pdf` | Gemini extracts data, live 3-way match renders |
