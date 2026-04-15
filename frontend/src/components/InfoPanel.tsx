import type { FieldStatus, Restriction } from '../types'
import './InfoPanel.css'

function formatDateISO(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

interface InfoPanelProps {
  statusData: FieldStatus | null
  selectedField: string | null
  onClose: () => void
  selectedDateTime: Date
  isPermanentBan?: boolean
}

export function InfoPanel({ statusData, selectedField, onClose, selectedDateTime, isPermanentBan }: InfoPanelProps) {
  if (!selectedField || !statusData) return null

  const field = statusData.fields.find(f => f.name === selectedField)
  if (!field) {
    return (
      <div className="info-panel">
        <div className="info-panel-header">
          <h2>{selectedField}</h2>
          <button onClick={onClose} className="close-btn" aria-label="Stäng">✕</button>
        </div>
        <div className="info-panel-body">
          <div className={`restrictions ${isPermanentBan ? 'active' : 'clear'}`}>
            {isPermanentBan ? (
              <p>⛔ Permanent tillträdesförbud. Detta är ett militärt område med ständigt tillträdesförbud för obehöriga.</p>
            ) : (
              <p>Vi saknar data för detta område. Det kan bero på att fältet inte ingår i våra källor ännu, eller att det inte har några aktuella avlysningar.</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  const selectedDate = formatDateISO(selectedDateTime)
  const isToday = selectedDate === formatDateISO(new Date())
  const dateRestrictions = field.restrictions.filter(r => r.date === selectedDate)
  const futureRestrictions = field.restrictions.filter(r => r.date > selectedDate)

  const dateLabel = isToday ? 'idag' : selectedDate

  // Samla unika PDF-URLer
  const pdfUrls = [...new Set(
    field.restrictions
      .map(r => r.source_url)
      .filter((u): u is string => !!u)
  )]

  return (
    <div className="info-panel">
      <div className="info-panel-header">
        <h2>{field.name}</h2>
        <button onClick={onClose} className="close-btn" aria-label="Stäng">✕</button>
      </div>

      <div className="info-panel-body">
        <div className="source-links">
          {pdfUrls.length > 0 ? (
            pdfUrls.map((url, i) => {
              const filename = url.split('/').pop() ?? 'PDF'
              return (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="pdf-link">
                  📄 {filename}
                </a>
              )
            })
          ) : (
            <a href={field.source_url} target="_blank" rel="noopener noreferrer">
              Källa: {field.source}
            </a>
          )}
        </div>

        {dateRestrictions.length > 0 ? (
          <div className="restrictions active">
            <h3>Aktiva restriktioner {dateLabel}</h3>
            <RestrictionList restrictions={dateRestrictions} />
          </div>
        ) : (
          <div className="restrictions clear">
            <p>Inga aktiva restriktioner {dateLabel}.</p>
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

function RestrictionList({ restrictions }: { restrictions: Restriction[] }) {
  return (
    <ul className="restriction-list">
      {restrictions.map((r, i) => (
        <li key={i}>
          <span className="date">{r.date}</span>
          {r.start && r.end && (
            <span className="time">{r.start}–{r.end}</span>
          )}
          {r.type && <span className="type">{r.type}</span>}
          {r.sectors.length > 0 && r.sectors[0] !== 'all' && (
            <span className="sectors">{r.sectors.join(', ')}</span>
          )}
        </li>
      ))}
    </ul>
  )
}
