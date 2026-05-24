import React from 'react'
import ReactECharts from 'echarts-for-react'
import Icon from './Icon'
import SourceInfoModal from './SourceInfoModal'
import { fetchDashboardData } from '../services/sourcesApi'

function formatNumber(value) {
  return new Intl.NumberFormat('en').format(Number(value) || 0)
}

function formatTrendLabel(direction, change) {
  const prefix = direction === 'up' ? 'Up' : direction === 'down' ? 'Down' : 'Same'
  return `${prefix} ${Math.abs(Number(change) || 0)}%`
}

function congestionClass(status) {
  if (status === 'HIGH') return 'high'
  if (status === 'MEDIUM') return 'medium'
  return 'low'
}

export default function Dashboard({ sources, selectedSource }) {
  const currentSource = sources.find((source) => source.id === selectedSource)
  const cameraNameById = React.useMemo(() => {
    return sources.reduce((lookup, source) => {
      if (source.camera_id) {
        lookup[source.camera_id] = source.title || source.camera_id
      }
      return lookup
    }, {})
  }, [sources])
  const [isInfoOpen, setIsInfoOpen] = React.useState(false)
  const [dashboardData, setDashboardData] = React.useState(null)
  const [loadedCameraId, setLoadedCameraId] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [isSourceLoading, setIsSourceLoading] = React.useState(false)
  const [error, setError] = React.useState(null)
  const [failedCameraId, setFailedCameraId] = React.useState('')
  const currentCameraId = currentSource?.camera_id || ''
  const hasCurrentDashboardData = Boolean(dashboardData && loadedCameraId === currentCameraId)
  const hasCurrentError = Boolean(error && failedCameraId === currentCameraId)
  const showDashboardLoading = Boolean(currentCameraId && !hasCurrentDashboardData && !hasCurrentError)

  React.useEffect(() => {
    if (!currentCameraId) {
      setDashboardData(null)
      setLoadedCameraId('')
      setLoading(false)
      setIsSourceLoading(false)
      setError(null)
      setFailedCameraId('')
      return
    }

    let isActive = true

    setDashboardData(null)
    setLoadedCameraId('')
    setError(null)
    setFailedCameraId('')
    setIsSourceLoading(true)

    const fetchData = async (isInitialLoad = false) => {
      try {
        setLoading(true)
        const data = await fetchDashboardData(currentCameraId, currentSource?.mode)
        if (!isActive) return
        setDashboardData(data)
        setLoadedCameraId(currentCameraId)
        setError(null)
        setFailedCameraId('')
      } catch (err) {
        if (!isActive) return
        console.error('Failed to fetch dashboard data:', err)
        setError(err.message)
        setFailedCameraId(currentCameraId)
      } finally {
        if (isActive) {
          setLoading(false)
          if (isInitialLoad) setIsSourceLoading(false)
        }
      }
    }

    fetchData(true)
    const interval = setInterval(fetchData, 10000)

    return () => {
      isActive = false
      clearInterval(interval)
    }
  }, [currentCameraId, currentSource?.mode])

  const liveTrend = Array.isArray(dashboardData?.live_trend) ? dashboardData.live_trend : []
  const trendLabels = liveTrend.map((point) => Array.isArray(point) ? point[0] : '')
  const trendValues = liveTrend.map((point) => Array.isArray(point) ? Number(point[1]) || 0 : 0)
  const hasTrendData = hasCurrentDashboardData && trendValues.length > 0
  const flow = dashboardData?.flow || {}
  const rushAlert = dashboardData?.rush_alert || {}
  const dailySummary = dashboardData?.daily_summary || {}
  const peakHours = Array.isArray(dashboardData?.peak_hours) ? dashboardData.peak_hours : []
  const gateComparison = Array.isArray(dashboardData?.gate_comparison) ? dashboardData.gate_comparison : []
  const congestion = Array.isArray(dashboardData?.congestion) ? dashboardData.congestion : []
  const weekOverWeek = dashboardData?.week_over_week || {}
  const waitMetric = dashboardData?.average_wait_time || dashboardData?.metric_availability?.average_wait_time
  const getCameraName = (cameraId) => cameraNameById[cameraId] || cameraId

  const emptyMetricState = currentCameraId ? 'Loading' : 'No source'
  const displayMetrics = hasCurrentDashboardData
    ? [
        { label: 'Current Occupancy', value: dashboardData.occupancy ?? 0, delta: dashboardData.occupancy_details?.scope || 'gate' },
        { label: 'Incoming', value: dashboardData.entries ?? 0, delta: `${flow.incoming_percent ?? 0}% of flow` },
        { label: 'Outgoing', value: dashboardData.exits ?? 0, delta: `${flow.outgoing_percent ?? 0}% of flow` },
        { label: 'Rush Status', value: rushAlert.status || 'NORMAL', delta: `${rushAlert.window_minutes || 10} min window` },
      ]
    : [
        { label: 'Current Occupancy', value: 0, delta: emptyMetricState },
        { label: 'Incoming', value: 0, delta: emptyMetricState },
        { label: 'Outgoing', value: 0, delta: emptyMetricState },
        { label: 'Rush Status', value: 'N/A', delta: emptyMetricState },
      ]

  const occupancyTrendOption = {
    tooltip: { trigger: 'axis' },
    grid: { top: 28, right: 24, bottom: 32, left: 42 },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: trendLabels,
      axisLine: { lineStyle: { color: '#d9e1ea' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#edf2f7' } },
      axisLabel: { color: '#667085' },
    },
    series: [
      {
        name: 'Occupancy',
        type: 'line',
        smooth: true,
        data: trendValues,
        symbolSize: 7,
        lineStyle: { width: 4, color: '#2563eb' },
        itemStyle: { color: '#2563eb' },
        areaStyle: { color: 'rgba(37, 99, 235, 0.12)' },
      },
    ],
  }

  const gateComparisonOption = {
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { top: 24, right: 24, bottom: 36, left: 54 },
    xAxis: {
      type: 'category',
      data: gateComparison.map((gate) => getCameraName(gate.camera)),
      axisTick: { show: false },
      axisLabel: { color: '#667085' },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#edf2f7' } },
      axisLabel: { color: '#667085' },
    },
    series: [
      {
        name: 'Traffic',
        type: 'bar',
        data: gateComparison.map((gate) => gate.traffic),
        itemStyle: { color: '#0f766e', borderRadius: [6, 6, 0, 0] },
        barMaxWidth: 48,
      },
    ],
  }

  return (
    <main className="dashboard">
      <header className="topbar">
        <div>
          <h2>
            {currentSource?.title || 'Camera'}
            <button
              className="source-info-button"
              type="button"
              aria-label="Show source details"
              onClick={() => setIsInfoOpen(true)}
            >
              <Icon name="info" size={20} />
            </button>
          </h2>
          <p>{currentSource ? `${currentSource.title} overview` : 'No source selected'}</p>
        </div>
        <div className="live-pill">
          <Icon name="activity" />
          <span>{loading ? 'Updating...' : 'Live monitoring'}</span>
        </div>
      </header>

      <section className="metrics" aria-label="Camera metrics">
        {displayMetrics.map((metric) => (
          <article className="metric-card" key={metric.label}>
            <p>{metric.label}</p>
            <strong>{typeof metric.value === 'number' ? formatNumber(metric.value) : metric.value}</strong>
            <span>{metric.delta}</span>
          </article>
        ))}
      </section>

      <section className="dashboard-grid" aria-label="Operational metrics">
        <article className="flow-panel">
          <div className="panel-heading">
            <h3>Incoming vs Outgoing Flow</h3>
            <span>{formatNumber(flow.total)} total movements</span>
          </div>
          <div className="flow-bars">
            <div>
              <div className="flow-label">
                <span>Incoming</span>
                <strong>{flow.incoming_percent ?? 0}%</strong>
              </div>
              <div className="meter"><span style={{ width: `${flow.incoming_percent ?? 0}%` }} /></div>
            </div>
            <div>
              <div className="flow-label">
                <span>Outgoing</span>
                <strong>{flow.outgoing_percent ?? 0}%</strong>
              </div>
              <div className="meter outgoing"><span style={{ width: `${flow.outgoing_percent ?? 0}%` }} /></div>
            </div>
          </div>
        </article>

        <article className={rushAlert.active ? 'rush-panel active' : 'rush-panel'}>
          <div className="panel-heading">
            <h3>Rush Alert</h3>
            <span>{rushAlert.status || 'NORMAL'}</span>
          </div>
          <strong>{formatNumber(rushAlert.current)} people</strong>
          <p>{rushAlert.ratio ? `${rushAlert.ratio}x average in the last ${rushAlert.window_minutes} minutes` : 'Waiting for enough movement history'}</p>
        </article>

        <article className="peak-panel">
          <div className="panel-heading">
            <h3>Peak Hours Today</h3>
            <span>Top traffic slots</span>
          </div>
          <div className="peak-list">
            {peakHours.length > 0 ? peakHours.map((slot, index) => (
              <div className="peak-row" key={`${slot.time}-${index}`}>
                <span>{slot.time}</span>
                <strong>{formatNumber(slot.count)} people</strong>
              </div>
            )) : (
              <div className="empty-inline">No peak data yet</div>
            )}
          </div>
        </article>
      </section>

      <section className="chart-layout">
        <article className="chart-panel">
          <div className="panel-heading">
            <h3>Hourly Trend Graph</h3>
            <span>Live occupancy</span>
          </div>
          {hasTrendData ? (
            <ReactECharts option={occupancyTrendOption} style={{ height: '100%', minHeight: 260 }} />
          ) : (
            <div className="chart-empty-state">No occupancy trend data yet</div>
          )}
        </article>

        <article className="chart-panel">
          <div className="panel-heading">
            <h3>Gate Comparison</h3>
            <span>Traffic share</span>
          </div>
          {gateComparison.length > 0 ? (
            <ReactECharts option={gateComparisonOption} style={{ height: '100%', minHeight: 260 }} />
          ) : (
            <div className="chart-empty-state">No gate comparison data yet</div>
          )}
        </article>
      </section>

      <section className="status-grid" aria-label="Summary metrics">
        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Daily Traffic Summary</h3>
            <span>{dailySummary.date || 'Today'}</span>
          </div>
          <dl className="summary-list">
            <div><dt>Total entries</dt><dd>{formatNumber(dailySummary.total_entries)}</dd></div>
            <div><dt>Total exits</dt><dd>{formatNumber(dailySummary.total_exits)}</dd></div>
            <div><dt>Peak count</dt><dd>{formatNumber(dailySummary.peak_count)}</dd></div>
            <div><dt>Rush events</dt><dd>{formatNumber(dailySummary.rush_events)}</dd></div>
          </dl>
        </article>

        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Congestion Level</h3>
            <span>Current vs historical max</span>
          </div>
          <div className="congestion-list">
            {congestion.length > 0 ? congestion.map((gate) => (
              <div className="congestion-row" key={gate.camera}>
                <span className={`status-dot ${congestionClass(gate.status)}`} />
                <span>{gate.camera}</span>
                <strong>{gate.status} ({gate.percent}%)</strong>
              </div>
            )) : (
              <div className="empty-inline">No congestion data yet</div>
            )}
          </div>
        </article>

        <article className="summary-panel">
          <div className="panel-heading">
            <h3>Week-over-Week</h3>
            <span>{formatTrendLabel(weekOverWeek.direction, weekOverWeek.change_percent)}</span>
          </div>
          <dl className="summary-list">
            <div><dt>This week</dt><dd>{formatNumber(weekOverWeek.current_total)}</dd></div>
            <div><dt>Last week</dt><dd>{formatNumber(weekOverWeek.previous_total)}</dd></div>
            <div><dt>Change</dt><dd>{formatTrendLabel(weekOverWeek.direction, weekOverWeek.change_percent)}</dd></div>
          </dl>
        </article>

        <article className="summary-panel muted">
          <div className="panel-heading">
            <h3>Average Crossing Time</h3>
            <span>{waitMetric?.label || 'Unavailable'}</span>
          </div>
          <p>{waitMetric?.reason || 'Requires track lifecycle timestamps before this metric can be calculated.'}</p>
        </article>
      </section>

      {isInfoOpen && (
        <SourceInfoModal
          source={currentSource}
          onClose={() => setIsInfoOpen(false)}
        />
      )}
      {showDashboardLoading && (
        <div className='dashboard-loading-overlay' role='status' aria-live='polite'>
          <div className='dashboard-loading-card'>{isSourceLoading ? 'Loading camera data...' : 'Refreshing camera data...'}</div>
        </div>
      )}
      {hasCurrentError && (
        <div className="dashboard-error">
          Error: {error}
        </div>
      )}
    </main>
  )
}
