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

Sign in with the administrator credentials created by `create_admin`. The React dashboard loads records from Django. The Add Printer form registers a printer profile. Local Windows development can use `sync_spooler`; on Render, the Windows monitor reports installed printers because the cloud server cannot scan the office PC.

The Reports page and dashboard Export Report button download a formatted PDF report from Django. It includes summary metrics, paper usage by size, printer inventory, print job history, and error history.

## API routes

- `GET /api/dashboard/`
- `GET /api/printers/`
- `POST /api/printers/` (admin manual registration)
- `POST /api/printers/sync/` (recent Windows monitor inventory)
- `POST /api/printers/agent-sync/` (agent-authenticated local inventory upload)
- `GET /api/print-jobs/`
- `GET /api/paper-usage/`
- `GET /api/alerts/`
- `GET /api/reports/summary/`
- `GET /api/reports/export/` (PDF download)

Administrator sign-in uses Django sessions. Local development uses SQLite; the `sync_spooler` management command requires `pywin32` and printers installed in Windows. Backend setup installs the PDF library with `python -m pip install -r backend/requirements.txt`.

## Deploy to Render

The root `render.yaml` defines a native Python web service and a private PostgreSQL database in Singapore. Render builds the React frontend, serves it from Django alongside the API, runs migrations before deploy, and provides HTTPS. Docker is not required.

1. Push this project, including `render.yaml`, to the Git repository connected to your Render account.
2. In Render, create a Blueprint for that repository and review the proposed services and costs before applying them.
3. Open the service URL and sign in as `admin`. Retrieve the generated `PRINTPULSE_INITIAL_ADMIN_PASSWORD` from the web service's Environment page.
4. For a USB printer, install its Windows driver on the PC it is connected to, then set up the local monitor below. You can also use **Add printer** to enter inventory before its first print job is captured.

### Connect a USB printer to the cloud dashboard

The USB printer must stay connected to a Windows PC that is powered on, awake, signed in, and connected to the internet. Jobs must be printed through that PC's Windows printer queue. The Windows monitor sends completed job details to Render over HTTPS; no router port forwarding is needed.

1. After the latest Render deploy is live, open the web service's **Environment** page and copy `PRINTPULSE_AGENT_TOKEN_V2`. Keep this secret private.
2. On the USB-connected PC, get this repository from GitHub and open **PowerShell as Administrator** using the same Windows account that will run the monitor.
3. From the repository folder, run:

   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File .\windows-agent\Setup-PrintPulseAgent.ps1
   ```

4. Paste the token when prompted. The setup enables the Windows PrintService Operational log, stores the token protected for that Windows account, starts the monitor, and configures it to start again when you sign in.
5. Print a test page to the USB printer. The completed job should appear in **Print Jobs** on the Render site.

The Windows monitor reports installed printer names and locations to PrintPulse about once a minute, so they appear in the inventory without waiting for a print job. The **Refresh monitor inventory** button shows printers that checked in during the last three minutes. The monitor starts from setup time and does not import older print history.

The monitor uploads the Windows username, printer name, page count, computer name, and print time. It does not upload document titles or document contents. To identify paper size, it briefly polls Windows' active print-job data and associates a reported size with the completed job; some drivers omit that value and very fast jobs may leave the queue before a poll, so those jobs remain **Unknown**. Toner and paper-level readings are not available from these generic events. Jobs sent directly to another printer or through a different PC are not captured.

The Blueprint currently uses Render's free web and Postgres plans for a no-card demo. The first administrator is created automatically with a generated password; retrieve `PRINTPULSE_INITIAL_ADMIN_PASSWORD` from the web service's Environment page after deployment and keep it private. Free web services spin down after inactivity, and free Postgres expires after 30 days, so export the database before then or the recorded inventory may be lost.

The new cloud database starts empty; the local SQLite database is not copied automatically. Windows printer discovery and print-job monitoring run on the office PC because the cloud server cannot access USB devices or the office network directly.

for client
//Set-Location "C:\Design and Development of a Universal Printer Monitoring and Paper Usage Tracking System"
git pull origin main
powershell.exe -ExecutionPolicy Bypass -File ".\windows-agent\Setup-PrintPulseAgent.ps1"//
