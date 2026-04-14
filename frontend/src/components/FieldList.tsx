import type { FieldStatus } from '../types'
import './FieldList.css'

interface FieldListProps {
  statusData: FieldStatus | null
  onFieldClick: (name: string) => void
}

export function FieldList({ statusData, onFieldClick }: FieldListProps) {
  if (!statusData) return null

  const today = new Date().toISOString().split('T')[0]!

  const activeFields = statusData.fields
    .filter(f => f.restrictions.some(r => r.date === today))
    .map(f => ({
      ...f,
      todayRestrictions: f.restrictions.filter(r => r.date === today),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'sv'))

  const inactiveFields = statusData.fields
    .filter(f => f.restrictions.length > 0 && !f.restrictions.some(r => r.date === today))
    .sort((a, b) => a.name.localeCompare(b.name, 'sv'))

  return (
    <div className="field-list">
      <div className="field-list-header">
        <h2>Skjutfält — {today}</h2>
        <span className="field-count">
          {activeFields.length} avlysta idag
        </span>
      </div>

      <div className="field-list-body">
        {activeFields.length > 0 && (
          <section>
            <h3 className="section-title active">Avlysta idag</h3>
            {activeFields.map(f => (
              <button
                key={f.id}
                className="field-item active"
                onClick={() => onFieldClick(f.name)}
              >
                <span className="field-name">{f.name}</span>
                <span className="field-times">
                  {f.todayRestrictions.map((r, i) => (
                    <span key={i} className="time-badge">
                      {r.start}–{r.end}
                    </span>
                  ))}
                </span>
              </button>
            ))}
          </section>
        )}

        {inactiveFields.length > 0 && (
          <section>
            <h3 className="section-title upcoming">Kommande restriktioner</h3>
            {inactiveFields.map(f => {
              const next = f.restrictions
                .filter(r => r.date > today)
                .sort((a, b) => a.date.localeCompare(b.date))[0]
              return (
                <button
                  key={f.id}
                  className="field-item upcoming"
                  onClick={() => onFieldClick(f.name)}
                >
                  <span className="field-name">{f.name}</span>
                  {next && (
                    <span className="next-date">{next.date}</span>
                  )}
                </button>
              )
            })}
          </section>
        )}
      </div>
    </div>
  )
}
