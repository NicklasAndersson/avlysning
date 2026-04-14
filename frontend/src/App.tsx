import { useState, useEffect } from 'react'
import { Map } from './components/Map'
import { InfoPanel } from './components/InfoPanel'
import { Disclaimer } from './components/Disclaimer'
import type { FieldStatus } from './types'
import './App.css'

function App() {
  const [statusData, setStatusData] = useState<FieldStatus | null>(null)
  const [selectedField, setSelectedField] = useState<string | null>(null)

  useEffect(() => {
    fetch('/data/skjutfalt_status.json')
      .then(res => res.json())
      .then(data => setStatusData(data as FieldStatus))
      .catch(err => console.error('Kunde inte ladda statusdata:', err))
  }, [])

  return (
    <div className="app">
      <header className="app-header">
        <h1>FM Avlysning</h1>
        {statusData && (
          <span className="last-updated">
            Uppdaterad: {new Date(statusData.last_updated).toLocaleString('sv-SE')}
          </span>
        )}
      </header>

      <main className="app-main">
        <Map
          statusData={statusData}
          onFieldClick={setSelectedField}
          selectedField={selectedField}
        />
        <InfoPanel
          statusData={statusData}
          selectedField={selectedField}
          onClose={() => setSelectedField(null)}
        />
      </main>

      <Disclaimer />
    </div>
  )
}

export default App
