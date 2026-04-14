import { useState, useEffect } from 'react'
import { Map } from './components/Map'
import { InfoPanel } from './components/InfoPanel'
import { FieldList } from './components/FieldList'
import { Disclaimer } from './components/Disclaimer'
import type { FieldStatus } from './types'
import './App.css'

function App() {
  const [statusData, setStatusData] = useState<FieldStatus | null>(null)
  const [selectedField, setSelectedField] = useState<string | null>(null)
  const [showList, setShowList] = useState(true)

  useEffect(() => {
    fetch('/data/skjutfalt_status.json')
      .then(res => res.json())
      .then(data => setStatusData(data as FieldStatus))
      .catch(err => console.error('Kunde inte ladda statusdata:', err))
  }, [])

  const handleFieldClick = (name: string | null) => {
    setSelectedField(name)
    if (name) setShowList(false)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>FM Avlysning</h1>
        <div className="header-right">
          <button
            className="list-toggle"
            onClick={() => { setShowList(!showList); setSelectedField(null) }}
          >
            {showList ? 'Dölj lista' : 'Visa lista'}
          </button>
          {statusData && (
            <span className="last-updated">
              Uppdaterad: {new Date(statusData.last_updated).toLocaleString('sv-SE')}
            </span>
          )}
        </div>
      </header>

      <main className="app-main">
        <Map
          statusData={statusData}
          onFieldClick={handleFieldClick}
          selectedField={selectedField}
        />
        {showList && !selectedField && (
          <FieldList
            statusData={statusData}
            onFieldClick={handleFieldClick}
          />
        )}
        <InfoPanel
          statusData={statusData}
          selectedField={selectedField}
          onClose={() => { setSelectedField(null); setShowList(true) }}
        />
      </main>

      <Disclaimer />
    </div>
  )
}

export default App
