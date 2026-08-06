import { BriefcaseBusiness } from 'lucide-react'
import { useEffect } from 'react'
import DecisionReferencePanel from '../components/DecisionReferencePanel.jsx'

export default function DecisionReferencePage({ reference, state, error, onGenerate }) {
  useEffect(() => {
    if (!reference && state === 'idle') onGenerate()
  }, [])

  return <section className="workspace-page decision-reference-page">
    <div className="decision-page-heading"><div><div className="decision-page-kicker"><BriefcaseBusiness size={14} />研究工作台</div><h2>仓位参考</h2><p>板块事实与研究优先级。</p></div></div>
    <DecisionReferencePanel reference={reference} state={state} error={error} onGenerate={onGenerate} />
  </section>
}
