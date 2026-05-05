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

  // selectedField kommer från field_config (FM-namn) eller som fallback polygon-namn.
  // För att alltid hitta rätt fält matchar vi både på `name` och på `id`.
  const field = statusData.fields.find(f => f.name === selectedField || f.id === selectedField)
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

  // Samla alla unika PDF-URLer från fältets pdf_urls, parse_errors, source_url och individuella restrictions
  const pdfUrls = [...new Set([
    ...(field.pdf_urls ?? []),
    ...(field.parse_errors ?? []),
    // Inkludera source_url om den är en PDF (kan vara fallback till första PDF:en)
    ...(field.source_url && field.source_url.toLowerCase().includes('.pdf') ? [field.source_url] : []),
    ...field.restrictions
      .map(r => r.source_url)
      .filter((u): u is string => !!u),
  ])]

  // Visa varning om parsning misslyckades, eller om vi har PDF:er
  // men ingen parsad restriktion (då vet vi inte säkert om fältet är fritt)
  const hasParseErrors = !!(field.parse_errors && field.parse_errors.length > 0)
  const hasUnparsedPdfs =
    !!(field.pdf_urls && field.pdf_urls.length > 0) &&
    field.restrictions.length === 0
  const isUncertain = hasParseErrors || hasUnparsedPdfs

  return (
    <div className="info-panel">
      <div className="info-panel-header">
        <h2>{field.name}</h2>
        <button onClick={onClose} className="close-btn" aria-label="Stäng">✕</button>
      </div>

      <div className="info-panel-body">
        <div className={`source-links ${isUncertain ? 'warning' : ''}`}>
          {pdfUrls.length > 0 ? (
            pdfUrls.map((url, i) => {
              const filename = url.split('/').pop() ?? 'PDF'
              return (
                <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="pdf-link">
                  📄 {filename}
                </a>
              )
            })
          ) : field.source_url ? (
            <a href={field.source_url} target="_blank" rel="noopener noreferrer">
              Källa: {field.source}
            </a>
          ) : null}
        </div>

        {dateRestrictions.length > 0 ? (
          <div className="restrictions active">
            <h3>Aktiva restriktioner {dateLabel}</h3>
            <RestrictionList restrictions={dateRestrictions} />
          </div>
        ) : hasParseErrors ? (
          <div className="restrictions upcoming">
            <p>
              ⚠️ Kunde inte läsa{' '}
              {field.parse_errors!.length === 1
                ? 'avlysnings-PDF:en'
                : `${field.parse_errors!.length} avlysnings-PDF:er`}{' '}
              för detta fält. Status okänd — kontrollera källan direkt.
            </p>
          </div>
        ) : hasUnparsedPdfs ? (
          <div className="restrictions upcoming">
            <p>
              ⚠️ Det finns {field.pdf_urls!.length === 1 ? 'en avlysnings-PDF' : `${field.pdf_urls!.length} avlysnings-PDF:er`}{' '}
              för detta fält men inga restriktioner kunde tolkas automatiskt.
              Status okänd — kontrollera källan direkt.
            </p>
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
