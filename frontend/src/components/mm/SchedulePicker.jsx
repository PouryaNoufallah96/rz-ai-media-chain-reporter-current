export default function SchedulePicker({ date, time, onDateChange, onTimeChange, onConfirm, confirmLabel = 'Confirm Schedule' }) {
  return (
    <div style={{display:'flex',flexDirection:'column',gap:8}}>
      <div style={{display:'flex',gap:6}}>
        <input type="date" value={date} onChange={e=>onDateChange(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
        <input type="time" value={time} onChange={e=>onTimeChange(e.target.value)} className="cr-input" style={{flex:1,padding:'7px 8px',fontSize:11}} />
      </div>
      <button onClick={onConfirm}
        style={{width:'100%',padding:9,fontSize:11,fontWeight:700,letterSpacing:'.06em',textTransform:'uppercase',border:'none',borderRadius:9,cursor:'pointer',background:'linear-gradient(135deg,#f0a040,#e08030)',color:'#07090e',transition:'opacity .18s'}}
        onMouseEnter={e=>e.currentTarget.style.opacity='.85'} onMouseLeave={e=>e.currentTarget.style.opacity='1'}>
        {confirmLabel}
      </button>
    </div>
  )
}
