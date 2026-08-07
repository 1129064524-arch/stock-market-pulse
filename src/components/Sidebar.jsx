import { memo } from 'react'
import { Settings2 } from 'lucide-react'
import mark from '../assets/market-pulse-mark.svg'
import { navGroups } from './navigation.js'

function Sidebar({ activeNav, menuOpen, onNavigate, onCloseMenu }) {
  return <>
    <aside className={`sidebar ${menuOpen ? 'open' : ''}`}>
      <div className="brand"><img className="brand-mark" src={mark} alt="市场脉冲" /><span>市场脉冲</span></div>
      <nav className="sidebar-nav" aria-label="主要导航">{navGroups.map((group) => <div className="nav-group" key={group.label}><div className="sidebar-label">{group.label}</div>{group.items.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${activeNav === label ? 'active' : ''}`} onClick={() => onNavigate(label)}><Icon size={18} /><span>{label}</span></button>)}</div>)}</nav>
      <div className="sidebar-footer"><button className={`nav-item ${activeNav === '设置' ? 'active' : ''}`} onClick={() => onNavigate('设置')}><Settings2 size={18} /><span>设置</span></button><p>分析仅供研究参考<br />不构成投资建议</p></div>
    </aside>
    {menuOpen && <button className="scrim" aria-label="关闭菜单" onClick={onCloseMenu} />}
  </>
}

export default memo(Sidebar)
