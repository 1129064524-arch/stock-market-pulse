import { AlertTriangle, ArrowUpRight, BrainCircuit, ChevronDown, RefreshCw, Search, Sparkles, Star, X } from 'lucide-react'
import { DailyChart, PriceMark } from '../components/market.jsx'

export default function MarketRadar({
  marketIndices,
  liveOverview,
  liveMovers,
  liveSectors,
  apiAvailable,
  providerHealth,
  marketSourceLabel,
  filteredMovers,
  selected,
  setSelected,
  focusOpen,
  setFocusOpen,
  watchlist,
  toggleWatch,
  dailyBars,
  dailyIndicators,
  syncingHistory,
  syncDailyHistory,
  signalAnalysisState,
  generateSignalAnalysis,
  query,
  setQuery,
  setOnlyStrong,
  market,
  setMarket,
  setActiveNav,
}) {
  return <>
    <section className="market-strip" aria-label="市场指数">
      {marketIndices.map((index, position) => <div className={`market-card ${position === 0 ? 'main-index' : ''}`} key={index.name}><span>{index.name}</span><strong>{index.value}</strong><PriceMark direction={index.direction}>{index.change}</PriceMark></div>)}
      <div className="market-breadth"><span>市场广度</span><div className="breadth-bar"><i style={{ width: `${liveOverview ? Math.round((liveOverview.advancing / Math.max(liveOverview.advancing + liveOverview.declining, 1)) * 100) : 68}%` }} /></div><strong>{liveOverview?.advancing?.toLocaleString() || '3,681'}</strong><span className="breadth-muted">上涨 / {liveOverview?.declining?.toLocaleString() || '1,426'} 下跌</span></div>
      <div className="market-card compact"><span>数据来源</span><strong>{liveOverview?.source === 'akshare' ? 'AkShare' : liveOverview?.source === 'eastmoney' ? '东方财富' : liveOverview?.source === 'sina' ? '新浪' : liveOverview?.source === 'cache' ? '本地缓存' : '演示数据'}</strong><span className="neutral-label">{liveOverview?.as_of ? new Date(liveOverview.as_of).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : '等待连接'} · {providerHealth?.find((item) => item.provider === liveOverview?.source)?.status === 'ready' ? '已验证' : liveOverview?.source === 'cache' ? '降级' : '待核验'}</span></div>
    </section>
    <section className="radar-grid">
      <article className="panel movers-panel">
        <div className="panel-heading"><div><h2>正在发生</h2><p>按信号置信度排序，实时刷新</p></div><div className="panel-controls"><label className="search"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索代码、名称或板块" /></label><button className="select-control" onClick={() => setMarket(market === '全部市场' ? '沪深 A 股' : '全部市场')}>{market}<ChevronDown size={15} /></button></div></div>
        <div className="table-wrap"><table><thead><tr><th>标的</th><th>最新价</th><th>涨跌幅</th><th>信号</th><th>量能</th><th>所属板块</th><th>置信度</th></tr></thead><tbody>{filteredMovers.map((stock) => <tr key={stock.code} className={selected.code === stock.code ? 'selected-row' : ''} onClick={() => { setSelected(stock); setFocusOpen(true) }}><td><strong>{stock.name}</strong><small>{stock.code}</small></td><td>{stock.price}</td><td><PriceMark direction={stock.direction}>{stock.change}</PriceMark></td><td><span className={`signal-chip ${stock.direction}`}>{stock.signal}</span></td><td>{stock.volume}</td><td>{stock.sector}</td><td><div className="score"><span>{stock.score}</span><i><b style={{ width: `${stock.score}%` }} /></i></div></td></tr>)}</tbody></table>{filteredMovers.length === 0 && <div className="empty-state"><Search size={24} /><p>没有匹配的市场信号</p><button onClick={() => { setQuery(''); setOnlyStrong(false) }}>清除筛选</button></div>}</div>
        <footer className="panel-footer"><span><span className={apiAvailable && ['akshare', 'eastmoney', 'sina'].includes(liveOverview?.source) ? 'live-dot' : 'offline-dot'} />{apiAvailable ? marketSourceLabel : '演示数据模式'}</span><button onClick={() => setActiveNav('信号池')}>查看 {liveMovers.length} 个高异动信号 <ArrowUpRight size={15} /></button></footer>
      </article>
      <aside className="right-column">
        {focusOpen && <FocusPanel selected={selected} watchlist={watchlist} toggleWatch={toggleWatch} dailyBars={dailyBars} dailyIndicators={dailyIndicators} syncingHistory={syncingHistory} syncDailyHistory={syncDailyHistory} signalAnalysisState={signalAnalysisState} generateSignalAnalysis={generateSignalAnalysis} setFocusOpen={setFocusOpen} setActiveNav={setActiveNav} />}
        <article className="panel sectors-panel"><div className="panel-heading compact-heading"><div><h2>板块联动</h2><p>成交额与强度同步观察</p></div><button className="text-button" onClick={() => { setQuery(''); setActiveNav('信号池') }}>全部板块</button></div><div className="sectors-list">{liveSectors.map((sector) => <button className="sector-row" key={sector.name} onClick={() => { setQuery(sector.name); setActiveNav('信号池') }}><div><strong>{sector.name}</strong><span>{sector.stocks} 只上涨</span></div><div><PriceMark direction={sector.direction}>{sector.change}</PriceMark><small>{sector.amount}</small></div></button>)}</div></article>
      </aside>
    </section>
  </>
}

function FocusPanel({ selected, watchlist, toggleWatch, dailyBars, dailyIndicators, syncingHistory, syncDailyHistory, signalAnalysisState, generateSignalAnalysis, setFocusOpen, setActiveNav }) {
  return <article className="panel focus-panel">
    <div className="panel-heading compact-heading"><div><h2>焦点标的</h2><p>来自市场异动</p></div><button className="icon-button" aria-label="关闭焦点标的" onClick={() => setFocusOpen(false)}><X size={17} /></button></div>
    <div className="focus-symbol"><div><div className="stock-name"><strong>{selected.name}</strong><button aria-label="加入自选" onClick={() => toggleWatch()}><Star size={16} fill={watchlist.some((item) => item.code === selected.code) ? 'currentColor' : 'none'} /></button></div><span>{selected.code} · {selected.sector}</span></div><div className="focus-price"><strong>{selected.price}</strong><PriceMark direction={selected.direction}>{selected.change}</PriceMark></div></div>
    <DailyChart code={selected.code} bars={dailyBars} />
    <div className="daily-metrics">{dailyIndicators ? <><span><small>MA5</small><strong>{dailyIndicators.sma_5 ?? '--'}</strong></span><span><small>MA20</small><strong>{dailyIndicators.sma_20 ?? '--'}</strong></span><span><small>日线趋势</small><strong className={`trend-${dailyIndicators.trend}`}>{dailyIndicators.trend === 'up' ? '向上' : dailyIndicators.trend === 'down' ? '向下' : '震荡'}</strong></span></> : <span className="history-empty">日线尚未同步</span>}<button className="text-button" onClick={syncDailyHistory} disabled={syncingHistory}>{syncingHistory ? <><RefreshCw className="loading-icon" size={14} />同步中</> : <><RefreshCw size={14} />同步日线</>}</button></div>
    <div className="explanation"><Sparkles size={17} /><div><strong>{selected.signal} · 置信度 {selected.score}</strong><p>{selected.note}</p><span><AlertTriangle size={13} />风险：{selected.risk}</span></div></div>
    <div className="signal-research"><button className="signal-ai-button" onClick={generateSignalAnalysis} disabled={signalAnalysisState === 'loading'}><BrainCircuit size={16} />{signalAnalysisState === 'loading' ? '正在进入研判' : 'AI 解读此信号'}</button></div>
    <button className="detail-button" onClick={() => setActiveNav('信号池')}>打开完整分析 <ArrowUpRight size={16} /></button>
  </article>
}
