import React from 'react'
import Icon from './Icon'

export default function SourceInfoModal({ source, onClose }) {
  React.useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  if (!source) {
    return null
  }

  const sourceType = source.mode === 'stream' ? 'Stream' : 'Generated'
  const streamStatus = source.worker_status || (source.worker_alive ? 'running' : 'stopped')

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="source-info-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-info-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <h2 id="source-info-title">Source Details</h2>
          <button className="dialog-close" type="button" aria-label="Close" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>

        <dl className="source-details">
          <div>
            <dt>Title</dt>
            <dd>{source.title}</dd>
          </div>
          <div>
            <dt>Description</dt>
            <dd>{source.description || 'No description provided.'}</dd>
          </div>
          <div>
            <dt>Source Type</dt>
            <dd>{sourceType}</dd>
          </div>
          {source.mode === 'stream' && (
            <>
              <div>
                <dt>Stream URL</dt>
                <dd>{source.streamUrl || 'No stream URL provided.'}</dd>
              </div>
              <div>
                <dt>Stream Status</dt>
                <dd>{streamStatus}</dd>
              </div>
              <div>
                <dt>Last Frame</dt>
                <dd>{source.last_frame_at || 'No frame received yet.'}</dd>
              </div>
              {source.last_error && (
                <div>
                  <dt>Last Error</dt>
                  <dd>{source.last_error}</dd>
                </div>
              )}
            </>
          )}
        </dl>
      </section>
    </div>
  )
}
