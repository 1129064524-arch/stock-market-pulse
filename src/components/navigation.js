import { Activity, Bell, BrainCircuit, BriefcaseBusiness, LayoutDashboard, LineChart, PieChart, Sparkles, Star } from 'lucide-react'

export const navGroups = [
  { label: '全市场监测', items: [{ label: '跨市场总览', icon: LayoutDashboard }, { label: '股票雷达', icon: Activity }, { label: '基金全景', icon: PieChart }, { label: '信号池', icon: Sparkles }] },
  { label: '个人资产', items: [{ label: '自选观察', icon: Star }] },
  { label: '研究工作台', items: [{ label: 'AI 研判', icon: BrainCircuit }, { label: '仓位参考', icon: BriefcaseBusiness }] },
  { label: '复盘与提醒', items: [{ label: '预警中心', icon: Bell }, { label: '盘后复盘', icon: LineChart }] },
]
