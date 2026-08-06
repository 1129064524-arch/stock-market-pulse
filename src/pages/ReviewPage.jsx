import { LineChart } from 'lucide-react'

export default function ReviewPage({ showNotice }) {
  return <section className="workspace-page"><div className="workspace-heading"><div><h2>盘后复盘</h2><p>当日结构与次日验证。</p></div><button className="filter-button" onClick={() => showNotice('盘后总结已刷新')}><LineChart size={15} />刷新总结</button></div><div className="review-grid"><article className="panel review-note"><h3>市场结构</h3><strong>成长风格占优，半导体与通信设备是主要强势方向。</strong><p>上涨家数明显领先，北向资金盘中净流入，强势板块的成交额同步放大。</p></article><article className="panel review-note"><h3>明日验证</h3><strong>观察强势板块能否维持量价配合。</strong><p>重点关注高置信度信号在早盘是否出现放量承接，避免追逐高乖离标的。</p></article><article className="panel review-note"><h3>风险记录</h3><strong>汽车整车板块仍偏弱。</strong><p>对于波动率显著高于均值的个股，保持风险提示，不以单一技术信号下结论。</p></article></div></section>
}
