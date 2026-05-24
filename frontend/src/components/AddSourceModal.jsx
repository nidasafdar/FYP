import React from 'react'
import Icon from './Icon'

const defaultForm = {
  title: '',
  description: '',
  mode: 'generate',
  streamUrl: '',
}

export default function AddSourceModal({ onClose, onConfirm, isSaving, serverError }) {
  const [form, setForm] = React.useState(defaultForm)
  const [errors, setErrors] = React.useState({})

  React.useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  function updateField(field, value) {
    setForm((currentForm) => ({ ...currentForm, [field]: value }))
    setErrors((currentErrors) => ({ ...currentErrors, [field]: '' }))
  }

  function toggleGenerateMode() {
    setForm((currentForm) => ({
      ...currentForm,
      mode: currentForm.mode === 'generate' ? 'stream' : 'generate',
    }))
    setErrors((currentErrors) => ({ ...currentErrors, streamUrl: '' }))
  }

  function validateForm() {
    const nextErrors = {}

    if (!form.title.trim()) {
      nextErrors.title = 'Title is required.'
    }

    if (!form.description.trim()) {
      nextErrors.description = 'Description is required.'
    }

    if (form.mode === 'stream') {
      if (!form.streamUrl.trim()) {
        nextErrors.streamUrl = 'Stream URL is required.'
      } else {
        try {
          const url = new URL(form.streamUrl)
          const validProtocol = ['http:', 'https:', 'rtsp:'].includes(url.protocol)

          if (!validProtocol) {
            nextErrors.streamUrl = 'Use a valid http, https, or rtsp URL.'
          }
        } catch {
          nextErrors.streamUrl = 'Enter a valid stream URL.'
        }
      }
    }

    return nextErrors
  }

  function handleSubmit(event) {
    event.preventDefault()

    const nextErrors = validateForm()
    setErrors(nextErrors)

    if (Object.keys(nextErrors).length > 0) {
      return
    }

    onConfirm(form)
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <form
        className="add-source-dialog"
        aria-label="Add source"
        onSubmit={handleSubmit}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-header">
          <h2>Add Source</h2>
          <button
            className="dialog-close"
            type="button"
            aria-label="Close"
            onClick={onClose}
            disabled={isSaving}
          >
            <Icon name="close" />
          </button>
        </div>

        {serverError && <p className="server-error">{serverError}</p>}

        <input
          className={errors.title ? 'dialog-input field-error' : 'dialog-input'}
          type="text"
          placeholder="title"
          value={form.title}
          onChange={(event) => updateField('title', event.target.value)}
          autoFocus
          aria-invalid={Boolean(errors.title)}
          aria-describedby={errors.title ? 'title-error' : undefined}
        />
        {errors.title && <p className="error-message" id="title-error">{errors.title}</p>}

        <textarea
          className={errors.description ? 'dialog-textarea field-error' : 'dialog-textarea'}
          placeholder="description"
          value={form.description}
          onChange={(event) => updateField('description', event.target.value)}
          aria-invalid={Boolean(errors.description)}
          aria-describedby={errors.description ? 'description-error' : undefined}
        />
        {errors.description && (
          <p className="error-message" id="description-error">{errors.description}</p>
        )}

        <div className="stream-url-field">
          <div className="stream-url-header">
            <label htmlFor="stream-url">Stream URL</label>
            <button
              type="button"
              className={form.mode === 'generate' ? 'generate-toggle active' : 'generate-toggle'}
              aria-pressed={form.mode === 'generate'}
              onClick={toggleGenerateMode}
            >
              <span className="generate-toggle-track" aria-hidden="true">
                <span className="generate-toggle-thumb" />
              </span>
              <span>Generate Data</span>
            </button>
          </div>
          <input
            id="stream-url"
            className={errors.streamUrl ? 'dialog-input field-error' : 'dialog-input'}
            type="url"
            placeholder="stream url"
            value={form.streamUrl}
            onChange={(event) => updateField('streamUrl', event.target.value)}
            disabled={form.mode === 'generate'}
            aria-invalid={Boolean(errors.streamUrl)}
            aria-describedby={errors.streamUrl ? 'stream-url-error' : undefined}
          />
        </div>
        {form.mode === 'stream' && errors.streamUrl && (
          <p className="error-message" id="stream-url-error">{errors.streamUrl}</p>
        )}

        <div className="dialog-actions">
          <button className="confirm-source" type="submit" disabled={isSaving}>
            <Icon name="check" />
            <span>{isSaving ? 'Saving...' : 'Confirm'}</span>
          </button>
        </div>
      </form>
    </div>
  )
}
