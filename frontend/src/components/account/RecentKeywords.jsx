export default function RecentKeywords({ keywords }) {
  const kws = keywords || []

  if (!kws.length) {
    return <p className="acct-empty">No keywords yet — run "Analyze &amp; Route" to see your recent topics here.</p>
  }

  return (
    <div className="acct-keyword-pills">
      {kws.map((kw, i) => <span key={i} className="acct-keyword-pill">{kw}</span>)}
    </div>
  )
}
