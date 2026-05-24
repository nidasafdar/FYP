import React from 'react'
import AddSourceModal from './components/AddSourceModal'
import Dashboard from './components/Dashboard'
import Sidebar from './components/Sidebar'
import { createSource, fetchSources } from './services/sourcesApi'

export default function App() {
  const [sources, setSources] = React.useState([])
  const [selectedSource, setSelectedSource] = React.useState('')
  const [isAddSourceOpen, setIsAddSourceOpen] = React.useState(false)
  const [isLoadingSources, setIsLoadingSources] = React.useState(true)
  const [sourceLoadError, setSourceLoadError] = React.useState('')
  const [isSavingSource, setIsSavingSource] = React.useState(false)
  const [sourceSaveError, setSourceSaveError] = React.useState('')

  React.useEffect(() => {
    loadSources()
  }, [])

  async function loadSources() {
    setIsLoadingSources(true)
    setSourceLoadError('')

    try {
      const dbSources = await fetchSources()
      setSources(dbSources)
      setSelectedSource((currentSelected) => {
        if (dbSources.some((source) => source.id === currentSelected)) {
          return currentSelected
        }

        return dbSources[0]?.id || ''
      })
    } catch (error) {
      setSourceLoadError(error.message)
    } finally {
      setIsLoadingSources(false)
    }
  }

  async function handleAddSource(source) {
    setIsSavingSource(true)
    setSourceSaveError('')

    try {
      const createdSource = await createSource(source)
      setSources((currentSources) => [...currentSources, createdSource])
      setSelectedSource(createdSource.id)
      setIsAddSourceOpen(false)
    } catch (error) {
      setSourceSaveError(error.message)
    } finally {
      setIsSavingSource(false)
    }
  }

  return (
    <div className="shell">
      <Sidebar
        sources={sources}
        selectedSource={selectedSource}
        onSelectSource={setSelectedSource}
        onAddSource={() => setIsAddSourceOpen(true)}
        isLoadingSources={isLoadingSources}
        sourceLoadError={sourceLoadError}
        onRetryLoad={loadSources}
      />

      <Dashboard sources={sources} selectedSource={selectedSource} />

      {isAddSourceOpen && (
        <AddSourceModal
          onClose={() => setIsAddSourceOpen(false)}
          onConfirm={handleAddSource}
          isSaving={isSavingSource}
          serverError={sourceSaveError}
        />
      )}
    </div>
  )
}
