import { Check, Filter, PieChart, RefreshCw, Star } from 'lucide-react'
import { PriceMark } from '../components/market.jsx'

export default function FundsPage({ funds, universeCount, categoryCounts, fundsState, fundSource, fundWatchlist, onlyMine, setOnlyMine, refreshFunds, toggleFundWatch }) {
  const visibleFunds = onlyMine ? funds.filter((fund) => fundWatchlist.includes(fund.code)) : funds
  const positiveCount = funds.filter((fund) => fund.direction === 'up').length
  const negativeCount = funds.filter((fund) => fund.direction === 'down').length
  const totalLabel = universeCount ? universeCount.toLocaleString() : '--'

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
        return <div className="fund-list-row" key={fund.code}>
          <div className="fund-identity"><strong>{fund.name}</strong><small>{fund.code} · {fund.nav_date}</small></div>
          <div><span className="fund-type">{fund.fund_type}</span><small>{fund.theme}</small></div>
          <div className="fund-values"><strong>{fund.nav}</strong><small>确认净值</small></div>
          <div className="fund-return"><PriceMark direction={fund.direction}>{fund.change}</PriceMark><small>周 {fund.week_change}</small></div>
          <div className="fund-period"><strong>月 {fund.month_change}</strong><small>年 {fund.year_change}</small></div>
          <div className="fund-signal"><span className={`signal-chip ${fund.direction}`}>{fund.signal}</span><small>{fund.risk}</small></div>
          <button className={`fund-watch-toggle ${watched ? 'watched' : ''}`} aria-label={watched ? `取消观察 ${fund.name}` : `加入观察 ${fund.name}`} onClick={() => toggleFundWatch(fund)}>{watched ? <Check size={15} /> : <Star size={15} />}</button>
        </div>
      })}
      {visibleFunds.length === 0 && <div className="empty-state"><PieChart size={24} /><p>还没有加入观察的基金</p><button onClick={() => setOnlyMine(false)}>查看全市场基金</button></div>}
    </div>
    <p className="fund-disclaimer">公开净值排行；风格映射仅供研究。</p>
  </section>
}
