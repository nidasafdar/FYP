const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

function normalizeSource(source) {
  return {
    id: source.id,
    title: source.title || '',
    description: source.description || '',
    mode: source.mode || source.source_type || 'generate',
    streamUrl: source.streamUrl || source.stream_url || '',
    camera_id: source.camera_id || '',
    created_at: source.created_at,
    updated_at: source.updated_at,
    worker_alive: Boolean(source.worker_alive),
    worker_status: source.worker_status || '',
    last_frame_at: source.last_frame_at || '',
    last_error: source.last_error || '',
  }
}

async function parseResponse(res) {
  const data = await res.json().catch(() => null)

  if (!res.ok) {
    const message = data?.detail || 'Request failed'
    throw new Error(Array.isArray(message) ? message.map((item) => item.msg).join(', ') : message)
  }

  return data
}

export async function fetchSources() {
  const res = await fetch(`${API_BASE}/sources`)
  const data = await parseResponse(res)
  return Array.isArray(data) ? data.map(normalizeSource) : []
}

export async function createSource(source) {
  const res = await fetch(`${API_BASE}/sources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: source.title.trim(),
      description: source.description.trim(),
      mode: source.mode,
      streamUrl: source.mode === 'stream' ? source.streamUrl.trim() : '',
    }),
  })
  const data = await parseResponse(res)
  return normalizeSource(data.source)
}

export async function fetchDashboardData(cameraId, sourceMode = 'generate') {
  const analyticsMode = sourceMode === 'stream' || sourceMode === 'live' ? 'live' : 'simulation'
  const params = new URLSearchParams({
    camera: cameraId,
    mode: analyticsMode,
  })
  const res = await fetch(`${API_BASE}/dashboard?${params}`)
  return parseResponse(res)
}
