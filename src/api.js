const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

async function csrfHeaders() {
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: 'include' })
  if (!response.ok) throw new Error('Could not initialize secure session')
  const { csrfToken } = await response.json()
  return { 'X-CSRFToken': csrfToken }
}

async function request(path) {
  const response = await fetch(`${API_BASE_URL}${path}`, { credentials: 'include' })
  if (!response.ok) {
    throw new Error(`PrintPulse API returned ${response.status}`)
  }
  return response.json()
}

export function getDashboard() {
  return request('/dashboard/')
}

export function getPrinters() {
  return request('/printers/')
}

export function createPrinter(printer) {
  return csrfHeaders().then((csrf) => fetch(`${API_BASE_URL}/printers/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...csrf },
    body: JSON.stringify(printer),
  })).then(async (response) => {
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not add printer')
    return data
  })
}

export function getPrintJobs(query = '') {
  return request(`/print-jobs/${query ? `?q=${encodeURIComponent(query)}` : ''}`)
}

export function getPaperUsage() {
  return request('/paper-usage/')
}

export function getReportSummary() {
  return request('/reports/summary/')
}

export async function downloadReport({ startDate = '', endDate = '' } = {}) {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  const query = params.toString()
  const response = await fetch(`${API_BASE_URL}/reports/export/${query ? `?${query}` : ''}`, { credentials: 'include' })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(data.detail || 'Report download failed')
  }
  return response.blob()
}

export function loginAdmin(username, password) {
  return csrfHeaders().then((csrf) => fetch(`${API_BASE_URL}/auth/login/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...csrf },
    body: JSON.stringify({ username, password }),
  })).then(async (response) => {
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Login failed')
    return data
  })
}

export function getCurrentUser() {
  return request('/auth/me/')
}

export function updateCurrentUser(profile) {
  return csrfHeaders().then((csrf) => fetch(`${API_BASE_URL}/auth/profile/`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...csrf },
    body: JSON.stringify(profile),
  })).then(async (response) => {
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Could not update profile')
    return data.user
  })
}

export function logoutAdmin() {
  return csrfHeaders().then((csrf) => fetch(`${API_BASE_URL}/auth/logout/`, {
    method: 'POST', credentials: 'include', headers: csrf,
  }))
}

export function syncPrinters() {
  return csrfHeaders().then((csrf) => fetch(`${API_BASE_URL}/printers/sync/`, {
    method: 'POST', credentials: 'include', headers: csrf,
  })).then(async (response) => {
    const data = await response.json()
    if (!response.ok) throw new Error(data.detail || 'Printer sync failed')
    return data
  })
}
