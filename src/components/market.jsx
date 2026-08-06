import { ArrowDownRight, ArrowUpRight } from 'lucide-react'

export const movers = [
  { code: '300308', name: '中际旭创', price: '184.62', change: '+8.41%', volume: '3.8x', sector: '通信设备', score: 91, direction: 'up', signal: '放量突破', note: '突破 20 日高点，所属板块同步走强', risk: '短线乖离偏高' },
  { code: '688256', name: '寒武纪-U', price: '612.80', change: '+6.73%', volume: '2.9x', sector: '半导体', score: 87, direction: 'up', signal: '资金共振', note: '主力净流入连续 3 个交易日', risk: '波动率高于均值' },
  { code: '002230', name: '科大讯飞', price: '54.36', change: '+5.18%', volume: '2.4x', sector: 'AI 应用', score: 84, direction: 'up', signal: '趋势转强', note: '5 日线上穿 20 日线，板块排名提升', risk: '上方年线压力' },
  { code: '601127', name: '赛力斯', price: '118.40', change: '-4.26%', volume: '2.1x', sector: '汽车整车', score: 79, direction: 'down', signal: '高位放量', note: '跌破短期均线，资金流出加速', risk: '趋势待确认' },
  { code: '159995', name: '芯片 ETF', price: '1.142', change: '+2.34%', volume: '1.8x', sector: 'ETF', score: 75, direction: 'up', signal: '板块转强', note: '半导体成交额升至全市场第 3', risk: '受龙头波动影响' },
  { code: '600519', name: '贵州茅台', price: '1518.21', change: '-1.64%', volume: '1.5x', sector: '白酒', score: 62, direction: 'down', signal: '资金背离', note: '指数反弹但个股资金持续流出', risk: '防御板块承压' },
]

export const sectors = [
  { name: '通信设备', change: '+4.82%', stocks: '18 / 42', amount: '284 亿', direction: 'up' },
  { name: '半导体', change: '+3.67%', stocks: '96 / 174', amount: '516 亿', direction: 'up' },
  { name: 'AI 应用', change: '+2.91%', stocks: '73 / 126', amount: '193 亿', direction: 'up' },
  { name: '汽车整车', change: '-1.22%', stocks: '8 / 31', amount: '98 亿', direction: 'down' },
]

export const fallbackIndices = [
  { name: '上证指数', value: '3,421.36', change: '+0.68%', direction: 'up' },
  { name: '深证成指', value: '10,824.19', change: '+1.12%', direction: 'up' },
  { name: '创业板指', value: '2,241.80', change: '+1.84%', direction: 'up' },
]

export const ruleLabels = {
  volume_breakout: '量价突破',
  sector_resonance: '板块共振',
  daily_trend: '日线趋势向上',
  risk_breakdown: '下行风险',
}

export function alertTime(value) {
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? '--:--' : date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

export function PriceMark({ direction, children }) {
  return <span className={`price ${direction}`}>{direction === 'up' ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{children}</span>
}

export function DailyChart({ code, bars }) {
  const chartBars = bars.slice(-30).map((bar) => {
    const close = Number(bar.close)
    const open = Number(bar.open)
    const high = Number(bar.high)
    const low = Number(bar.low)
    if (!Number.isFinite(close)) return null
    const safeOpen = Number.isFinite(open) ? open : close
    return {
      open: safeOpen,
      close,
      high: Number.isFinite(high) ? high : Math.max(safeOpen, close),
      low: Number.isFinite(low) ? low : Math.min(safeOpen, close),
    }
  }).filter(Boolean)
  if (chartBars.length < 2) return <div className="daily-chart-empty">同步日线后显示近 30 个交易日 K 线</div>

  const minimum = Math.min(...chartBars.map((bar) => bar.low))
  const maximum = Math.max(...chartBars.map((bar) => bar.high))
  const range = Math.max(maximum - minimum, Math.abs(maximum) * 0.015, 0.01)
  const plotTop = 14
  const plotBottom = 148
  const yFor = (value) => plotBottom - ((value - minimum) / range) * (plotBottom - plotTop)
  const step = 492 / Math.max(chartBars.length - 1, 1)
  const candleWidth = Math.max(4, Math.min(11, step * 0.56))
  const lastBar = chartBars.at(-1)
  const lastX = 14 + (chartBars.length - 1) * step
  const lastY = yFor(lastBar.close)

  return <div className="daily-chart-wrap"><svg className="daily-chart candles" viewBox="0 0 520 184" role="img" aria-label={`${code} 近 ${chartBars.length} 个交易日 K 线`}><path className="chart-grid" d="M0 14H520M0 81H520M0 148H520" /><line className="chart-axis" x1="0" y1="160" x2="520" y2="160" /><line className="last-price-line" x1="0" y1={lastY} x2="520" y2={lastY} /><g>{chartBars.map((bar, index) => { const x = 14 + index * step; const openY = yFor(bar.open); const closeY = yFor(bar.close); const direction = bar.close >= bar.open ? 'up' : 'down'; return <g key={`${bar.close}-${index}`}><line className={`candle-wick ${direction}`} x1={x} y1={yFor(bar.high)} x2={x} y2={yFor(bar.low)} /><rect className={`candle-body ${direction}`} x={x - candleWidth / 2} y={Math.min(openY, closeY)} width={candleWidth} height={Math.max(2, Math.abs(closeY - openY))} /></g> })}</g><circle className="last-price-dot" cx={lastX} cy={lastY} r="3" /></svg><span>K 线 · 本地已同步 {chartBars.length} 个交易日 · 最新 {lastBar.close.toFixed(2)}</span></div>
}

export function signalResearchPayload(stock, overview) {
  return {
    signal: {
      code: stock.code,
      name: stock.name,
      rule_name: stock.rule_name || 'market_mover',
      rule_label: stock.rule_label || stock.signal || '市场异动',
      rule_version: stock.rule_version || 'v1',
      score: Number(stock.score || 0),
      evidence: stock.evidence || stock.note || '当前行情出现异动',
      risk: stock.risk || '数据有限，需持续观察',
      triggered_at: stock.triggered_at || overview?.as_of || new Date().toISOString(),
      source: stock.source || overview?.source || 'market_pulse',
      price: String(stock.price || '--'),
      change: String(stock.change || '--'),
      sector: stock.sector || '未分类',
      direction: stock.direction === 'down' ? 'down' : 'up',
      volume: String(stock.volume || '--'),
    },
  }
}
