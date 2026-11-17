# PrintPulse Monitoring Dashboard

A React/Vite frontend connected to a Django API for the Printer Monitoring and Paper Usage Management System capstone.

## Included in this prototype

- Printer monitoring dashboard with page totals, active printer count, and error count
- Printing activity chart with time-range selector
- Paper usage breakdown for A4, Short/Letter, and Long/Legal
- Recent print job table with user, printer, pages, paper size, status, and time
- System alert list for low paper, offline printers, and paper jams
- Printer inventory with manual registration and Windows Spooler discovery
- Print job history, paper usage summaries, report metrics, and administrator settings
- Formatted PDF downloads with paper usage, printer inventory, print jobs, and printer error history

## Run locally

Install Node.js 18 or newer, then run:

```bash
npm install
npm run dev
```

Open the local URL shown by Vite.

On Windows, double-click `start-printpulse.bat` or the PrintPulse desktop shortcut. It starts both services, opens the host browser, and prints the LAN address other computers can use. Keep the server windows open while using PrintPulse.

### Access from up to 10 computers

Connect the host and client computers to the same trusted local network. On each client, open the LAN address printed by the launcher, such as `http://192.168.1.25:5173/`, and sign in with the administrator account. The host computer must stay on with both server windows open.

If Windows Firewall blocks access, allow inbound TCP port `5173` for Private networks on the host. Client computers do not need Python or Node.js installed. The Django API stays on the host and the React server proxies API requests to it.

## Run the connected backend

The Django API uses SQLite for local development. In a second terminal:

```bash
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py seed_demo
python backend/manage.py create_admin --username admin --password admin123
python backend/manage.py runserver 127.0.0.1:8000
```

Keep both servers running:

- React: `http://localhost:5173`
- Django API: `http://127.0.0.1:8000/api/`

To import printers installed on the Windows machine through Windows Spooler:

```bash
python backend/manage.py sync_spooler
```

Sign in with the administrator credentials created by `create_admin`. The React dashboard loads records from Django. The Add Printer form registers a printer profile; install the printer in Windows and run printer sync to discover it from Windows Spooler.

The Reports page and dashboard Export Report button download a formatted PDF report from Django. It includes summary metrics, paper usage by size, printer inventory, print job history, and error history.

## API routes

- `GET /api/dashboard/`
- `GET /api/printers/`
- `POST /api/printers/` (admin manual registration)
- `POST /api/printers/sync/` (Windows Spooler discovery)
- `GET /api/print-jobs/`
- `GET /api/paper-usage/`
- `GET /api/alerts/`
- `GET /api/reports/summary/`
- `GET /api/reports/export/` (PDF download)

Administrator sign-in uses Django sessions. Local development uses SQLite; Windows Spooler discovery requires `pywin32` and printers installed in Windows. Backend setup installs the PDF library with `python -m pip install -r backend/requirements.txt`.

## Deploy to Render

The root `render.yaml` defines a native Python web service and a private PostgreSQL database in Singapore. Render builds the React frontend, serves it from Django alongside the API, runs migrations before deploy, and provides HTTPS. Docker is not required.

1. Push this project, including `render.yaml`, to a GitHub, GitLab, or Bitbucket repository connected to your Render account.
2. In Render, create a new Blueprint and select that repository. Review the proposed services and costs before applying them.
3. After the first deploy is live, open the web service Shell and run `cd backend && python manage.py createsuperuser` to create the first sign-in.
4. Open the service URL, sign in, and add or sync the printer inventory.

The Blueprint currently uses Render's free web and Postgres plans for a no-card demo. The first administrator is created automatically with a generated password; retrieve `PRINTPULSE_INITIAL_ADMIN_PASSWORD` from the web service's Environment page after deployment and keep it private. Free web services spin down after inactivity, and free Postgres expires after 30 days, so export the database before then or the recorded inventory may be lost.

The new cloud database starts empty; the local SQLite database is not copied automatically. Printer discovery uses Windows Spooler, so it must run on a Windows computer that can see the office printers; the cloud web server cannot discover office printers by itself. The current project does not yet include an office agent that continuously sends every print job to the cloud, so deployment enables remote viewing of records stored in the cloud but does not by itself guarantee live print transaction collection.
