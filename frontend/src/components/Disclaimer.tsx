import { useState } from 'react'
import './Disclaimer.css'

export function Disclaimer() {
  // ponytail: localStorage räcker, ingen backend-persistens behövs
  const [dismissed, setDismissed] = useState(
    () => localStorage.getItem('ended-notice-dismissed') === '1'
  )

  const dismiss = () => {
    setDismissed(true)
    localStorage.setItem('ended-notice-dismissed', '1')
  }

  return (
    <>
      {!dismissed && (
        <div className="ended-notice" role="status">
          <p>
            <strong>Experimentet är avslutat.</strong> Sidan uppdateras inte längre –
            informationen som visas är gammal och kan vara felaktig.
          </p>
          <button className="ended-notice-close" onClick={dismiss} aria-label="Stäng meddelandet">
            ×
          </button>
        </div>
      )}
      <footer className="disclaimer">
        <p>
          <strong>Obs!</strong> Detta är <em>inte</em> en officiell tjänst från Försvarsmakten.
          Fysisk skyltning (bommar, röda lampor, varningsskyltar) vid fältet gäller alltid.
        </p>
      </footer>
    </>
  )
}
