import { BriefcaseBusiness, CircleAlert, RefreshCw } from 'lucide-react'

export default function DecisionReferencePanel({ reference, state, error, onGenerate }) {
  const cards = reference?.cards || []
  return <section className="decision-reference" aria-labelledby="decision-reference-title">
    <header className="decision-heading"><div><h2 id="decision-reference-title"><BriefcaseBusiness size={16} />仓位决策参考</h2><p>板块与资金研究优先级。</p></div><div className="decision-heading-actions">{reference && <span className={`decision-source ${reference.analysis_source}`}>{reference.analysis_source === 'llm' ? '模型分析' : '规则分析'}</span>}<button className="primary-button" onClick={onGenerate} disabled={state === 'loading'}>{state === 'loading' ? <><RefreshCw className="loading-icon" size={14} />分析中</> : <><BriefcaseBusiness size={14} />{reference ? '重新分析' : '生成参考'}</>}</button></div></header>
    {state === 'loading' && <div className="decision-grid" aria-label="正在生成仓位决策参考">{Array.from({ length: 6 }).map((_, index) => <div className="decision-skeleton" key={index}><i /><i /><i /></div>)}</div>}
    {state === 'error' && <div className="decision-error"><CircleAlert size={16} /><span>{error}</span></div>}
    {state !== 'loading' && cards.length > 0 && <div className="decision-grid">{cards.map((card) => <DecisionCard card={card} key={card.theme} />)}</div>}
    {state === 'idle' && cards.length === 0 && <div className="decision-empty"><BriefcaseBusiness size={20} /><div><strong>等待 API 分析</strong><p>生成后展示板块状态与事实指标。</p></div></div>}
    {reference && <footer className="decision-disclaimer"><span>更新时间 {new Date(reference.as_of).toLocaleString('zh-CN')}</span><span>{reference.disclaimer}</span></footer>}
  </section>
}

function DecisionCard({ card }) {
  const metrics = [
    ['今日', card.day_change],
    ['20日', card.twenty_day_change],
    ['PE', card.pe],
    ['PB', card.pb],
    ['主力净流入', card.main_flow],
  ]
  return <article className="decision-card"><div className="decision-card-heading"><h3>{card.theme}</h3><span className={`decision-tag ${statusClass(card.decision)}`}>{card.decision}</span></div><div className="decision-metrics">{metrics.map(([label, value]) => <span key={label}><small>{label}</small><strong>{value}</strong></span>)}</div><p>{card.analysis}</p><div className="decision-risk"><CircleAlert size={13} /><span>{card.risk}</span></div></article>
}

function statusClass(decision) {
  if (decision === '重点跟踪') return 'priority'
  if (decision === '风险收敛') return 'risk'
  if (decision === '逢低核对') return 'verify'
  if (decision === '趋势观察') return 'trend'
  return 'neutral'
}
