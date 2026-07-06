# Spotter HOS Trip Planner

Django + React app for planning truck trips and generating daily log sheets.

### Live app: https://hos-trip-planner-ten.vercel.app

## What It Does

- Takes current location, pickup, dropoff, current cycle used and start time.
- Shows a route map using OpenStreetMap, Nominatim, OSRM and Leaflet.
- Plans pickup/dropoff, fuel stops, breaks, rests and 34 hour restarts.
- Generates downloadable daily log sheets.

## Run Locally

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver 0.0.0.0:8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Environment

Frontend:

```bash
VITE_API_BASE=http://localhost:8000
```

Backend:

```bash
DJANGO_SECRET_KEY=replace-me
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=your-backend-host.com
CORS_ALLOWED_ORIGINS=https://your-frontend-host.com
```

## Assumptions

- Property carrying driver.
- 70 hour/8 day cycle.
- No adverse driving conditions.
- Pickup and dropoff each take 1 hour.
- Fuel stop at least every 1,000 miles.
