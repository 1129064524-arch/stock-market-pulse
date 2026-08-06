import { Check, CircleAlert, PlugZap, RotateCcw, Save, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'

const emptyForm = {
  base_url: '',
  endpoint: '',
  model: '',
  protocol: 'chat_completions',
  timeout_seconds: 25,
  auto_analysis_enabled: false,
  auto_analysis_minutes: 3,
}

export default function SettingsPage({ onNotice, onSettingsChanged }) {
  const [form, setForm] = useState(emptyForm)
  const [apiKey, setApiKey] = useState('')
  const [status, setStatus] = useState(null)
  const [loadState, setLoadState] = useState('loading')
  const [saveState, setSaveState] = useState('idle')
  const [testState, setTestState] = useState('idle')
  const [error, setError] = useState('')

  const loadSettings = async () => {
    setLoadState('loading')
    try {
      const response = await fetch('/api/llm/settings')
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '设置读取失败')
      setStatus(payload)
      setForm({
        base_url: payload.base_url || '',
        endpoint: payload.endpoint || '',
        model: payload.model || '',
        protocol: payload.protocol || 'chat_completions',
        timeout_seconds: payload.timeout_seconds || 25,
        auto_analysis_enabled: Boolean(payload.auto_analysis_enabled),
        auto_analysis_minutes: payload.auto_analysis_minutes || 3,
      })
      setLoadState('ready')
      setError('')
    } catch (loadError) {
      setLoadState('error')
      setError(loadError.message)
    }
  }

  useEffect(() => { loadSettings() }, [])

  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))

  const save = async (event) => {
    event.preventDefault()
    setSaveState('loading')
    setError('')
    try {
      const response = await fetch('/api/llm/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, api_key: apiKey || 'KEEP_EXISTING' }),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '设置保存失败')
      setStatus(payload)
      setApiKey('')
      setSaveState('success')
      onSettingsChanged?.(payload)
      onNotice?.('模型通道设置已保存')
      window.setTimeout(() => setSaveState('idle'), 2200)
    } catch (saveError) {
      setSaveState('error')
      setError(saveError.message)
    }
  }

  const test = async () => {
    setTestState('loading')
    setError('')
    try {
      const response = await fetch('/api/llm/test', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '模型连接失败')
      setTestState('success')
      onNotice?.(`模型连接正常 · ${payload.model}`)
      window.setTimeout(() => setTestState('idle'), 2500)
    } catch (testError) {
      setTestState('error')
      setError(testError.message)
    }
  }

  const reset = async () => {
    if (!window.confirm('清除本地模型通道配置？')) return
    try {
      const response = await fetch('/api/llm/settings', { method: 'DELETE' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '配置清除失败')
      setStatus(payload)
      setForm(emptyForm)
      setApiKey('')
      setSaveState('idle')
      setTestState('idle')
      onSettingsChanged?.(payload)
      onNotice?.('本地模型通道已清除')
    } catch (resetError) {
      setError(resetError.message)
    }
  }

  return <section className="workspace-page settings-page">
    <div className="settings-intro"><div><h2>工作区设置</h2><p>模型通道与自动统筹。</p></div><span className={`model-status ${status?.configured ? 'connected' : ''}`}>{status?.configured ? '模型通道已配置' : '待配置'}</span></div>
    {loadState === 'loading' && <div className="panel settings-loading">正在读取本地配置…</div>}
    {loadState !== 'loading' && <form className="settings-layout" onSubmit={save}>
      <article className="panel settings-panel">
        <div className="panel-heading compact-heading"><div><h2><PlugZap size={15} />模型通道</h2><p>兼容 Responses / Chat Completions。</p></div><span className="signal-source ready"><ShieldCheck size={13} />本地保存</span></div>
        <div className="settings-fields">
          <label className="settings-field settings-field-wide"><span>基础地址</span><input value={form.base_url} onChange={(event) => update('base_url', event.target.value)} placeholder="https://api.openai.com/v1" autoComplete="off" /><small>兼容模型服务地址。</small></label>
          <label className="settings-field settings-field-wide"><span>完整端点 <em>可选</em></span><input value={form.endpoint} onChange={(event) => update('endpoint', event.target.value)} placeholder="留空则按协议自动拼接" autoComplete="off" /><small>留空时自动使用 `/responses` 或 `/chat/completions`。</small></label>
          <label className="settings-field"><span>协议</span><select value={form.protocol} onChange={(event) => update('protocol', event.target.value)}><option value="chat_completions">Chat Completions</option><option value="responses">Responses</option></select></label>
          <label className="settings-field"><span>模型名称</span><input value={form.model} onChange={(event) => update('model', event.target.value)} placeholder="gpt-4.1-mini" autoComplete="off" /></label>
          <label className="settings-field settings-field-wide"><span>API Key {status?.api_key_masked && <em>当前 {status.api_key_masked}</em>}</span><input type="password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={status?.api_key_set ? '留空保持当前密钥' : '输入模型通道密钥'} autoComplete="new-password" /></label>
          <label className="settings-field"><span>请求超时（秒）</span><input type="number" min="5" max="180" step="1" value={form.timeout_seconds} onChange={(event) => update('timeout_seconds', Number(event.target.value))} /></label>
        </div>
      </article>

      <article className="panel settings-panel automation-panel">
        <div className="panel-heading compact-heading"><div><h2><Check size={15} />自动统筹</h2><p>定时读取市场证据。</p></div></div>
        <div className="automation-control"><label className="switch-row"><span><strong>盘中自动调用模型</strong><small>仅在交易时段运行，不会触发交易操作。</small></span><input type="checkbox" checked={form.auto_analysis_enabled} onChange={(event) => update('auto_analysis_enabled', event.target.checked)} /><i aria-hidden="true" /></label><label className="settings-field"><span>统筹间隔（分钟）</span><input type="number" min="1" max="60" step="1" value={form.auto_analysis_minutes} onChange={(event) => update('auto_analysis_minutes', Number(event.target.value))} /></label></div>
        <div className="settings-safety"><ShieldCheck size={16} /><div><strong>研究边界</strong><p>只解释本地数据，不生成交易指令。</p></div></div>
      </article>

      <div className="settings-actions"><button type="button" className="detail-button" onClick={test} disabled={testState === 'loading' || !status?.configured}><PlugZap size={15} />{testState === 'loading' ? '测试中' : testState === 'success' ? '连接正常' : '测试连接'}</button><button type="button" className="text-button settings-reset" onClick={reset}><RotateCcw size={14} />清除配置</button><button type="submit" className="primary-button" disabled={saveState === 'loading'}><Save size={15} />{saveState === 'loading' ? '保存中' : saveState === 'success' ? '已保存' : '保存设置'}</button></div>
      {error && <div className="settings-error"><CircleAlert size={16} /><span>{error}</span></div>}
      <p className="settings-path">配置文件：{status?.config_path || '.env'} · 当前设置只作用于本机 API 服务。</p>
    </form>}
  </section>
}
