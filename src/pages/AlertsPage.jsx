import { Bell, Clock3 } from 'lucide-react'

export default function AlertsPage({ alertItems, eventsState, setAlertEditorOpen }) {
  return <section className="workspace-page"><div className="workspace-heading"><div><h2>预警中心</h2><p>规则去重，减少干扰。</p></div><button className="primary-button" onClick={() => setAlertEditorOpen(true)}><Bell size={16} />新建预警</button></div><div className="panel alert-list">{alertItems.map((alert) => <div className="alert-list-row" key={alert.id}><span className="alert-time"><Clock3 size={15} />{alert.time}</span><div><strong>{alert.title}</strong><p>{alert.detail}</p></div><span className={`alert-status ${alert.direction === 'down' ? 'risk-alert' : alert.status === '规则触发' ? 'active-alert' : ''}`}>{alert.status}</span></div>)}{alertItems.length === 0 && <div className="empty-state"><Bell size={24} /><p>{eventsState === 'loading' ? '正在读取规则事件' : '尚未有规则事件'}</p></div>}</div></section>
}
