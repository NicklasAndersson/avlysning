import type { FieldStatus } from '../types'
import './FieldList.css'

function formatDateISO(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

interface FieldListProps {
  statusData: FieldStatus | null
  onFieldClick: (name: string) => void
  selectedDateTime: Date
}

export function FieldList({ statusData, onFieldClick, selectedDateTime }: FieldListProps) {
  if (!statusData) return null

  const selectedDate = formatDateISO(selectedDateTime)
  const isToday = selectedDate === formatDateISO(new Date())

  const activeFields = statusData.fields
    .filter(f => f.restrictions.some(r => r.date === selectedDate))
    .map(f => ({
      ...f,
      dateRestrictions: f.restrictions.filter(r => r.date === selectedDate),
    }))
    .sort((a, b) => a.name.localeCompare(b.name, 'sv'))

  const upcomingFields = statusData.fields
    .filter(f => f.restrictions.length > 0 && !f.restrictions.some(r => r.date === selectedDate))
    .sort((a, b) => a.name.localeCompare(b.name, 'sv'))

  const dateLabel = isToday ? selectedDate : `${selectedDate} (valt datum)`

  return (
    <div className="field-list">
      <div className="field-list-header">
        <h2>Skjutfält — {dateLabel}</h2>
        <span className="field-count">
          {activeFields.length} avlysta {isToday ? 'idag' : 'denna dag'}
        </span>
      </div>

      <div className="field-list-body">
        {activeFields.length > 0 && (
          <section>
            <h3 className="section-title active">Avlysta {isToday ? 'idag' : selectedDate}</h3>
            {activeFields.map(f => (
              <button
                key={f.id}
                className="field-item active"
                onClick={() => onFieldClick(f.name)}
              >
                <span className="field-name">{f.name}</span>
                <span className="field-times">
                  {f.dateRestrictions.map((r, i) => (
                    <span key={i} className="time-badge">
                      {r.start}–{r.end}
                    </span>
                  ))}
                </span>
              </button>
            ))}
          </section>
        )}

        {upcomingFields.length > 0 && (
          <section>
            <h3 className="section-title upcoming">Kommande restriktioner</h3>
            {upcomingFields.map(f => {
              const next = f.restrictions
                .filter(r => r.date > selectedDate)
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
