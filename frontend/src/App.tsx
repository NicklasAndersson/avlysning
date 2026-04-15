import { useState, useEffect, useCallback, useRef } from 'react'
import { Map } from './components/Map'
import { InfoPanel } from './components/InfoPanel'
import { FieldList } from './components/FieldList'
import { Disclaimer } from './components/Disclaimer'
import type { FieldStatus } from './types'
import { dataUrl } from './dataUrl'
import './App.css'

function toLocalDatetimeString(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function App() {
  const [statusData, setStatusData] = useState<FieldStatus | null>(null)
  const [selectedField, setSelectedField] = useState<string | null>(null)
  const [isPermanentBan, setIsPermanentBan] = useState(false)
  const [showList, setShowList] = useState(false)
  const [selectedDateTime, setSelectedDateTime] = useState(() => new Date())
  const [isLive, setIsLive] = useState(true)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    fetch(dataUrl('skjutfalt_status.json'))
      .then(res => res.json())
      .then(data => setStatusData(data as FieldStatus))
      .catch(err => console.error('Kunde inte ladda statusdata:', err))
  }, [])

  // Auto-tick varje 60s när isLive
  useEffect(() => {
    if (isLive) {
      intervalRef.current = setInterval(() => {
        setSelectedDateTime(new Date())
      }, 60_000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isLive])

  const handleDateTimeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    if (!val) return
    setSelectedDateTime(new Date(val))
    setIsLive(false)
  }, [])

  const handleNowClick = useCallback(() => {
    setSelectedDateTime(new Date())
    setIsLive(true)
  }, [])

  const handleFieldClick = (name: string | null, permanentBan = false) => {
    setSelectedField(name)
    setIsPermanentBan(permanentBan)
    if (name) setShowList(false)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>FM Avlysning</h1>
        <div className="header-right">
          <div className="datetime-picker">
            <input
              type="datetime-local"
              className="datetime-input"
              value={toLocalDatetimeString(selectedDateTime)}
              onChange={handleDateTimeChange}
            />
            {!isLive && (
              <button className="now-btn" onClick={handleNowClick}>
                Nu
              </button>
            )}
            {isLive && (
              <span className="live-indicator">● Live</span>
            )}
          </div>
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
          selectedDateTime={selectedDateTime}
        />
        {showList && !selectedField && (
          <FieldList
            statusData={statusData}
            onFieldClick={handleFieldClick}
            selectedDateTime={selectedDateTime}
          />
        )}
        <InfoPanel
          statusData={statusData}
          selectedField={selectedField}
          onClose={() => { setSelectedField(null); setShowList(true) }}
          selectedDateTime={selectedDateTime}
          isPermanentBan={isPermanentBan}
        />
      </main>

      <Disclaimer />
    </div>
  )
}

export default App
