# eShopCo latency analytics on Vercel

This project provides `POST /`, which summarizes the bundled telemetry for each requested region.

## 1. Add the sample data

Download `q-vercel-latency.json` from the assignment page and place it beside `vercel.json` (the project root). Keep the filename exactly as shown. The endpoint reads this bundled, read-only file when it handles a request.

## 2. Deploy it

1. Create a GitHub repository and upload this project's files, including the JSON bundle.
2. In a terminal, change into this project folder and run `npx vercel`.
3. If asked, sign in to Vercel, choose your account, and accept the suggested project settings.
4. Vercel prints a test URL such as `https://your-project-name.vercel.app`. The endpoint URL is that URL followed by `/` (the root endpoint).
5. To publish a production deployment, run `npx vercel --prod`. Use the production URL Vercel prints, with `/` at the end if desired.

The public endpoint URL cannot be known until you create the Vercel project and deploy it.

## 3. Send a POST request

Send JSON with `Content-Type: application/json`, for example:

```json
{"regions":["emea","apac"],"threshold_ms":188}
```

The response has one object per requested region, with `avg_latency`, `p95_latency`, `avg_uptime`, and `breaches`. The p95 uses linear interpolation; breaches count latency values strictly greater than the supplied threshold. CORS permits POST and OPTIONS from any origin.

To test from PowerShell after deployment:

```powershell
$body = @{ regions = @('emea', 'apac'); threshold_ms = 188 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'https://YOUR-PROJECT.vercel.app/' -ContentType 'application/json' -Body $body
```

Replace `YOUR-PROJECT` with the deployment name printed by Vercel.

## Data shape

The supplied JSON should contain a list of records with a region, latency, and uptime field. Common field names such as `region`, `latency_ms`/`latency`, and `uptime` are supported. It can also wrap the list in `data`, `records`, `telemetry`, `pings`, or `results`.
