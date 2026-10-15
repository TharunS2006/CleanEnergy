# Putting the project on Vercel

Vercel runs the API as a serverless function. A serverless function has no disk that survives
between requests, so the SQLite file used on your laptop cannot be used there. The project
therefore switches to PostgreSQL automatically when the environment variable `DATABASE_URL` is set.
(This was tested against PostgreSQL 16: all 13 tests pass on it. It has not been run on Vercel itself
from the machine this was written on, so if something differs, check the "If it fails" list below.)

## 1. A free Postgres database

1. Go to https://neon.tech and create a free project (or add "Neon" / "Postgres" from the Storage tab of your Vercel project).
2. Copy the connection string. It looks like `postgresql://user:password@ep-xxxx.neon.tech/neondb?sslmode=require`.

## 2. Create the tables and sample data (once, from your laptop)

```bash
# Windows PowerShell
$env:DATABASE_URL = "postgresql://...your string..."
python seed.py

# Mac / Linux
DATABASE_URL="postgresql://...your string..." python seed.py
```

## 3. Deploy

1. Push this folder to a GitHub repository.
2. On https://vercel.com choose **Add New > Project**, import the repository. Framework preset: **FastAPI** (or "Other").
3. Under **Environment Variables** add `DATABASE_URL` with the same connection string.
4. Press **Deploy**. Your site is at `https://your-project.vercel.app` and the API docs at `/docs`.

Or with the command line: `npm i -g vercel`, then `vercel` in this folder, then add `DATABASE_URL` in the dashboard and run `vercel --prod`.

## If it fails

* **500 errors / cannot connect:** `DATABASE_URL` is missing or wrong in the Vercel project settings. Redeploy after changing it.
* **Page is blank but /docs works:** the files in `public/` were not deployed. Check that `public` is committed and not ignored.
* **Function not found:** the entry point is `index.py` in the project root, which imports `app` from `app/main.py`.
* **Slow first request:** serverless cold start, normal on the free plan.
