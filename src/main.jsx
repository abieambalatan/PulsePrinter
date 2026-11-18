import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'
import { downloadReport, getCurrentUser, getDashboard, getPaperUsage, getPrintJobs, getReportSummary, loginAdmin, logoutAdmin, syncPrinters, createPrinter, updateCurrentUser } from './api'

const icons = {
  grid: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  printer: <><path d="M6 9V3h12v6" /><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" /><path d="M6 14h12v7H6z" /><path d="M18 12h.01" /></>,
  file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h6" /></>,
  paper: <><path d="M6 2h12v20H6z" /><path d="M9 6h6M9 10h6M9 14h4" /></>,
  chart: <><path d="M3 3v18h18" /><path d="m7 16 3-4 3 2 5-7" /></>,
  settings: <><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z" /><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-1.94 1.94-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V20h-2.75v-.09a1.7 1.7 0 0 0-1.03-1.56 1.7 1.7 0 0 0-1.88.34l-.06.06-1.94-1.94.06-.06A1.7 1.7 0 0 0 7.6 15a1.7 1.7 0 0 0-1.56-1.03H5.95v-2.75h.09A1.7 1.7 0 0 0 7.6 10a1.7 1.7 0 0 0-.34-1.88L7.2 8.06 9.14 6.12l.06.06a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 12.11 5V4.9h2.75V5a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.88-.34l.06-.06 1.94 1.94-.06.06A1.7 1.7 0 0 0 19.4 10c.25.62.85 1.03 1.52 1.03H21v2.75h-.08c-.67 0-1.27.4-1.52 1.03z" /></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-4-4" /></>,
  chevron: <path d="m9 18 6-6-6-6" />,
  download: <><path d="M12 3v12M7 10l5 5 5-5M5 21h14" /></>,
  refresh: <><path d="M20 11a8.1 8.1 0 0 0-14.8-4L3 10" /><path d="M3 4v6h6M4 13a8.1 8.1 0 0 0 14.8 4L21 14" /><path d="M21 20v-6h-6" /></>,
  more: <><circle cx="5" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="19" cy="12" r="1" fill="currentColor" stroke="none" /></>,
  warning: <><path d="m12 3 10 18H2L12 3z" /><path d="M12 9v4M12 17h.01" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
}

function Icon({ name, size = 18, className = '' }) {
  return <svg className={`icon ${className}`} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{icons[name]}</svg>
}

const navItems = [
  { label: 'Dashboard', icon: 'grid' },
  { label: 'Printers', icon: 'printer' },
  { label: 'Print Jobs', icon: 'file' },
  { label: 'Paper Usage', icon: 'paper' },
  { label: 'Reports', icon: 'chart' },
]

function App() {
  const [active, setActive] = useState('Dashboard')
  const [range, setRange] = useState('Last 7 days')
  const [query, setQuery] = useState('')
  const [lastUpdated, setLastUpdated] = useState('Just now')
  const [showNotifications, setShowNotifications] = useState(false)
  const [dashboardData, setDashboardData] = useState(null)
  const [apiConnected, setApiConnected] = useState(false)
  const [user, setUser] = useState(null)
  const [authChecked, setAuthChecked] = useState(false)

  const loadDashboard = async () => {
    try {
      const data = await getDashboard()
      setDashboardData(data)
      setApiConnected(true)
      setLastUpdated('Updated just now')
    } catch {
      setApiConnected(false)
      setLastUpdated('Demo data')
    }
  }

  useEffect(() => {
    getCurrentUser()
      .then((data) => {
        if (data.authenticated) setUser(data.user)
      })
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true))
  }, [])

  useEffect(() => {
    if (user) loadDashboard()
  }, [user])

  const refresh = () => loadDashboard()
  const handleProfileUpdate = async (profile) => {
    const updatedUser = await updateCurrentUser(profile)
    setUser(updatedUser)
    return updatedUser
  }
  const handleReportDownload = async (startDate = '', endDate = '') => {
    try {
      const blob = await downloadReport({ startDate, endDate })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = startDate || endDate
        ? `printpulse-report-${startDate || 'beginning'}-to-${endDate || 'present'}.pdf`
        : `printpulse-report-${new Date().toISOString().slice(0, 10)}.pdf`
      link.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      window.alert(error.message)
    }
  }
  const dashboardPrinters = dashboardData?.printers || []

  if (!authChecked) return <LoadingScreen />
  if (!user) return <LoginScreen onLogin={setUser} />

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Icon name="printer" size={21} /></div>
          <div><strong>Print<span>Pulse</span></strong><small>MONITORING SYSTEM</small></div>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <div className="workspace-switcher"><div className="workspace-icon">AO</div><div><b>Admin Office</b><small>Central Branch</small></div><Icon name="chevron" size={15} /></div>
        <nav className="main-nav">
          <div className="nav-caption">MAIN MENU</div>
          {navItems.map((item) => <button key={item.label} className={`nav-item ${active === item.label ? 'active' : ''}`} onClick={() => setActive(item.label)}><Icon name={item.icon} /><span>{item.label}</span>{item.badge && <em>{item.badge}</em>}</button>)}
          <div className="nav-caption utility-caption">SYSTEM</div>
          <button className={`nav-item ${active === 'Settings' ? 'active' : ''}`} onClick={() => setActive('Settings')}><Icon name="settings" /><span>Settings</span></button>
        </nav>
        <div className="sidebar-footer"><div className="help-card"><div className="help-icon">?</div><div><b>Need help?</b><span>Contact support</span></div><Icon name="chevron" size={15} /></div><div className="user-profile"><div className="avatar avatar-teal">{user.username.slice(0, 2).toUpperCase()}</div><div><b>{user.name}</b><span>Administrator</span></div><button className="logout-button" onClick={() => logoutAdmin().finally(() => setUser(null))}>Log out</button></div></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><div className="breadcrumbs"><span>Workspace</span><Icon name="chevron" size={14} /><b>{active}</b></div><div className="topbar-actions"><div className="search-box"><Icon name="search" size={17} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search anything..." /></div><button className="icon-button notification-button" onClick={() => setShowNotifications(!showNotifications)}><Icon name="bell" size={19} /><i></i></button>{showNotifications && <div className="notification-popover"><b>Notifications</b>{dashboardData?.alerts?.length ? dashboardData.alerts.map((alert) => <p key={alert.id}>{alert.title}: {alert.detail}</p>) : <p>No active notifications.</p>}</div>}<div className="top-avatar avatar-teal">{(user.first_name || user.username).slice(0, 2).toUpperCase()}</div></div></header>
        <div className="page-content">
          <section className="page-heading"><div><div className="eyebrow"><span className="live-dot"></span> SYSTEM OVERVIEW <span className="muted">•</span> {lastUpdated}</div><h1>Good morning, {user.first_name || user.name || user.username} <span>👋</span></h1><p>Here’s what’s happening with your printing environment today.</p></div><div className="heading-actions"><button className="button secondary" onClick={refresh}><Icon name="refresh" size={16} /> Refresh</button><button className="button primary" onClick={() => setActive('Reports')}><Icon name="download" size={16} /> Export report</button></div></section>

          {active !== 'Dashboard' ? <LiveSubPage active={active} query={query} setQuery={setQuery} printers={dashboardPrinters} user={user} apiConnected={apiConnected} onRefresh={refresh} onDownloadReport={handleReportDownload} onUpdateProfile={handleProfileUpdate} /> : <Dashboard range={range} setRange={setRange} dashboardData={dashboardData} />}
        </div>
      </main>
    </div>
  )
}

function LoadingScreen() {
  return <div className="auth-shell"><div className="auth-loading"><div className="brand-mark"><Icon name="printer" size={21} /></div><span>Loading PrintPulse...</span></div></div>
}

function LoginScreen({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const data = await loginAdmin(username, password)
      onLogin(data.user)
    } catch (loginError) {
      setError(loginError.message)
    } finally {
      setSubmitting(false)
    }
  }

  return <div className="auth-shell"><div className="login-card"><div className="login-brand"><div className="brand-mark"><Icon name="printer" size={21} /></div><div><strong>Print<span>Pulse</span></strong><small>MONITORING SYSTEM</small></div></div><div className="login-heading"><span className="eyebrow">ADMIN PORTAL</span><h1>Welcome back</h1><p>Sign in to monitor your printing environment.</p></div><form onSubmit={submit}><label>Username<input value={username} onChange={(event) => setUsername(event.target.value)} placeholder="Enter username" autoComplete="username" required /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter password" autoComplete="current-password" required /></label>{error && <div className="login-error">{error}</div>}<button className="button primary login-button" disabled={submitting}>{submitting ? 'Signing in...' : 'Sign in to dashboard'}</button></form><small className="login-note">Administrator access only</small></div></div>
}

function Dashboard({ range, setRange, dashboardData }) {
  const summary = dashboardData?.summary || {}
  const dashboardJobs = dashboardData?.recent_jobs || []
  const dashboardAlerts = dashboardData?.alerts || []
  const paperRows = dashboardData?.paper_usage || []
  const paperTotal = paperRows.reduce((total, row) => total + row.value, 0)
  const paperColors = ['#4f6cf0', '#8963e8', '#eda15f', '#32a58b']
  let paperOffset = 0
  const paperGradient = paperRows.map((row, index) => {
    const start = paperOffset
    paperOffset += paperTotal ? (row.value / paperTotal) * 100 : 0
    return `${paperColors[index % paperColors.length]} ${start}% ${paperOffset}%`
  }).join(', ')
  return <>
    <section className="stat-grid">
      <StatCard title="Total pages printed" value={(summary.total_pages ?? 0).toLocaleString()} icon="printer" tone="blue" />
      <StatCard title="Paper consumed" value={(summary.paper_consumed ?? 0).toLocaleString()} suffix=" sheets" icon="paper" tone="purple" />
      <StatCard title="Active printers" value={summary.active_printers ?? 0} suffix={` / ${summary.total_printers ?? 0}`} icon="chart" tone="green" />
      <StatCard title="Detected errors" value={summary.detected_errors ?? 0} icon="warning" tone="orange" />
    </section>

    <section className="content-grid top-grid"><div className="card chart-card"><div className="card-header"><div><h2>Printing activity</h2><p>Number of pages printed over time</p></div><select value={range} onChange={(e) => setRange(e.target.value)}><option>Last 7 days</option><option>Last 30 days</option><option>This year</option></select></div><ActivityChart activity={dashboardData?.activity || []} /></div><div className="card paper-card"><div className="card-header"><div><h2>Paper usage</h2><p>Consumption by paper size</p></div><button className="more-button"><Icon name="more" size={18} /></button></div>{paperTotal > 0 ? <div className="donut-wrap"><div className="donut" style={{ background: `conic-gradient(${paperGradient})` }}><div className="donut-hole"><strong>{paperTotal.toLocaleString()}</strong><span>total sheets</span></div></div><div className="legend">{paperRows.map((row, index) => <Legend key={row.label} color={['blue', 'purple', 'orange'][index % 3]} label={row.label} value={row.value.toLocaleString()} percent={`${((row.value / paperTotal) * 100).toFixed(1)}%`} />)}</div></div> : <EmptyState text="No paper usage recorded." />}</div></section>

    <section className="content-grid lower-grid"><div className="card jobs-card"><div className="card-header"><div><h2>Recent print jobs</h2><p>Latest printing activity from all devices</p></div><button className="text-button">View all <Icon name="chevron" size={14} /></button></div>{dashboardJobs.length ? <div className="table-wrap"><table><thead><tr><th>USER</th><th>PRINTER</th><th>PAGES</th><th>PAPER SIZE</th><th>STATUS</th><th>TIME</th></tr></thead><tbody>{dashboardJobs.map((job) => <tr key={job.id}><td><div className="user-cell"><div className={`avatar avatar-${job.color || 'blue'}`}>{job.initials}</div><b>{job.user}</b></div></td><td><div className="printer-cell"><Icon name="printer" size={15} />{job.printer}</div></td><td><b>{job.pages}</b></td><td><span className="paper-pill">{job.paper}</span></td><td><span className={`status ${job.status.toLowerCase()}`}><i></i>{job.status}</span></td><td className="time-cell">{job.time}</td></tr>)}</tbody></table></div> : <EmptyState text="No recent print jobs." />}</div><div className="card alerts-card"><div className="card-header"><div><h2>System alerts</h2><p>Issues that need your attention</p></div><span className="alert-count">{dashboardAlerts.length}</span></div><div className="alert-list">{dashboardAlerts.length ? dashboardAlerts.map((alert) => <Alert key={alert.id} icon={alert.icon} tone={alert.tone} title={alert.title} detail={alert.detail} time={alert.time} />) : <EmptyState text="No active alerts." />}</div><button className="view-alerts">View alert history <Icon name="chevron" size={14} /></button></div></section>
  </>
}

function StatCard({ title, value, suffix, icon, tone }) { return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon name={icon} size={20} /></div><div className="stat-content"><div className="stat-label">{title}<button className="more-button"><Icon name="more" size={15} /></button></div><div className="stat-value">{value}<small>{suffix}</small></div></div></div> }
function Legend({ color, label, value, percent }) { return <div className="legend-row"><span className={`legend-dot ${color}`}></span><span>{label}</span><b>{value}</b><small>{percent}</small></div> }
function Alert({ icon, tone, title, detail, time }) { return <div className="alert-row"><div className={`alert-icon ${tone}`}><Icon name={icon} size={17} /></div><div className="alert-copy"><b>{title}</b><span>{detail}</span></div><small>{time}</small></div> }

function LiveSubPage({ active, query, setQuery, printers: connectedPrinters, user, apiConnected, onRefresh, onDownloadReport, onUpdateProfile }) {
  const [jobRows, setJobRows] = useState([])
  const [paperRows, setPaperRows] = useState([])
  const [report, setReport] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [syncMessage, setSyncMessage] = useState('')
  const [showAddPrinter, setShowAddPrinter] = useState(false)
  const [savingPrinter, setSavingPrinter] = useState(false)
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const pageData = {
    Printers: { title: 'Printers', desc: 'Monitor and manage all connected printers.' },
    'Print Jobs': { title: 'Print jobs', desc: 'Review every printing activity across your workspace.' },
    'Paper Usage': { title: 'Paper usage', desc: 'Track consumption by paper size and printer.' },
    Reports: { title: 'Reports', desc: 'Generate daily and monthly printing reports.' },
    Settings: { title: 'Settings', desc: 'Manage your profile and PrintPulse administration.' },
  }
  const data = pageData[active]

  useEffect(() => {
    if (active === 'Print Jobs') getPrintJobs(query).then((result) => setJobRows(result.results)).catch(() => setJobRows([]))
    if (active === 'Paper Usage') getPaperUsage().then((result) => setPaperRows(result.results)).catch(() => setPaperRows([]))
    if (active === 'Reports') getReportSummary().then(setReport).catch(() => setReport(null))
  }, [active, query])

  const handleSync = async () => {
    setSyncing(true)
    setSyncMessage('')
    try {
      const result = await syncPrinters()
      setSyncMessage(result.synced
        ? `${result.synced} printer(s) recently reported by a Windows monitor.`
        : 'No printers have checked in from a Windows monitor in the last 3 minutes. Make sure the monitor is running on the PC where the printer is installed; the cloud server cannot scan that PC directly.')
      onRefresh()
    } catch (error) {
      setSyncMessage(error.message)
    } finally {
      setSyncing(false)
    }
  }

  const handleAddPrinter = async (event) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    setSavingPrinter(true)
    setSyncMessage('')
    try {
      await createPrinter({
        name: formData.get('name'),
        location: formData.get('location'),
        connection_type: formData.get('connection_type'),
        status: formData.get('status'),
        paper_level: Number(formData.get('paper_level')),
      })
      setShowAddPrinter(false)
      setSyncMessage('Printer added successfully.')
      onRefresh()
    } catch (error) {
      setSyncMessage(error.message)
    } finally {
      setSavingPrinter(false)
    }
  }

  return <div className="subpage">{active !== 'Settings' && <div className="subpage-banner"><div><span className="eyebrow">MANAGEMENT</span><h2>{data.title}</h2><p>{data.desc}</p></div><div className="subpage-actions">{active === 'Printers' && <><button className="button secondary" onClick={handleSync} disabled={syncing}><Icon name="refresh" size={16} /> {syncing ? 'Checking...' : 'Refresh monitor inventory'}</button><button className="button primary" onClick={() => setShowAddPrinter(true)}><Icon name="plus" size={16} /> Add printer</button></>}{active === 'Reports' && <div className="report-date-filter"><label>From<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} /></label><label>To<input type="date" value={endDate} min={startDate || undefined} onChange={(event) => setEndDate(event.target.value)} /></label><button className="button primary" onClick={() => onDownloadReport(startDate, endDate)}><Icon name="download" size={16} /> Download PDF</button></div>}</div></div>}
    {syncMessage && <div className="inline-message">{syncMessage}</div>}
    {active === 'Printers' && <div className="card jam-summary"><div><b>Paper jam history</b><span>Detected incidents per printer</span></div>{connectedPrinters.map((printer) => <div className="jam-count" key={printer.id || printer.name}><span>{printer.name}</span><strong>{printer.paper_jams ?? 0}</strong></div>)}</div>}
    {active === 'Printers' && <div className="printer-cards">{connectedPrinters.map((printer, index) => <div className="card printer-card" key={printer.id || printer.name}><div className="printer-top"><div className={`large-printer-icon ${printer.color || ['blue', 'purple', 'orange'][index % 3]}`}><Icon name="printer" size={25} /></div><button className="more-button"><Icon name="more" /></button></div><h3>{printer.name}</h3><p>{printer.location || 'Windows local printer'}</p><div className="printer-status"><span className={`status ${printer.status.toLowerCase()}`}><i></i>{printer.status}</span><span>{printer.connection_type || 'Windows Spooler'}</span></div><div className="level-row"><span>Paper level</span><b>{printer.level}%</b></div><div className="progress"><span className={printer.level < 20 ? 'low' : ''} style={{ width: `${printer.level}%` }}></span></div><div className="printer-stats"><span><b>{printer.jobs || 0}</b> jobs</span><span><b>{printer.pages || 0}</b> pages</span></div></div>)}</div>}
    {active === 'Print Jobs' && <div className="card data-card"><div className="data-toolbar"><div><h3>Print job history</h3><p>Records captured by the monitoring API</p></div><input className="module-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search user or printer..." /></div><div className="table-wrap"><table><thead><tr><th>USER</th><th>PRINTER</th><th>PAGES</th><th>PAPER</th><th>STATUS</th><th>TIME</th></tr></thead><tbody>{jobRows.map((job, index) => <tr key={job.id}><td><div className="user-cell"><div className={`avatar avatar-${job.color || ['coral', 'blue', 'violet', 'green'][index % 4]}`}>{job.initials}</div><b>{job.user}</b></div></td><td>{job.printer}</td><td><b>{job.pages}</b></td><td><span className="paper-pill">{job.paper}</span></td><td><span className={`status ${job.status.toLowerCase()}`}><i></i>{job.status}</span></td><td className="time-cell">{job.time}</td></tr>)}</tbody></table></div>{!jobRows.length && <EmptyState text="No print jobs found." />}</div>}
    {active === 'Paper Usage' && <div className="usage-grid">{paperRows.map((row, index) => { const total = paperRows.reduce((sum, item) => sum + item.sheets, 0) || 1; const percent = Math.round((row.sheets / total) * 100); return <div className="card usage-card" key={row.paper_size}><div className={`usage-icon ${['blue', 'purple', 'orange'][index % 3]}`}><Icon name="paper" size={20} /></div><span>{row.paper_size === 'Short' ? 'Short / Letter' : row.paper_size === 'Long' ? 'Long / Legal' : row.paper_size}</span><strong>{row.sheets.toLocaleString()}</strong><small>{percent}% of total usage</small><div className="progress"><span className={['blue-progress', 'purple-progress', 'orange-progress'][index % 3]} style={{ width: `${percent}%` }}></span></div></div> })}</div>}
    {active === 'Reports' && <div className="report-grid">{[['Daily pages', report?.daily_pages || 0, 'printer'], ['Monthly pages', report?.monthly_pages || 0, 'chart'], ['Total sheets', report?.total_sheets || 0, 'paper'], ['Printer errors', report?.printer_errors || 0, 'warning']].map(([label, value, icon]) => <div className="card report-card" key={label}><div className="stat-icon blue"><Icon name={icon} size={19} /></div><span>{label}</span><strong>{Number(value).toLocaleString()}</strong><small>Live from Django API</small></div>)}</div>}
    {active === 'Settings' && <ProfileSettings user={user} apiConnected={apiConnected} onSave={onUpdateProfile} />}
    {showAddPrinter && <div className="modal-backdrop" onClick={() => setShowAddPrinter(false)}><form className="printer-modal" onSubmit={handleAddPrinter} onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><span className="eyebrow">PRINTER SETUP</span><h3>Add printer</h3></div><button type="button" className="modal-close" onClick={() => setShowAddPrinter(false)}>×</button></div><label>Printer name<input name="name" placeholder="e.g. Epson L5290" required maxLength="120" /></label><label>Location<input name="location" placeholder="e.g. Finance Office" maxLength="120" /></label><div className="form-columns"><label>Connection<select name="connection_type"><option>Network</option><option>USB</option><option>Windows Spooler</option><option>Manual</option></select></label><label>Initial status<select name="status"><option>Offline</option><option>Online</option><option>Attention</option></select></label></div><label>Paper level (%)<input name="paper_level" type="number" min="0" max="100" defaultValue="0" required /></label><p className="modal-note">Manual entry adds a printer to your inventory. The Windows monitor reports printers installed on its PC automatically.</p>{syncMessage && <div className="login-error">{syncMessage}</div>}<button className="button primary login-button" disabled={savingPrinter}>{savingPrinter ? 'Adding printer...' : 'Save printer'}</button></form></div>}
  </div>
}

function EmptyState({ text }) { return <div className="empty-state"><Icon name="file" size={24} /><span>{text}</span></div> }

function ProfileSettings({ user, apiConnected, onSave }) {
  const [section, setSection] = useState('Profile')
  const [form, setForm] = useState({ username: user.username || '', email: user.email || '', first_name: user.first_name || '', last_name: user.last_name || '' })
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    setForm({ username: user.username || '', email: user.email || '', first_name: user.first_name || '', last_name: user.last_name || '' })
  }, [user])

  const updateField = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  const submit = async (event) => {
    event.preventDefault()
    setSaving(true)
    setMessage('')
    setError('')
    try {
      await onSave(form)
      setMessage('Your profile was updated.')
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  return <div className="settings-page"><div className="settings-intro"><div><span className="eyebrow">PREFERENCES & ACCESS</span><h2>Settings</h2><p>Manage your account details and administrative tools.</p></div><div className="settings-user-chip"><span className="settings-avatar avatar-teal">{user.username.slice(0, 2).toUpperCase()}</span><span><b>{user.name}</b><small>Administrator</small></span></div></div><div className="settings-tabs" role="tablist" aria-label="Settings sections"><button type="button" role="tab" aria-selected={section === 'Profile'} className={section === 'Profile' ? 'active' : ''} onClick={() => setSection('Profile')}>My profile</button><button type="button" role="tab" aria-selected={section === 'Admin Office'} className={section === 'Admin Office' ? 'active' : ''} onClick={() => setSection('Admin Office')}>Admin Office</button></div>{section === 'Profile' ? <div className="settings-layout"><form className="card profile-card" onSubmit={submit}><div className="profile-card-heading"><div className="settings-avatar avatar-teal">{user.username.slice(0, 2).toUpperCase()}</div><div><h3>Administrator profile</h3><p>Edit the information for your signed-in account.</p></div></div><div className="profile-fields"><label>Username<input name="username" value={form.username} onChange={updateField} required maxLength="150" autoComplete="username" /></label><label>Email address<input name="email" type="email" value={form.email} onChange={updateField} maxLength="254" autoComplete="email" /></label><label>First name<input name="first_name" value={form.first_name} onChange={updateField} maxLength="150" autoComplete="given-name" /></label><label>Last name<input name="last_name" value={form.last_name} onChange={updateField} maxLength="150" autoComplete="family-name" /></label></div>{error && <div className="login-error" role="alert">{error}</div>}{message && <div className="profile-success" role="status">{message}</div>}<div className="profile-form-footer"><span>Your account stays private to you.</span><button className="button primary" disabled={saving}>{saving ? 'Saving...' : 'Save changes'}</button></div></form><div className="card settings-connection"><div className="settings-icon"><Icon name="chart" size={18} /></div><div><h3>API connection</h3><p>Dashboard data is loaded from the Django backend.</p></div><span className={`status ${apiConnected ? 'completed' : 'attention'}`}><i></i>{apiConnected ? 'Connected' : 'Offline'}</span></div></div> : <div className="card admin-office-card"><div className="admin-office-info"><div><span className="eyebrow">PRINTPULSE ADMINISTRATION</span><h3>System management</h3><p>Manage user accounts, printers, print jobs, paper usage, and alerts.</p></div><a className="button secondary" href="/admin/" target="_blank" rel="noreferrer">Open full page</a></div><iframe className="admin-office-frame" src="/admin/" title="PrintPulse administration" /></div>}</div>
}

function ActivityChart({ activity }) {
  const maxPages = Math.max(0, ...activity.map((item) => item.pages))
  if (!maxPages) return <EmptyState text="No printing activity recorded." />

  const points = activity.map((item, index) => {
    const x = activity.length === 1 ? 350 : (index / (activity.length - 1)) * 700
    const y = 210 - (item.pages / maxPages) * 180
    return [x, y]
  })
  const line = points.map(([x, y], index) => `${index ? 'L' : 'M'}${x},${y}`).join(' ')
  const area = `${line} L700,230 L0,230 Z`

  return <div className="chart-area"><div className="y-axis"><span>{maxPages.toLocaleString()}</span><span>{Math.round(maxPages * .75).toLocaleString()}</span><span>{Math.round(maxPages * .5).toLocaleString()}</span><span>{Math.round(maxPages * .25).toLocaleString()}</span><span>0</span></div><div className="chart-body"><div className="chart-gridlines"><i></i><i></i><i></i><i></i><i></i></div><svg className="line-chart" viewBox="0 0 700 230" preserveAspectRatio="none"><defs><linearGradient id="areaFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#4767f5" stopOpacity=".22" /><stop offset="100%" stopColor="#4767f5" stopOpacity="0" /></linearGradient></defs><path d={area} fill="url(#areaFill)" /><path d={line} fill="none" stroke="#4767f5" strokeWidth="3" strokeLinecap="round" /></svg><div className="x-axis">{activity.map((item) => <span key={item.day}>{item.day}</span>)}</div></div></div>
}

function SubPage({ active, query, setQuery, printers: connectedPrinters }) { const pageData = { Printers: { title: 'Printers', desc: 'Monitor and manage all connected printers.' }, 'Print Jobs': { title: 'Print jobs', desc: 'Review every printing activity across your workspace.' }, 'Paper Usage': { title: 'Paper usage', desc: 'Track consumption by paper size and printer.' }, Reports: { title: 'Reports', desc: 'Generate daily and monthly printing reports.' }, Settings: { title: 'Settings', desc: 'Configure your workspace and monitoring preferences.' } }; const data = pageData[active]; return <div className="subpage"><div className="subpage-banner"><div><span className="eyebrow">MANAGEMENT</span><h2>{data.title}</h2><p>{data.desc}</p></div><button className="button primary"><Icon name="plus" size={16} /> {active === 'Printers' ? 'Add printer' : 'Create report'}</button></div>{active === 'Printers' ? <div className="printer-cards">{connectedPrinters.map((printer) => <div className="card printer-card" key={printer.name}><div className="printer-top"><div className={`large-printer-icon ${printer.color || 'blue'}`}><Icon name="printer" size={25} /></div><button className="more-button"><Icon name="more" /></button></div><h3>{printer.name}</h3><p>{printer.location}</p><div className="printer-status"><span className={`status ${printer.status.toLowerCase()}`}><i></i>{printer.status}</span><span>Last checked 2 min ago</span></div><div className="level-row"><span>Paper level</span><b>{printer.level}%</b></div><div className="progress"><span className={printer.level < 20 ? 'low' : ''} style={{ width: `${printer.level}%` }}></span></div><div className="printer-stats"><span><b>{printer.jobs}</b> jobs</span><span><b>{printer.pages}</b> pages</span></div></div>)}</div> : <div className="card placeholder-card"><div className="placeholder-icon"><Icon name={active === 'Reports' ? 'chart' : active === 'Paper Usage' ? 'paper' : active === 'Settings' ? 'settings' : 'file'} size={28} /></div><h3>{active} module ready</h3><p>Connect this view to the Django API to load live {active.toLowerCase()} data. The dashboard is already structured for your capstone workflow.</p>{active === 'Print Jobs' && <input className="module-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter jobs..." />}</div>}</div> }

createRoot(document.getElementById('root')).render(<App />)
