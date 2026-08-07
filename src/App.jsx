import { useEffect, useMemo, useState } from 'react'
import {
  Bell,
  CircleHelp,
  Filter,
  Menu,
  RefreshCw,
} from 'lucide-react'
import { alertTime, fallbackIndices, movers, ruleLabels, sectors, signalResearchPayload } from './components/market.jsx'
import Sidebar from './components/Sidebar.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import CrossMarketPage from './pages/CrossMarketPage.jsx'
import DecisionReferencePage from './pages/DecisionReferencePage.jsx'
import FundsPage from './pages/FundsPage.jsx'
import HelpPage from './pages/HelpPage.jsx'
import MarketRadar from './pages/MarketRadar.jsx'
import ResearchWorkspace from './pages/ResearchWorkspace.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import SignalPoolPage from './pages/SignalPoolPage.jsx'
import SettingsPage from './pages/SettingsPage.jsx'
import WatchlistPage from './pages/WatchlistPage.jsx'

function App() {
  const [theme, setTheme] = useState(() => window.localStorage.getItem('market-pulse-theme') || 'light')
  const [activeNav, setActiveNav] = useState('跨市场总览')
  const [market, setMarket] = useState('全部市场')
  const [query, setQuery] = useState('')
  const [onlyStrong, setOnlyStrong] = useState(false)
  const [selected, setSelected] = useState(movers[0])
  const [menuOpen, setMenuOpen] = useState(false)
  const [liveMovers, setLiveMovers] = useState(movers)
  const [liveSectors, setLiveSectors] = useState(sectors)
  const [liveOverview, setLiveOverview] = useState(null)
  const [funds, setFunds] = useState([])
  const [fundUniverseCount, setFundUniverseCount] = useState(0)
  const [fundCategoryCounts, setFundCategoryCounts] = useState({})
  const [fundsState, setFundsState] = useState('idle')
  const [fundSource, setFundSource] = useState('sample')
  const [selectedFund, setSelectedFund] = useState(null)
  const [fundHoldings, setFundHoldings] = useState([])
  const [fundLinkedStocks, setFundLinkedStocks] = useState([])
  const [fundHoldingsState, setFundHoldingsState] = useState('idle')
  const [fundHoldingsError, setFundHoldingsError] = useState('')
  const [fundAnalysis, setFundAnalysis] = useState(null)
  const [fundAnalysisState, setFundAnalysisState] = useState('idle')
  const [fundAnalysisError, setFundAnalysisError] = useState('')
  const [linkage, setLinkage] = useState(null)
  const [linkageState, setLinkageState] = useState('idle')
  const [onlyMineFunds, setOnlyMineFunds] = useState(false)
  const [apiAvailable, setApiAvailable] = useState(false)
  const [ruleSignals, setRuleSignals] = useState([])
  const [signalsState, setSignalsState] = useState('idle')
  const [signalEvents, setSignalEvents] = useState([])
  const [eventsState, setEventsState] = useState('idle')
  const [refreshingMarket, setRefreshingMarket] = useState(false)
  const [dailyIndicators, setDailyIndicators] = useState(null)
  const [dailyBars, setDailyBars] = useState([])
  const [syncingHistory, setSyncingHistory] = useState(false)
  const [llmConfigured, setLlmConfigured] = useState(false)
  const [llmProtocol, setLlmProtocol] = useState('chat_completions')
  const [analysis, setAnalysis] = useState(null)
  const [analysisState, setAnalysisState] = useState('idle')
  const [analysisError, setAnalysisError] = useState('')
  const [crossAnalysis, setCrossAnalysis] = useState(null)
  const [crossAnalysisState, setCrossAnalysisState] = useState('idle')
  const [crossAnalysisError, setCrossAnalysisError] = useState('')
  const [decisionReference, setDecisionReference] = useState(null)
  const [decisionState, setDecisionState] = useState('idle')
  const [decisionError, setDecisionError] = useState('')
  const [signalAnalysis, setSignalAnalysis] = useState(null)
  const [signalAnalysisState, setSignalAnalysisState] = useState('idle')
  const [signalAnalysisError, setSignalAnalysisError] = useState('')
  const [focusOpen, setFocusOpen] = useState(true)
  const [watchlist, setWatchlist] = useState(() => {
    try { return JSON.parse(window.localStorage.getItem('market-pulse-watchlist') || '[]') } catch { return [] }
  })
  const [fundWatchlist, setFundWatchlist] = useState(() => {
    try { return JSON.parse(window.localStorage.getItem('market-pulse-fund-watchlist') || '[]') } catch { return [] }
  })
  const [alerts, setAlerts] = useState([{ id: 'seed-alert', time: '10:58', title: '半导体板块成交额快速放大', detail: '10 分钟内增幅 38%，龙头同步走强', status: '已读' }])
  const [alertEditorOpen, setAlertEditorOpen] = useState(false)
  const [alertDraft, setAlertDraft] = useState({ rule: '涨跌幅突破', threshold: '5' })
  const [notice, setNotice] = useState('')

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('market-pulse-theme', theme)
  }, [theme])

  useEffect(() => {
    const destinations = ['跨市场总览', '股票雷达', '基金全景', '信号池', '自选观察', 'AI 研判', '仓位参考', '预警中心', '盘后复盘']
    const handleShortcut = (event) => {
      if (!event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
      const index = Number(event.key) - 1
      if (index >= 0 && index < destinations.length) {
        event.preventDefault()
        setActiveNav(destinations[index])
      }
    }
    window.addEventListener('keydown', handleShortcut)
    return () => window.removeEventListener('keydown', handleShortcut)
  }, [])

  useEffect(() => {
    let active = true

    fetch('/api/market/overview')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Market API unavailable')))
      .then((snapshot) => {
        if (!active) return
        setLiveMovers(snapshot.movers)
        setLiveSectors(snapshot.sectors)
        setLiveOverview(snapshot)
        setSelected((current) => snapshot.movers.find((stock) => stock.code === current.code) || snapshot.movers[0] || current)
        setApiAvailable(true)
      })
      .catch(() => {
        if (active) setApiAvailable(false)
      })

    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    setFundsState('loading')
    fetch('/api/funds/overview')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Funds API unavailable')))
      .then((payload) => {
        if (!active) return
        setFunds(payload.funds || [])
        setFundUniverseCount(payload.universe_count || 0)
        setFundCategoryCounts(payload.category_counts || {})
        setFundSource(payload.source || 'sample')
        setFundsState('ready')
      })
      .catch(() => { if (active) setFundsState('error') })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!liveOverview?.as_of || funds.length === 0) return undefined
    let active = true
    setLinkageState('loading')
    fetch('/api/linkage/overview')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Linkage API unavailable')))
      .then((payload) => {
        if (!active) return
        setLinkage(payload)
        setLinkageState('ready')
      })
      .catch(() => { if (active) setLinkageState('error') })
    return () => { active = false }
  }, [liveOverview?.as_of, funds.length, fundSource])

  useEffect(() => {
    if (!liveOverview?.as_of) return undefined
    let active = true
    setSignalsState('loading')
    fetch('/api/signals/current')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Signals unavailable')))
      .then((signals) => {
        if (!active) return
        setRuleSignals(signals)
        setSignalsState('ready')
      })
      .catch(() => {
        if (active) setSignalsState('error')
      })
    return () => { active = false }
  }, [liveOverview?.as_of])

  useEffect(() => {
    if (!liveOverview?.as_of) return undefined
    let active = true
    setEventsState('loading')
    fetch('/api/signals/history?limit=40')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('Alert history unavailable')))
      .then((payload) => {
        if (!active) return
        setSignalEvents(payload.events || [])
        setEventsState('ready')
      })
      .catch(() => {
        if (active) setEventsState('error')
      })
    return () => { active = false }
  }, [liveOverview?.as_of])

  useEffect(() => {
    let active = true
    setDailyIndicators(null)
    setDailyBars([])
    fetch(`/api/stocks/${selected.code}/daily-bars?limit=60`)
      .then((response) => response.ok ? response.json() : null)
      .then((payload) => {
        if (active && payload?.indicators?.samples) {
          setDailyIndicators(payload.indicators)
          setDailyBars(payload.bars || [])
        }
      })
      .catch(() => {})
    return () => { active = false }
  }, [selected.code])

  useEffect(() => {
    window.localStorage.setItem('market-pulse-watchlist', JSON.stringify(watchlist))
  }, [watchlist])

  useEffect(() => {
    window.localStorage.setItem('market-pulse-fund-watchlist', JSON.stringify(fundWatchlist))
  }, [fundWatchlist])

  useEffect(() => {
    Promise.all([
      fetch('/api/v1/watchlist/stock').then((response) => response.ok ? response.json() : []),
      fetch('/api/v1/watchlist/fund').then((response) => response.ok ? response.json() : []),
    ]).then(([stocks, savedFunds]) => {
      if (stocks.length) setWatchlist((current) => [...current, ...stocks.filter((item) => !current.some((existing) => existing.code === item.code))])
      if (savedFunds.length) setFundWatchlist((current) => [...new Set([...current, ...savedFunds.map((item) => item.code)])])
    }).catch(() => {})
  }, [])

  const showNotice = (message) => {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 2600)
  }

  const toggleWatch = (stock = selected) => {
    setWatchlist((current) => {
      const exists = current.some((item) => item.code === stock.code)
      fetch(`/api/v1/watchlist/stock/${stock.code}`, exists ? { method: 'DELETE' } : { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: stock.name }) }).catch(() => {})
      showNotice(exists ? `已移除 ${stock.name}` : `已加入 ${stock.name}`)
      return exists ? current.filter((item) => item.code !== stock.code) : [...current, stock]
    })
  }

  const toggleFundWatch = (fund) => {
    setFundWatchlist((current) => {
      const exists = current.includes(fund.code)
      fetch(`/api/v1/watchlist/fund/${fund.code}`, exists ? { method: 'DELETE' } : { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: fund.name }) }).catch(() => {})
      showNotice(exists ? `已移除 ${fund.name}` : `已加入 ${fund.name}`)
      return exists ? current.filter((code) => code !== fund.code) : [...current, fund.code]
    })
  }

  const refreshFunds = async () => {
    setFundsState('loading')
    try {
      const response = await fetch('/api/funds/refresh', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error('基金估值刷新失败')
      setFunds(payload.funds || [])
      setFundUniverseCount(payload.universe_count || 0)
      setFundCategoryCounts(payload.category_counts || {})
      setFundSource(payload.source || 'sample')
      setFundsState('ready')
      showNotice(payload.source === 'eastmoney' ? '基金全市场净值榜已刷新' : '基金数据源暂不可用，已显示演示数据')
    } catch {
      setFundsState('error')
      showNotice('基金估值刷新失败，请稍后重试')
    }
  }

  const openFundHoldings = async (fund) => {
    if (selectedFund?.code === fund.code && fundHoldingsState === 'ready') return
    setSelectedFund(fund)
    setFundHoldings([])
    setFundLinkedStocks([])
    setFundAnalysis(null)
    setFundAnalysisState('idle')
    setFundHoldingsError('')
    setFundHoldingsState('loading')
    try {
      const [holdingsResponse, linkedResponse, analysisResponse] = await Promise.all([
        fetch(`/api/v1/funds/${fund.code}/holdings`),
        fetch(`/api/v1/linkage/fund/${fund.code}/stocks`),
        fetch(`/api/v1/analysis/funds/${fund.code}/latest`),
      ])
      const holdingsPayload = await holdingsResponse.json()
      const linkedPayload = await linkedResponse.json()
      if (!holdingsResponse.ok) throw new Error(holdingsPayload?.detail?.message || '季报持仓暂不可用')
      if (!linkedResponse.ok) throw new Error(linkedPayload?.detail?.message || '穿透行情暂不可用')
      setFundHoldings(holdingsPayload || [])
      setFundLinkedStocks(linkedPayload || [])
      if (analysisResponse.ok) {
        setFundAnalysis(await analysisResponse.json())
        setFundAnalysisState('success')
      }
      setFundHoldingsState('ready')
    } catch (error) {
      setFundHoldingsError(error.message || '持仓数据加载失败')
      setFundHoldingsState('error')
    }
  }

  const closeFundHoldings = () => {
    setSelectedFund(null)
    setFundHoldings([])
    setFundLinkedStocks([])
    setFundAnalysis(null)
    setFundAnalysisState('idle')
    setFundHoldingsError('')
    setFundHoldingsState('idle')
  }

  const analyzeFund = async () => {
    if (!selectedFund) return
    setFundAnalysisState('loading')
    setFundAnalysisError('')
    try {
      const response = await fetch(`/api/v1/analysis/funds/${selectedFund.code}`, { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload?.detail?.message || '暂时无法生成基金研判')
      setFundAnalysis(payload)
      setFundAnalysisState('success')
    } catch (error) {
      setFundAnalysisError(error.message)
      setFundAnalysisState('error')
    }
  }

  const openStock = (stock) => {
    setSelected({ ...stock, signal: stock.rule_label || stock.signal, note: stock.evidence || stock.note })
    setFocusOpen(true)
    setActiveNav('股票雷达')
  }

  const createAlert = (event) => {
    event.preventDefault()
    const threshold = Number(alertDraft.threshold)
    if (!Number.isFinite(threshold) || threshold <= 0) {
      showNotice('请输入有效的预警阈值')
      return
    }
    setAlerts((current) => [{
      id: `${selected.code}-${Date.now()}`,
      time: '刚刚',
      title: `${selected.name} · ${alertDraft.rule}`,
      detail: `当阈值达到 ${threshold}% 时提醒`,
      status: '启用中',
    }, ...current])
    setAlertEditorOpen(false)
    setActiveNav('预警中心')
    showNotice('预警已创建')
  }

  useEffect(() => {
    fetch('/api/llm/status')
      .then((response) => response.ok ? response.json() : { configured: false })
      .then((status) => {
        setLlmConfigured(status.configured)
        setLlmProtocol(status.protocol || 'chat_completions')
      })
      .catch(() => setLlmConfigured(false))
  }, [])

  useEffect(() => {
    let active = true
    const loadLatestCrossAnalysis = () => {
      fetch('/api/analysis/cross-market/latest')
        .then((response) => response.ok ? response.json() : null)
        .then((payload) => {
          if (!active || !payload) return
          setCrossAnalysis(payload)
          setCrossAnalysisState('success')
          setCrossAnalysisError('')
        })
        .catch(() => {})
    }
    loadLatestCrossAnalysis()
    const interval = window.setInterval(loadLatestCrossAnalysis, 60_000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [])

  const generateAnalysis = async () => {
    setAnalysisState('loading')
    setAnalysisError('')

    try {
      const response = await fetch('/api/analysis/market', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '暂时无法生成分析')
      setAnalysis(payload)
      setAnalysisState('success')
    } catch (error) {
      setAnalysisState('error')
      setAnalysisError(error.message)
    }
  }

  const generateCrossAnalysis = async () => {
    setCrossAnalysisState('loading')
    setCrossAnalysisError('')
    try {
      const response = await fetch('/api/analysis/cross-market', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '暂时无法生成跨市场研判')
      setCrossAnalysis(payload)
      setCrossAnalysisState('success')
    } catch (error) {
      setCrossAnalysisState('error')
      setCrossAnalysisError(error.message)
    }
  }

  const generateDecisionReference = async () => {
    setDecisionState('loading')
    setDecisionError('')
    try {
      const response = await fetch('/api/analysis/decision-reference', { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '暂时无法生成仓位决策参考')
      setDecisionReference(payload)
      setDecisionState('success')
    } catch (error) {
      setDecisionState('error')
      setDecisionError(error.message)
    }
  }

  const generateSignalAnalysis = async () => {
    setActiveNav('AI 研判')
    setSignalAnalysisState('loading')
    setSignalAnalysisError('')

    try {
      const response = await fetch('/api/analysis/signals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signalResearchPayload(selected, liveOverview)),
      })
      const payload = await response.json()
      if (!response.ok) throw new Error(payload.detail?.message || '暂时无法生成信号解读')
      setSignalAnalysis(payload)
      setSignalAnalysisState('success')
    } catch (error) {
      setSignalAnalysisState('error')
      setSignalAnalysisError(error.message)
    }
  }

  useEffect(() => {
    setSignalAnalysis(null)
    setSignalAnalysisState('idle')
    setSignalAnalysisError('')
  }, [selected.code, selected.rule_name, selected.evidence, selected.note])

  const refreshMarket = async () => {
    setRefreshingMarket(true)
    try {
      const response = await fetch('/api/market/refresh', { method: 'POST' })
      const snapshot = await response.json()
      if (!response.ok) throw new Error('刷新失败')
      setLiveMovers(snapshot.movers)
      setLiveSectors(snapshot.sectors)
      setLiveOverview(snapshot)
      setSelected((current) => snapshot.movers.find((stock) => stock.code === current.code) || snapshot.movers[0] || current)
      setApiAvailable(true)
      showNotice(['akshare', 'eastmoney'].includes(snapshot.source) ? '实时行情已刷新' : '数据源暂不可用，已显示缓存数据')
    } catch {
      showNotice('行情刷新失败，请稍后重试')
    } finally {
      setRefreshingMarket(false)
    }
  }

  useEffect(() => {
    let active = true
    let polling = false
    let controller

    const pollLatestSnapshots = async () => {
      if (document.visibilityState === 'hidden' || polling) return
      polling = true
      controller?.abort()
      controller = new AbortController()
      const requestOptions = { signal: controller.signal }
      const [marketResult, fundsResult, signalsResult, linkageResult] = await Promise.allSettled([
        fetch('/api/market/overview', requestOptions),
        fetch('/api/funds/overview', requestOptions),
        fetch('/api/signals/current', requestOptions),
        fetch('/api/linkage/overview', requestOptions),
      ])
      polling = false
      if (!active) return

      if (marketResult.status === 'fulfilled' && marketResult.value.ok) {
        const snapshot = await marketResult.value.json()
        setLiveMovers(snapshot.movers || [])
        setLiveSectors(snapshot.sectors || [])
        setLiveOverview(snapshot)
        setSelected((current) => {
          const next = snapshot.movers?.find((stock) => stock.code === current.code) || snapshot.movers?.[0] || current
          return next.code === current.code && next.price === current.price && next.change === current.change ? current : next
        })
        setApiAvailable(true)
      }
      if (fundsResult.status === 'fulfilled' && fundsResult.value.ok) {
        const payload = await fundsResult.value.json()
        setFunds(payload.funds || [])
        setFundUniverseCount(payload.universe_count || 0)
        setFundCategoryCounts(payload.category_counts || {})
        setFundSource(payload.source || 'sample')
        setFundsState('ready')
      }
      if (signalsResult.status === 'fulfilled' && signalsResult.value.ok) {
        setRuleSignals(await signalsResult.value.json())
        setSignalsState('ready')
      }
      if (linkageResult.status === 'fulfilled' && linkageResult.value.ok) {
        setLinkage(await linkageResult.value.json())
        setLinkageState('ready')
      }
    }

    const interval = window.setInterval(pollLatestSnapshots, 60_000)
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') pollLatestSnapshots()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      active = false
      controller?.abort()
      window.clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [])

  const syncDailyHistory = async () => {
    setSyncingHistory(true)
    try {
      const response = await fetch(`/api/stocks/${selected.code}/daily-history?limit=60`, { method: 'POST' })
      const payload = await response.json()
      if (!response.ok) throw new Error('日线同步失败')
      const indicatorsResponse = await fetch(`/api/stocks/${selected.code}/daily-bars?limit=60`)
      const indicatorsPayload = await indicatorsResponse.json()
      setDailyIndicators(indicatorsPayload.indicators)
      setDailyBars(indicatorsPayload.bars || [])
      showNotice(`已同步 ${payload.bars.length} 个交易日日线`)
    } catch {
      showNotice('日线同步失败，请稍后重试')
    } finally {
      setSyncingHistory(false)
    }
  }

  const filteredMovers = useMemo(() => liveMovers.filter((stock) => {
    const queryMatch = `${stock.name}${stock.code}${stock.sector}`.toLowerCase().includes(query.toLowerCase())
    return queryMatch && (!onlyStrong || stock.score >= 80)
  }), [liveMovers, query, onlyStrong])
  const signalPool = useMemo(() => {
    const candidates = ruleSignals.length ? ruleSignals : liveMovers.map((stock) => ({ ...stock, rule_label: stock.signal, evidence: stock.note }))
    return candidates.filter((stock) => {
      const queryMatch = `${stock.name}${stock.code}${stock.sector}${stock.rule_label}`.toLowerCase().includes(query.toLowerCase())
      return queryMatch && (!onlyStrong || stock.score >= 80)
    })
  }, [ruleSignals, liveMovers, query, onlyStrong])
  const alertItems = useMemo(() => [
    ...signalEvents.map((event) => ({
      id: `${event.code}-${event.rule_name}-${event.triggered_at}`,
      time: alertTime(event.triggered_at),
      title: `${event.name} · ${ruleLabels[event.rule_name] || event.rule_name} · ${event.score}`,
      detail: `${event.evidence} 风险：${event.risk}`,
      status: '规则触发',
      direction: event.rule_name === 'risk_breakdown' ? 'down' : 'up',
    })),
    ...alerts,
  ], [signalEvents, alerts])
  const watchSignals = useMemo(() => {
    const matched = new Map()
    for (const signal of ruleSignals) {
      if (!matched.has(signal.code)) matched.set(signal.code, signal)
    }
    return matched
  }, [ruleSignals])
  const pageDescriptions = {
    '跨市场总览': '股票、基金、联动。',
    '股票雷达': '异动与板块。',
    '信号池': '规则异动。',
    '基金全景': '净值与风格。',
    'AI 研判': '证据与风险。',
    '自选观察': '关注标的。',
    '预警中心': '规则提醒。',
    '盘后复盘': '结构复盘。',
    '设置': '模型与统筹。',
    '帮助': '快速说明。',
    '仓位参考': '研究优先级。',
  }
  const marketIndices = liveOverview?.indices || fallbackIndices
  const marketSourceLabel = liveOverview?.source === 'akshare' ? 'AkShare 全市场快照' : liveOverview?.source === 'eastmoney' ? (liveOverview.is_live ? '东方财富实时快照' : '东方财富收盘快照') : liveOverview?.source === 'cache' ? '本地缓存快照' : '演示数据模式'
  const marketTrading = liveOverview?.market_status === 'trading'

  return <div className="app-shell">
    <Sidebar activeNav={activeNav} menuOpen={menuOpen} onNavigate={(label) => { setActiveNav(label); setMenuOpen(false) }} onCloseMenu={() => setMenuOpen(false)} />

    <main>
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="打开菜单" onClick={() => setMenuOpen(true)}><Menu size={20} /></button>
        <div className="market-status"><span className={marketTrading ? 'live-dot' : 'offline-dot'} />沪深市场 <strong>{marketTrading ? '交易中' : '已收盘'}</strong><span className="market-time">{liveOverview?.as_of ? new Date(liveOverview.as_of).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '--:--:--'}</span></div>
        <div className="topbar-actions"><button className="icon-button" aria-label="帮助" onClick={() => setActiveNav('帮助')}><CircleHelp size={19} /></button><button className="notification" aria-label={`${Math.min(alertItems.length, 99)} 条预警`} onClick={() => setActiveNav('预警中心')}><Bell size={19} /><i>{Math.min(alertItems.length, 99)}</i></button><button className="avatar" aria-label="个人账户" onClick={() => showNotice('当前为本地研究工作区')}>我</button></div>
      </header>

      <div className="content">
        <section className="page-heading">
          <div className="page-heading-copy"><h1>{activeNav}</h1><p>{pageDescriptions[activeNav]}</p></div>
          <div className="heading-actions">{activeNav === '股票雷达' && <><button className="filter-button" onClick={() => setOnlyStrong((value) => !value)}><Filter size={17} />{onlyStrong ? '仅看高置信度' : '筛选信号'}</button><button className="filter-button" onClick={refreshMarket} disabled={refreshingMarket}><RefreshCw className={refreshingMarket ? 'loading-icon' : ''} size={17} />{refreshingMarket ? '刷新中' : '刷新行情'}</button><button className="primary-button" onClick={() => setAlertEditorOpen((open) => !open)}><Bell size={17} />新建预警</button></>}{activeNav === '信号池' && <button className="filter-button" onClick={() => setOnlyStrong((value) => !value)}><Filter size={17} />{onlyStrong ? '显示全部' : '仅高置信度'}</button>}</div>
        </section>

        {alertEditorOpen && <section className="alert-editor" aria-label="创建预警"><form onSubmit={createAlert}><div><span>为 {selected.name} 创建预警</span><strong>{selected.code} · {selected.price}</strong></div><label>条件<select value={alertDraft.rule} onChange={(event) => setAlertDraft((draft) => ({ ...draft, rule: event.target.value }))}><option>涨跌幅突破</option><option>成交量放大</option><option>置信度变化</option></select></label><label>阈值<input type="number" min="0.1" step="0.1" value={alertDraft.threshold} onChange={(event) => setAlertDraft((draft) => ({ ...draft, threshold: event.target.value }))} /><span>%</span></label><button type="button" className="text-button" onClick={() => setAlertEditorOpen(false)}>取消</button><button type="submit" className="primary-button">保存预警</button></form></section>}

        {activeNav === '跨市场总览' && <CrossMarketPage liveOverview={liveOverview} movers={liveMovers} fundOverview={{ funds, universe_count: fundUniverseCount, category_counts: fundCategoryCounts, source: fundSource }} linkage={linkage} linkageState={linkageState} crossAnalysis={crossAnalysis} crossAnalysisState={crossAnalysisState} crossAnalysisError={crossAnalysisError} llmConfigured={llmConfigured} generateCrossAnalysis={generateCrossAnalysis} setActiveNav={setActiveNav} />}

        {activeNav === '股票雷达' && <MarketRadar marketIndices={marketIndices} liveOverview={liveOverview} liveMovers={liveMovers} liveSectors={liveSectors} apiAvailable={apiAvailable} marketSourceLabel={marketSourceLabel} filteredMovers={filteredMovers} selected={selected} setSelected={setSelected} focusOpen={focusOpen} setFocusOpen={setFocusOpen} watchlist={watchlist} toggleWatch={toggleWatch} dailyBars={dailyBars} dailyIndicators={dailyIndicators} syncingHistory={syncingHistory} syncDailyHistory={syncDailyHistory} signalAnalysisState={signalAnalysisState} generateSignalAnalysis={generateSignalAnalysis} query={query} setQuery={setQuery} setOnlyStrong={setOnlyStrong} market={market} setMarket={setMarket} setActiveNav={setActiveNav} />}

        {activeNav === '基金全景' && <FundsPage funds={funds} universeCount={fundUniverseCount} categoryCounts={fundCategoryCounts} fundsState={fundsState} fundSource={fundSource} fundWatchlist={fundWatchlist} onlyMine={onlyMineFunds} setOnlyMine={setOnlyMineFunds} refreshFunds={refreshFunds} toggleFundWatch={toggleFundWatch} selectedFund={selectedFund} fundHoldings={fundHoldings} fundLinkedStocks={fundLinkedStocks} fundHoldingsState={fundHoldingsState} fundHoldingsError={fundHoldingsError} openFundHoldings={openFundHoldings} closeFundHoldings={closeFundHoldings} analyzeFund={analyzeFund} fundAnalysis={fundAnalysis} fundAnalysisState={fundAnalysisState} fundAnalysisError={fundAnalysisError} />}

        {activeNav === '信号池' && <SignalPoolPage signalPool={signalPool} signalsState={signalsState} ruleSignals={ruleSignals} onlyStrong={onlyStrong} setOnlyStrong={setOnlyStrong} setQuery={setQuery} openStock={openStock} />}

        {activeNav === '自选观察' && <WatchlistPage watchlist={watchlist} watchSignals={watchSignals} setActiveNav={setActiveNav} openStock={openStock} toggleWatch={toggleWatch} showNotice={showNotice} />}

        {activeNav === '预警中心' && <AlertsPage alertItems={alertItems} eventsState={eventsState} setAlertEditorOpen={setAlertEditorOpen} />}

        {activeNav === '盘后复盘' && <ReviewPage showNotice={showNotice} />}
        {activeNav === 'AI 研判' && <ResearchWorkspace llmConfigured={llmConfigured} llmProtocol={llmProtocol} analysisState={analysisState} analysis={analysis} analysisError={analysisError} generateAnalysis={generateAnalysis} selected={selected} signalAnalysisState={signalAnalysisState} signalAnalysis={signalAnalysis} signalAnalysisError={signalAnalysisError} generateSignalAnalysis={generateSignalAnalysis} />}
        {activeNav === '仓位参考' && <DecisionReferencePage reference={decisionReference} state={decisionState} error={decisionError} onGenerate={generateDecisionReference} />}
        {activeNav === '设置' && <SettingsPage theme={theme} setTheme={setTheme} onNotice={showNotice} onSettingsChanged={(settings) => { setLlmConfigured(Boolean(settings.configured)); setLlmProtocol(settings.protocol || 'chat_completions') }} />}
        {activeNav === '帮助' && <HelpPage setActiveNav={setActiveNav} />}
        {notice && <div className="toast" role="status">{notice}</div>}
      </div>
    </main>
  </div>
}

export default App
