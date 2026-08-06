import { AlertCircle, ArrowDownRight, ArrowUpRight, BrainCircuit, Check, Filter, PieChart, RefreshCw, Star, X } from 'lucide-react'
import { PriceMark } from '../components/market.jsx'

export default function FundsPage({ funds, universeCount, categoryCounts, fundsState, fundSource, fundWatchlist, onlyMine, setOnlyMine, refreshFunds, toggleFundWatch, selectedFund, fundHoldings, fundLinkedStocks, fundHoldingsState, fundHoldingsError, openFundHoldings, closeFundHoldings, analyzeFund, fundAnalysis, fundAnalysisState, fundAnalysisError }) {
  const visibleFunds = onlyMine ? funds.filter((fund) => fundWatchlist.includes(fund.code)) : funds
  const positiveCount = funds.filter((fund) => fund.direction === 'up').length
  const negativeCount = funds.filter((fund) => fund.direction === 'down').length
  const totalLabel = universeCount ? universeCount.toLocaleString() : '--'
  const holdingByCode = Object.fromEntries(fundLinkedStocks.map((item) => [item.code, item]))
  const reportDate = fundHoldings[0]?.report_date || '--'

  return <section className="workspace-page funds-page">
    <div className="workspace-heading">
      <div><h2>基金全景</h2><p>全市场净值与风格。</p></div>
      <div className="workspace-actions">
        <span className={`signal-source ${fundsState}`}>{fundSource === 'eastmoney' ? `全市场扫描 · ${totalLabel} 只` : '演示基金全景'}</span>
        <button className="filter-button" onClick={() => setOnlyMine((value) => !value)}><Filter size={15} />{onlyMine ? '查看全市场' : '只看我的基金'}</button>
        <button className="primary-button" onClick={refreshFunds} disabled={fundsState === 'loading'}><RefreshCw className={fundsState === 'loading' ? 'loading-icon' : ''} size={15} />{fundsState === 'loading' ? '扫描中' : '刷新净值榜'}</button>
      </div>
    </div>

    <div className="fund-strip" aria-label="基金全景概览">
      <div><span>基金宇宙</span><strong>{totalLabel}</strong><small>开放式基金目录</small></div>
      <div><span>本次异动</span><strong>{funds.length}</strong><small>涨幅榜 + 跌幅榜</small></div>
      <div><span>强弱分布</span><strong><em className="fund-up">{positiveCount}</em> / <em className="fund-down">{negativeCount}</em></strong><small>上涨 / 下跌</small></div>
      <div><span>类型规模</span><strong>{(categoryCounts['混合型'] || 0).toLocaleString()}</strong><small>混合型基金 · 另含指数、债券、QDII、FOF</small></div>
    </div>

    <div className="panel fund-list">
      <div className="fund-list-header"><span>基金</span><span>类型 / 主题</span><span>单位净值</span><span>日 / 周</span><span>阶段表现</span><span>异动与风险</span><span>观察</span></div>
      {visibleFunds.map((fund) => {
        const watched = fundWatchlist.includes(fund.code)
        return <div className={`fund-list-row ${selectedFund?.code === fund.code ? 'selected' : ''}`} key={fund.code} role="button" tabIndex={0} onClick={() => openFundHoldings(fund)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openFundHoldings(fund) } }}>
          <div className="fund-identity"><strong>{fund.name}</strong><small>{fund.code} · {fund.nav_date}</small></div>
          <div><span className="fund-type">{fund.fund_type}</span><small>{fund.theme}</small></div>
          <div className="fund-values"><strong>{fund.nav}</strong><small>确认净值</small></div>
          <div className="fund-return"><PriceMark direction={fund.direction}>{fund.change}</PriceMark><small>周 {fund.week_change}</small></div>
          <div className="fund-period"><strong>月 {fund.month_change}</strong><small>年 {fund.year_change}</small></div>
          <div className="fund-signal"><span className={`signal-chip ${fund.direction}`}>{fund.signal}</span><small>{fund.risk}</small></div>
          <button className={`fund-watch-toggle ${watched ? 'watched' : ''}`} aria-label={watched ? `取消观察 ${fund.name}` : `加入观察 ${fund.name}`} onClick={(event) => { event.stopPropagation(); toggleFundWatch(fund) }}>{watched ? <Check size={15} /> : <Star size={15} />}</button>
        </div>
      })}
      {visibleFunds.length === 0 && <div className="empty-state"><PieChart size={24} /><p>还没有加入观察的基金</p><button onClick={() => setOnlyMine(false)}>查看全市场基金</button></div>}
    </div>
    {selectedFund && <section className="fund-holdings-panel" aria-label={`${selectedFund.name}持仓穿透`}>
      <div className="fund-holdings-heading">
        <div><span className="section-kicker">真实持仓穿透</span><h3>{selectedFund.name}<small>{selectedFund.code}</small></h3><p>按公开季报前十大重仓股与当前股票行情估算贡献</p></div>
        <button className="icon-button" onClick={closeFundHoldings} aria-label="关闭持仓详情"><X size={16} /></button>
      </div>
      {fundHoldingsState === 'loading' && <div className="fund-holdings-status"><RefreshCw className="loading-icon" size={16} />正在读取季报持仓与市场行情...</div>}
      {fundHoldingsState === 'error' && <div className="fund-holdings-status error"><AlertCircle size={16} /><span>{fundHoldingsError}</span></div>}
      {fundHoldingsState === 'ready' && <>
        <div className="fund-holdings-meta"><span>报告期 <strong>{reportDate}</strong></span><span>已匹配行情 <strong>{fundLinkedStocks.length}/{fundHoldings.length}</strong></span><span className="fund-data-note">数据源：天天基金公开季报 · 仅研究估算</span><button className="fund-ai-button" onClick={analyzeFund} disabled={fundAnalysisState === 'loading'}><BrainCircuit size={14} />{fundAnalysisState === 'loading' ? '分析中' : '基金研判'}</button></div>
        {fundHoldings.length === 0 ? <div className="fund-holdings-status"><AlertCircle size={16} />暂无可用季报持仓</div> : <div className="fund-holdings-table">
          <div className="fund-holdings-table-head"><span>重仓股</span><span>占净值比</span><span>实时涨跌</span><span>组合贡献</span></div>
          {fundHoldings.map((holding) => {
            const linked = holdingByCode[holding.stock_code]
            const change = linked?.change_pct
            const contribution = linked?.contribution
            const positive = Number(change) >= 0
            return <div className="fund-holdings-row" key={holding.stock_code}><div><strong>{holding.stock_name}</strong><small>{holding.stock_code}</small></div><span>{holding.weight_pct.toFixed(2)}%</span><span className={linked ? (positive ? 'fund-up' : 'fund-down') : 'unmatched'}>{linked ? <>{positive ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}{change > 0 ? '+' : ''}{Number(change).toFixed(2)}%</> : '待匹配'}</span><span className={linked ? (Number(contribution) >= 0 ? 'fund-up' : 'fund-down') : 'unmatched'}>{linked ? `${contribution > 0 ? '+' : ''}${Number(contribution).toFixed(3)}%` : '--'}</span></div>
          })}
        </div>}
        {fundAnalysisState === 'error' && <div className="fund-analysis-status error"><AlertCircle size={15} />{fundAnalysisError}</div>}
        {fundAnalysisState === 'success' && fundAnalysis && <div className="fund-analysis-result"><strong>{fundAnalysis.summary}</strong><div><span><b>依据</b>{fundAnalysis.evidence.join('；')}</span><span><b>风险</b>{fundAnalysis.risks.join('；')}</span><span><b>后续</b>{fundAnalysis.next_checks.join('；')}</span></div><small>{fundAnalysis.disclaimer}</small></div>}
      </>}
    </section>}
    <p className="fund-disclaimer">公开净值排行；风格映射仅供研究。</p>
  </section>
}
