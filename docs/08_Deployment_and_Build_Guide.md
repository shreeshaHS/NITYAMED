# NityaMed Deployment & Build Guide

## 1. Persistent PostgreSQL (Neon or Supabase)
1. Create a free PostgreSQL database on **Neon** (`neon.tech`) or **Supabase** (`supabase.com`).
2. Copy the connection string and ensure `?sslmode=require` is appended:
   ```text
   postgresql+psycopg://USER:PASSWORD@HOST:5432/nityamed?sslmode=require
   ```
3. Run migrations, curated seed, Indian medicine import, and admin creation locally against your production `DATABASE_URL` (one-time bootstrap):
   ```powershell
   cd C:\Users\asus\Desktop\NityaMed\backend
   $env:DATABASE_URL="postgresql+psycopg://USER:PASSWORD@HOST:5432/nityamed?sslmode=require"
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m app.modules.medicines.seed
   .\.venv\Scripts\python.exe -m app.modules.medicines.import_cli "C:\Users\asus\Desktop\Indian-Medicine-Dataset-main\DATA\updated_indian_medicine_data.csv"
   .\.venv\Scripts\python.exe -m app.modules.auth.create_admin_cli --email nityamed578@gmail.com --password "<STRONG_ADMIN_PASSWORD>"
   ```

## 2. Deploy Backend + Web to Render
1. Push `NityaMed` to a GitHub repository.
2. In Render Dashboard, click **New -> Blueprint** and select the repo containing `render.yaml`.
3. Fill in the prompted environment variables (`DATABASE_URL`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`).
4. Update `EXPO_PUBLIC_API_URL` on `nityamed-web` (if your API service URL differs from `https://nityamed-api.onrender.com/api/v1`) and update `CORS_ORIGINS` on `nityamed-api` to match your exact web URL.

## 3. Scheduled Dose Expiry, Refill & Backup Email Sweep
Because Render free-tier web services sleep when idle, trigger the protected sweep endpoint every 15 minutes using an external scheduler (e.g., `cron-job.org` or GitHub Actions):
- **Method:** `POST`
- **URL:** `https://<your-api>.onrender.com/api/v1/internal/jobs/sweep`
- **Header:** `X-Cron-Secret: <your CRON_SECRET from Render>`

## 4. Build Android APK with Expo EAS
1. Install EAS CLI and log in:
   ```powershell
   npm install -g eas-cli
   eas login
   ```
2. Configure `mobile/.env` with your deployed Render API URL:
   ```env
   EXPO_PUBLIC_API_URL=https://<your-api>.onrender.com/api/v1
   ```
3. Build an installable APK using `mobile/eas.json`:
   ```powershell
   cd C:\Users\asus\Desktop\NityaMed\mobile
   eas build -p android --profile preview
   ```
4. Download and install the generated `.apk` on your Android phone, then test offline SQLite sync, exact local dose alarms, and voice replies.
