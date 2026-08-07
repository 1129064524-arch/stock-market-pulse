import { Activity, ArrowUpRight, BrainCircuit, GitBranch, PieChart } from 'lucide-react'
import { PriceMark } from '../components/market.jsx'

export default function CrossMarketPage({ liveOverview, movers, fundOverview, linkage, linkageState, crossAnalysis, crossAnalysisState, crossAnalysisError, llmConfigured, generateCrossAnalysis, setActiveNav }) {
  const funds = fundOverview.funds || []
  const linkageItems = linkage?.items || []
  const resonanceCount = linkageItems.filter((item) => item.state.startsWith('共振')).length
  const divergenceCount = linkageItems.filter((item) => item.state === '出现背离').length

  return <section className="workspace-page cross-market-page">
    <div className="cross-summary" aria-label="跨市场概览">
      <div><span>股票异动</span><strong>{movers.length}</strong><small>{liveOverview?.advancing?.toLocaleString() || '--'} 上涨 / {liveOverview?.declining?.toLocaleString() || '--'} 下跌</small></div>
      <div><span>基金全市场</span><strong>{fundOverview.universe_count?.toLocaleString() || '--'}</strong><small>当前展示 {funds.length} 条净值异动</small></div>
      <div><span>跨市场共振</span><strong>{resonanceCount}</strong><small>股票板块与基金风格同向</small></div>
      <div><span>风格背离</span><strong className="cross-risk-number">{divergenceCount}</strong><small>待核对净值与持仓</small></div>
    </div>

    <article className="panel cross-ai-panel"><div><div className="cross-ai-title"><BrainCircuit size={16} /><strong>跨市场 AI 统筹</strong><span className={`model-status ${llmConfigured ? 'connected' : ''}`}>{llmConfigured ? '模型已配置' : '待配置'}</span></div><p>本地快照 → 研究清单。</p></div><div className="cross-ai-actions"><button className="text-button" onClick={() => setActiveNav('仓位参考')}>仓位参考 <ArrowUpRight size={14} /></button><button className="primary-button" onClick={generateCrossAnalysis} disabled={crossAnalysisState === 'loading'}><BrainCircuit size={15} />{crossAnalysisState === 'loading' ? '正在统筹' : crossAnalysis ? '重新统筹' : '生成跨市场研判'}</button></div></article>

    {crossAnalysisState === 'success' && crossAnalysis && <article className="panel cross-analysis-result"><div className={`cross-regime ${crossAnalysis.regime}`}>{crossAnalysis.regime}</div><div className="cross-analysis-summary"><strong>{crossAnalysis.summary}</strong><EvidenceMeta coverage={crossAnalysis.evidence_coverage} refs={crossAnalysis.evidence_refs} /><span>{crossAnalysis.disclaimer}</span></div><AnalysisList title="股票侧" items={crossAnalysis.stock_view} /><AnalysisList title="基金侧" items={crossAnalysis.fund_view} /><AnalysisList title="下一步核对" items={crossAnalysis.next_checks} /><AnalysisList title="风险与背离" items={[...crossAnalysis.divergences, ...crossAnalysis.risks]} /></article>}
    {crossAnalysisState === 'error' && <div className="panel cross-analysis-error"><BrainCircuit size={17} /><span>{crossAnalysisError}</span></div>}

    <div className="cross-market-grid">
      <MarketSide title="股票市场" description="个股与板块" icon={Activity} action="进入股票雷达" onOpen={() => setActiveNav('股票雷达')} rows={movers.slice(0, 6)} kind="stock" />
      <MarketSide title="基金市场" description="净值与风格" icon={PieChart} action="进入基金全景" onOpen={() => setActiveNav('基金全景')} rows={funds.slice(0, 6)} kind="fund" />
    </div>

    <article className="panel linkage-panel">
      <div className="panel-heading compact-heading"><div><h2><GitBranch size={15} />股票 × 基金联动</h2><p>基金风格与股票板块</p></div><span className={`signal-source ${linkageState}`}>{linkageState === 'loading' ? '联动计算中' : `${linkageItems.length} 个主题`}</span></div>
      <div className="linkage-header"><span>主题</span><span>基金侧</span><span>股票侧</span><span>关联板块</span><span>联动状态</span><span>置信度</span></div>
      {linkageItems.map((item) => <div className="linkage-row" key={item.theme}><strong>{item.theme}</strong><span>{item.fund_change}</span><span>{item.sector_change}</span><span>{item.sectors.join('、') || '暂无直接映射'}</span><span className={`linkage-state ${item.state.includes('向下') || item.state === '出现背离' ? 'risk' : item.state.includes('向上') ? 'positive' : ''}`}>{item.state}</span><div className="score"><span>{item.confidence}</span><i><b style={{ width: `${item.confidence}%` }} /></i></div></div>)}
      {linkageItems.length === 0 && <div className="empty-state"><GitBranch size={24} /><p>{linkageState === 'loading' ? '正在协调股票与基金信号' : '等待两侧市场数据'}</p></div>}
      <footer className="linkage-note">风格映射，不等同于最新持仓。</footer>
    </article>
  </section>
}

function AnalysisList({ title, items }) {
  return <div className="cross-analysis-column"><h3>{title}</h3><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>
}

function EvidenceMeta({ coverage, refs = [] }) {
  if (!coverage) return null
  const limited = coverage.status !== 'verified'
  return <div className={`evidence-meta ${limited ? 'limited' : ''}`} title={(coverage.limitations || []).join('；')}><span>{limited ? '证据有限' : '证据已核验'}</span><small>{coverage.referenced_count || 0}/{coverage.item_count || 0} 项 · {(coverage.sources || []).join(' / ') || '本地数据'}</small>{refs?.length ? <small>引用 {refs.length}</small> : null}</div>
}

function MarketSide({ title, description, icon: Icon, action, onOpen, rows, kind }) {
  return <article className="panel cross-side-panel"><div className="panel-heading compact-heading"><div><h2><Icon size={15} />{title}</h2><p>{description}</p></div><button className="text-button" onClick={onOpen}>{action} <ArrowUpRight size={14} /></button></div><div className="cross-list-header"><span>标的</span><span>{kind === 'fund' ? '主题' : '板块'}</span><span>信号</span><span>涨跌</span></div>{rows.map((item) => <div className="cross-list-row" key={item.code}><div><strong>{item.name}</strong><small>{item.code}</small></div><span>{kind === 'fund' ? item.theme : item.sector}</span><span className={`signal-chip ${item.direction}`}>{kind === 'fund' ? item.signal : item.signal}</span><PriceMark direction={item.direction}>{item.change}</PriceMark></div>)}</article>
}
