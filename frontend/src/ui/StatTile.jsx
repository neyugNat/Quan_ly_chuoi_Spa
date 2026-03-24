export function StatTile({ title, value, sub }) {
  return (
    <article className="card stat-tile">
      <div className="stat-tile-title">{title}</div>
      <div className="stat-tile-value">{value}</div>
      {sub ? <div className="stat-tile-sub">{sub}</div> : null}
    </article>
  )
}
