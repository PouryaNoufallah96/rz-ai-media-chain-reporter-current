export default function StatsRow({ stats }) {
  const s = stats || { postsGenerated: 0, scheduled: 0, saved: 0 }
  return (
    <div className="acct-stats-row">
      <div className="acct-stat-box">
        <div className="acct-stat-value">{s.postsGenerated}</div>
        <div className="acct-stat-label">Posts Generated</div>
      </div>
      <div className="acct-stat-box">
        <div className="acct-stat-value">{s.scheduled}</div>
        <div className="acct-stat-label">Scheduled</div>
      </div>
      <div className="acct-stat-box">
        <div className="acct-stat-value">{s.saved}</div>
        <div className="acct-stat-label">Saved</div>
      </div>
    </div>
  )
}
