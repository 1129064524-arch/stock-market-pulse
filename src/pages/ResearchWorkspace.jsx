import { AlertTriangle, BrainCircuit, RefreshCw } from 'lucide-react'

export default function ResearchWorkspace({
  llmConfigured,
  llmProtocol,
  analysisState,
  analysis,
  analysisError,
  generateAnalysis,
  selected,
  signalAnalysisState,
  signalAnalysis,
  signalAnalysisError,
  generateSignalAnalysis,
}) {
  return <section className="workspace-page research-workspace">
    <div className="workspace-heading">
      <div><h2>研究任务</h2><p>证据与风险核对。</p></div>
      <span className={`model-status ${llmConfigured ? 'connected' : ''}`}>{llmConfigured ? (llmProtocol === 'responses' ? 'Responses 通道已配置' : '模型已配置') : '待配置'}</span>
    </div>
    <div className="research-layout">
      <article className="panel market-research">
        <div className="panel-heading compact-heading"><div><h2>市场快照</h2><p>结构与风险</p></div><button className="primary-button" onClick={generateAnalysis} disabled={analysisState === 'loading'}>{analysisState === 'loading' ? <><RefreshCw className="loading-icon" size={15} />正在分析</> : <><BrainCircuit size={15} />{analysis ? '重新生成' : '生成市场研判'}</>}</button></div>
        {analysisState === 'success' && analysis ? <div className="analysis-result research-result"><div className={`stance ${analysis.stance}`}>{analysis.stance}</div><div className="analysis-summary"><strong>{analysis.summary}</strong><span>{analysis.disclaimer}</span></div><div className="analysis-column"><h3>观察依据</h3><ul>{analysis.evidence.map((item) => <li key={item}>{item}</li>)}</ul></div><div className="analysis-column risk-column"><h3>已知风险</h3><ul>{analysis.risks.map((item) => <li key={item}>{item}</li>)}</ul></div><div className="analysis-column watch-column"><h3>继续跟踪</h3><ul>{analysis.watchlist.map((item) => <li key={item.code}><strong>{item.name}</strong><span>{item.reason}</span></li>)}</ul></div></div> : <div className={`analysis-empty ${analysisState === 'error' ? 'error' : ''}`}><BrainCircuit size={22} /><div><strong>{analysisState === 'error' ? '无法生成研判' : '等待生成市场研判'}</strong><p>{analysisState === 'error' ? analysisError : llmConfigured ? '生成后会把当前快照拆成证据、风险和继续跟踪项。' : '在 .env 中配置兼容模型地址、密钥和模型名称。'}</p></div></div>}
      </article>
      <article className="panel signal-research-workspace">
        <div className="panel-heading compact-heading"><div><h2>单条信号</h2><p>{selected.name} · {selected.code} · {selected.signal}</p></div><span className="signal-source ready">置信度 {selected.score}</span></div>
        <div className="research-signal-summary"><strong>{selected.name}</strong><span>{selected.sector} · {selected.price} · {selected.change}</span><p>{selected.note}</p><small><AlertTriangle size={13} />风险：{selected.risk}</small></div>
        <button className="signal-ai-button" onClick={generateSignalAnalysis} disabled={signalAnalysisState === 'loading'}><BrainCircuit size={16} />{signalAnalysisState === 'loading' ? '正在解读' : signalAnalysis ? '重新解读此信号' : '生成信号研究清单'}</button>
        {signalAnalysisState === 'success' && signalAnalysis ? <div className="signal-research-result"><strong>{signalAnalysis.summary}</strong><div className="signal-research-grid"><ResearchList title="触发原因" items={signalAnalysis.why_now} /><ResearchList title="后续确认" items={signalAnalysis.confirmations} /><ResearchList title="失效条件" items={signalAnalysis.invalidations} /><ResearchList title="下一交易日" items={signalAnalysis.next_session_checklist} /></div><p><AlertTriangle size={13} />{signalAnalysis.risks.join('；')}<span>{signalAnalysis.disclaimer}</span></p></div> : signalAnalysisState === 'error' ? <p className="signal-research-error">{signalAnalysisError}</p> : <div className="research-empty">从信号池选择一个标的，再生成针对性的研究清单。</div>}
      </article>
    </div>
  </section>
}

function ResearchList({ title, items }) {
  return <div><h3>{title}</h3><ul>{items.map((item) => <li key={item}>{item}</li>)}</ul></div>
}
