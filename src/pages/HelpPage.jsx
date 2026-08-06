import { Activity, BrainCircuit, CircleHelp, PieChart, Settings2, Sparkles } from 'lucide-react'

const sections = [
  { icon: Activity, title: '跨市场总览', text: '股票、基金、联动。' },
  { icon: Sparkles, title: '信号池', text: '筛选高置信度异动。' },
  { icon: PieChart, title: '基金全景', text: '扫描全市场净值。' },
  { icon: BrainCircuit, title: 'AI 研判', text: '生成证据与风险清单。' },
  { icon: Settings2, title: '模型设置', text: '配置协议、模型和密钥。' },
]

export default function HelpPage({ setActiveNav }) {
  return <section className="workspace-page help-page">
    <div className="help-intro"><div><h2>工作区说明</h2><p>扫描 → 核对 → 研究。</p></div><CircleHelp size={20} /></div>
    <div className="help-grid">{sections.map(({ icon: Icon, title, text }) => <article className="panel help-item" key={title}><Icon size={17} /><div><h3>{title}</h3><p>{text}</p></div></article>)}</div>
    <article className="panel help-boundary"><div><strong>数据与模型边界</strong><p>行情来自本地 API；模型只读快照。</p></div><button className="detail-button" onClick={() => setActiveNav('设置')}><Settings2 size={14} />打开设置</button></article>
  </section>
}
