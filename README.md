# NEXORA / LandSecureAI

Intelligent Land Record Digitization and Validation System for Smart India Hackathon 2026.

## Local run

```powershell
cd C:\Users\vyshn\Downloads\LandSecureAI
.\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001.

## Public deployment: Render

Render is the simplest free option for this FastAPI prototype. It provides a public HTTPS subdomain automatically, so no router configuration or local tunnel is required. The included `render.yaml` contains the build, start, and health-check settings.

1. Create or sign in to a GitHub account.
2. Create a new GitHub repository, for example `landsecureai`.
3. From this project folder, commit and push the project:

   ```powershell
   git init
   git add .
   git commit -m "Prepare LandSecureAI for deployment"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/landsecureai.git
   git push -u origin main
   ```

4. Open https://render.com and sign in with GitHub.
5. Choose **New +** and select **Blueprint**.
6. Select the GitHub repository and branch `main`.
7. Confirm the service from `render.yaml`, then click **Apply**.
8. Wait for the build and deploy to finish. Render will display a URL such as `https://landsecureai.onrender.com`.
9. Open that URL from any device or network. The HTTPS URL is the shareable public address.

The deployment command is:

```text
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

`$PORT` is supplied by Render. Do not hard-code port `8001` in the hosted service.

## Demo behavior

- Upload any PDF, image, or text file. OCR and validation are simulated locally, so Tesseract, API keys, government APIs, and a database are not required.
- The upload response contains the predefined Ravi Kumar registry comparison, extracted OCR details, and six field checks.
- Use `Demo: Show Mismatch` to show realistic area and boundary mismatches with a manual-review warning.

## Endpoints

- `GET /`
- `GET /health`
- `GET /api/stats`
- `GET /api/records`
- `GET /api/records/{record_id}`
- `POST /api/validate` with multipart field `file`
