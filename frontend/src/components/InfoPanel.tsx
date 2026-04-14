import type { FieldStatus, Field } from '../types'
import './InfoPanel.css'

interface InfoPanelProps {
  statusData: FieldStatus | null
  selectedField: string | null
  onClose: () => void
}

export function InfoPanel({ statusData, selectedField, onClose }: InfoPanelProps) {
  if (!selectedField || !statusData) return null

  const field = statusData.fields.find(f => f.id === selectedField)
  if (!field) return null

  const today = new Date().toISOString().split('T')[0]!
  const todayRestrictions = field.restrictions.filter(r => r.date === today)
  const futureRestrictions = field.restrictions.filter(r => r.date > today)

  return (
    <div className="info-panel">
      <div className="info-panel-header">
        <h2>{field.name}</h2>
        <button onClick={onClose} className="close-btn" aria-label="Stäng">✕</button>
      </div>

      <div className="info-panel-body">
        <p className="source">
          Källa: <a href={field.source_url} target="_blank" rel="noopener noreferrer">{field.source}</a>
        </p>

        {todayRestrictions.length > 0 ? (
          <div className="restrictions active">
            <h3>Aktiva restriktioner idag</h3>
            <RestrictionList restrictions={todayRestrictions} />
          </div>
        ) : (
          <div className="restrictions clear">
            <p>Inga aktiva restriktioner idag.</p>
          </div>
        )}

        {futureRestrictions.length > 0 && (
          <div className="restrictions upcoming">
            <h3>Kommande</h3>
            <RestrictionList restrictions={futureRestrictions} />
          </div>
        )}
      </div>
    </div>
  )
}

function RestrictionList({ restrictions }: { restrictions: Field['restrictions'] }) {
  return (
    <ul className="restriction-list">
      {restrictions.map((r, i) => (
        <li key={i}>
          <span className="date">{r.date}</span>
          {r.start && r.end && (
            <span className="time">{r.start}–{r.end}</span>
          )}
          <span className="type">{r.type}</span>
          <span className="sectors">{r.sectors.join(', ')}</span>
        </li>
      ))}
    </ul>
  )
}
