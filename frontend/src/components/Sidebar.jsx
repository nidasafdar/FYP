import Icon from './Icon'

export default function Sidebar({
  sources,
  selectedSource,
  onSelectSource,
  onAddSource,
  isLoadingSources,
  sourceLoadError,
  onRetryLoad,
}) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-mark">CA</div>
        <div>
          <h3>Campus Analytics</h3>
          <p>Mobility & occupancy</p>
        </div>
      </div>

      <button className="add-source" type="button" onClick={onAddSource}>
        <Icon name="plus" />
        <span>Add source</span>
      </button>

      <label className="field-label" htmlFor="source-select">Source</label>

      <nav className="source-list" aria-label="Camera sources">
        {isLoadingSources && <p className="source-state">Loading sources...</p>}
        {!isLoadingSources && sourceLoadError && (
          <div className="source-state error">
            <p>{sourceLoadError}</p>
            <button type="button" onClick={onRetryLoad}>
              <Icon name="refresh" />
              <span>Retry</span>
            </button>
          </div>
        )}
        {!isLoadingSources && !sourceLoadError && sources.length === 0 && (
          <p className="source-state">No sources in the database yet.</p>
        )}
        {sources.map((source) => (
          <button
            key={source.id}
            type="button"
            className={source.id === selectedSource ? 'source-item active' : 'source-item'}
            onClick={() => onSelectSource(source.id)}
          >
            <Icon name="camera" />
            <span>{source.title}</span>
          </button>
        ))}
      </nav>

      <button className="about-button" type="button">
        <Icon name="info" />
        <span>About</span>
      </button>
    </aside>
  )
}
