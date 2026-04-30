# Precision HCC — Semiconductor Ops Guide
### Team Checklist & Guidance App

---

## What this is

A private web app for the Precision HCC team. It contains checklists and
detailed guidance for all four semiconductor service capabilities:

1. Compliance & Documentation Systems
2. Workforce Infrastructure
3. Safety & Risk Compliance
4. Electronics & Instrumentation

Team members log in, check off items as they're completed, and add notes
to any checklist item that the whole team can see. Vanessa (admin) gets a
dashboard showing everyone's progress.

---

## Running it on your computer (5 minutes)

**Step 1 — Make sure Python is installed**

Open Terminal (Mac) or Command Prompt (Windows) and type:
```
python --version
```
If you see `Python 3.x.x` you're good. If not, download Python from
https://python.org (click "Download Python 3.xx").

**Step 2 — Install the app's dependencies**

In Terminal/Command Prompt, navigate to this folder:
```
cd path/to/precision-ops-app
```
Then run:
```
pip install -r requirements.txt
```

**Step 3 — Start the app**

```
python start.py
```

You'll see:
```
  Precision HCC — Ops Guide
  http://localhost:5000
  Invite code: precision2024
```

**Step 4 — Open in browser**

Go to: http://localhost:5000

The first person to register becomes the admin automatically.

---

## Sharing with your team (free cloud hosting on Render.com)

Render is a free hosting service. This takes about 10 minutes.

**Step 1** — Create a free account at https://render.com

**Step 2** — Upload this folder to GitHub (free at github.com)
- Create a new repository (private is fine)
- Upload all the files in this folder

**Step 3** — In Render, click "New" → "Web Service"
- Connect your GitHub account
- Select your repository
- Set these fields:
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `python start.py`
  - **Environment:** Python 3

**Step 4** — Add environment variables in Render (under "Environment"):
```
SECRET_KEY     = (any long random string, e.g. "MyPrecisionApp2024SecretKey!")
INVITE_CODE    = (the code you want staff to use to register, e.g. "precision2024")
PORT           = 10000
```

**Step 5** — Click "Create Web Service"

Render gives you a URL like `https://precision-ops.onrender.com`.
Share that URL with your team along with the invite code.

**Cost:** Free tier keeps the app running. It may "sleep" after 15 minutes
of no use (free tier limitation) — it wakes up in about 30 seconds when
someone visits.

---

## How to use the app

**Registering:**
- Go to the app URL
- Click "Register"
- Enter your name, email, password, and the invite code
- The first person to register becomes admin

**Checking off items:**
- Click any checklist item to mark it done (turns green)
- Your progress saves automatically to the server
- Refresh the page — your checkmarks are still there

**Adding notes:**
- Click "Notes" on any checklist item
- Type your note and click Add
- Notes are visible to everyone on the team

**Admin dashboard (Vanessa only):**
- Click "Admin Dashboard" in the left sidebar
- See every team member's progress bars across all 4 capabilities
- See recent activity (who checked what and when)
- Promote team members to admin, or remove them

---

## Invite code

The default invite code is: **precision2024**

To change it, set the `INVITE_CODE` environment variable before starting:

On Mac/Linux:
```
INVITE_CODE=mynewcode python start.py
```

On Render: update the environment variable in the dashboard.

---

## Changing the admin password

Log in as admin, then at the bottom of the sidebar click your name
and update your password. Or contact your hosting provider to reset the database.

---

## Files in this folder

```
precision-ops-app/
├── start.py           ← Run this to start the app
├── requirements.txt   ← Python packages needed
├── README.md          ← This file
├── server/
│   └── app.py         ← Backend (API, auth, database)
├── public/
│   └── index.html     ← Frontend (the app itself)
└── db/
    └── precision_ops.db  ← Created automatically on first run
```

The database file (`db/precision_ops.db`) is a single file that stores
all users, progress, and notes. Back it up regularly by copying that file.

---

## Resetting all progress

Delete the file `db/precision_ops.db` and restart the app.
Everyone will need to re-register.

---

## Support

Built for Precision HealthCare Consultants.
Contact: vbest@precisionhcc.com | 516-906-8600
