import { AlertCircle, Clock3, LineChart, RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'

export default function ReviewPage({ showNotice }) {
  const [history, setHistory] = useState([])
  const [state, setState] = useState('loading')
  const loadHistory = () => {
    setState('loading')
    fetch('/api/v1/analysis/history?limit=12').then((response) => response.ok ? response.json() : Promise.reject(new Error('history'))).then((payload) => { setHistory(payload); setState('ready') }).catch(() => setState('error'))
  }
  useEffect(() => { loadHistory() }, [])
  return <section className="workspace-page"><div className="workspace-heading"><div><h2>盘后复盘</h2><p>当日结构与次日验证。</p></div><button className="filter-button" onClick={() => { loadHistory(); showNotice('研判记录已刷新') }} disabled={state === 'loading'}><RefreshCw className={state === 'loading' ? 'loading-icon' : ''} size={15} />刷新记录</button></div><div className="review-grid"><article className="panel review-note"><h3>市场结构</h3><strong>成长风格占优，半导体与通信设备是主要强势方向。</strong><p>上涨家数明显领先，北向资金盘中净流入，强势板块的成交额同步放大。</p></article><article className="panel review-note"><h3>明日验证</h3><strong>观察强势板块能否维持量价配合。</strong><p>重点关注高置信度信号在早盘是否出现放量承接，避免追逐高乖离标的。</p></article><article className="panel review-note"><h3>风险记录</h3><strong>汽车整车板块仍偏弱。</strong><p>对于波动率显著高于均值的个股，保持风险提示，不以单一技术信号下结论。</p></article></div><section className="panel review-history"><div className="review-history-heading"><div><h3>模型研判记录</h3><p>只展示本地保存的研究结果，不代表实时行情。</p></div><span>{history.length} 条</span></div>{state === 'error' && <div className="review-history-empty"><AlertCircle size={16} />暂时无法读取记录</div>}{state === 'ready' && history.length === 0 && <div className="review-history-empty"><Clock3 size={16} />尚无保存的模型研判</div>}{state === 'ready' && history.length > 0 && <div className="review-history-list">{history.map((item, index) => <article key={`${item.kind}-${item.generated_at}-${index}`}><div><strong>{item.kind.startsWith('fund:') ? `基金 ${item.kind.slice(5)}` : item.kind === 'cross-market' ? '跨市场研判' : item.kind}</strong><time>{new Date(item.generated_at).toLocaleString('zh-CN')}</time></div><p>{item.summary || item.disclaimer || '已保存研究结果'}</p></article>)}</div>}</section></section>
}
