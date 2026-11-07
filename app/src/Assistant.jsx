import { useEffect, useRef, useState } from 'react'
import { parseQuery, recommend } from './recommender.js'
import { moneyShort } from './format'

const EXAMPLES = [
  "I earn $100k a year and want a 2 bedroom under $600k in a safe suburb",
  'Quiet 1 bed near a train station under $750k',
  'Family-friendly 3 bedroom with parking under $2m',
  'Studio near the harbour under $500k',
]

export default function Assistant({ addresses, lifestyle, chat, setChat, onResults, onSelect }) {
  const [text, setText] = useState('')
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [chat.length])

  const ask = (question) => {
    if (!question.trim() || !addresses || !lifestyle) return
    const q = parseQuery(question, Object.keys(lifestyle.suburbs))
    const r = recommend(q, addresses, lifestyle)
    setChat([...chat, { role: 'user', text: question }, { role: 'bot', ...r }])
    onResults(r)
    setText('')
  }

  return (
    <div className="assistant">
      <p className="lede">Describe what you're after: income or budget, bedrooms, and the lifestyle you want. I'll rank real flats by their ValuIQ value and suburb data, and pin them on the map.</p>
      {!chat.length && (
        <div className="examples">
          {EXAMPLES.map((e) => <button key={e} onClick={() => ask(e)} disabled={!addresses || !lifestyle}>{e}</button>)}
        </div>
      )}
      <div className="chat">
        {chat.map((m, k) => m.role === 'user'
          ? <div key={k} className="msg user">{m.text}</div>
          : <BotMessage key={k} m={m} addresses={addresses} onSelect={onSelect} onShow={() => onResults(m)} latest={k === chat.length - 1} />)}
        <div ref={endRef} />
      </div>
      <form className="ask" onSubmit={(e) => { e.preventDefault(); ask(text) }}>
        <input value={text} onChange={(e) => setText(e.target.value)} aria-label="Ask ValuIQ"
          placeholder={addresses && lifestyle ? 'e.g. 2 bed under $900k near the train, safe area' : 'Loading data…'} />
        <button type="submit" disabled={!text.trim()}>Ask</button>
      </form>
      <p className="note">Values are ValuIQ estimates at 31 Aug 2026, not current listings. Crime, livability, income and rent are current Microburbs suburb indicators, used here for recommendations only and never in the valuation model. The borrowing guide is a rule of thumb, not financial advice.</p>
    </div>
  )
}

function BotMessage({ m, addresses, onSelect, onShow, latest }) {
  const row = (i) => addresses[i]
  return (
    <div className="msg bot">
      {m.reply.map((p, k) => <p key={k}>{p}</p>)}
      {!latest && (m.results.length || m.closest.length) ? <button className="link small" onClick={onShow}>Show these on the map again</button> : null}
      {m.suburbCards.length > 0 && (
        <div className="subcards">
          {m.suburbCards.map((s) => (
            <div key={s.name} className="subcard">
              <strong>{s.name.replace(/\s*\(.*\)$/, '')}</strong>
              <span>{s.count.toLocaleString('en-AU')} match{s.count === 1 ? '' : 'es'} · median {moneyShort(s.median)}</span>
              <span>Safety {s.safety ?? '–'}/100 · income {moneyShort(s.income)}</span>
              <span>Unit rent {s.rent ? `$${s.rent}/wk` : '–'}</span>
            </div>
          ))}
        </div>
      )}
      {[['results', m.results, false], ['closest', m.closest, true]].map(([key, list, stretch]) => list.length > 0 && (
        <ol key={key} className="recs" style={{ counterReset: `rec ${key === 'closest' ? m.results.length : 0}` }}>
          {key === 'closest' && <li className="sub">Just above budget</li>}
          {list.map((i) => (
            <li key={i}><button onClick={() => onSelect(i)}>
              <span>{row(i)[1]}<small>{row(i)[2].replace(/\s*\(.*\)$/, '')}{row(i)[4] != null ? ` · ${row(i)[4] === 0 ? 'studio' : `${row(i)[4]} bed`}` : ''}{row(i)[18] != null ? ` · ${Math.round(row(i)[18])} m to station` : ''}</small></span>
              <b className={stretch ? 'stretch' : ''}>{moneyShort(row(i)[3])}</b>
            </button></li>
          ))}
        </ol>
      ))}
    </div>
  )
}
