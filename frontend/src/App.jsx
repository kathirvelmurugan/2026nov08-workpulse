import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import WorkItemDetail from './pages/WorkItemDetail'

export default function App() {
  const [view, setView] = useState('dashboard')
  const [selectedItem, setSelectedItem] = useState(null)
  const [heartbeat, setHeartbeat] = useState({})

  useEffect(() => {
    fetch('/api/heartbeat').then(r => r.json()).then(setHeartbeat)
    const t = setInterval(() => fetch('/api/heartbeat').then(r => r.json()).then(setHeartbeat), 10000)
    return () => clearInterval(t)
  }, [])

  return (
    <div className="flex h-screen">
      <nav className="w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-800">
          <h1 className="text-lg font-bold text-blue-400">WorkPulse SDLC</h1>
          <p className="text-xs text-gray-500">AI-Powered Development</p>
        </div>
        <div className="flex-1 p-2">
          <NavItem active={view === 'dashboard'} onClick={() => { setView('dashboard'); setSelectedItem(null) }}>Dashboard</NavItem>
          <NavItem active={view === 'projects'} onClick={() => { setView('projects'); setSelectedItem(null) }}>Projects</NavItem>
          <NavItem active={view === 'new'} onClick={() => { setView('new'); setSelectedItem(null) }}>+ New Work Item</NavItem>
        </div>
        <div className="p-3 border-t border-gray-800 text-xs text-gray-600">
          {heartbeat.status === 'ok' ? 'Online' : 'Offline'}
        </div>
      </nav>
      <main className="flex-1 overflow-y-auto p-6">
        {view === 'dashboard' && <Dashboard onSelect={item => { setSelectedItem(item); setView('detail') }} />}
        {view === 'detail' && selectedItem && <WorkItemDetail item={selectedItem} onBack={() => { setView('dashboard'); setSelectedItem(null) }} />}
        {view === 'projects' && <ProjectsView />}
        {view === 'new' && <NewWorkItem onCreated={item => { setSelectedItem(item); setView('detail') }} />}
      </main>
    </div>
  )
}

function NavItem({ active, onClick, children }) {
  return (
    <button onClick={onClick} className={`w-full text-left px-3 py-2 rounded-md text-sm mb-1 transition-colors ${active ? 'bg-blue-600/20 text-blue-400' : 'text-gray-400 hover:bg-gray-800 hover:text-gray-200'}`}>
      {children}
    </button>
  )
}

function ProjectsView() {
  const [projects, setProjects] = useState([])
  const [form, setForm] = useState({ name: '', project_type: 'internal', description: '', repo_url: '' })

  useEffect(() => { fetch('/api/projects').then(r => r.json()).then(setProjects) }, [])

  const create = () => {
    fetch('/api/projects', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      .then(r => r.json()).then(() => fetch('/api/projects').then(r => r.json()).then(setProjects))
    setForm({ name: '', project_type: 'internal', description: '', repo_url: '' })
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-blue-400 mb-6">Projects</h2>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6 max-w-md">
        <input className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm mb-2" placeholder="Project name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
        <select className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm mb-2" value={form.project_type} onChange={e => setForm({ ...form, project_type: e.target.value })}>
          <option value="internal">Internal</option><option value="client">Client</option>
        </select>
        <input className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm mb-2" placeholder="Description (optional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        <input className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm mb-3" placeholder="Repo URL (optional)" value={form.repo_url} onChange={e => setForm({ ...form, repo_url: e.target.value })} />
        <button onClick={create} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium">Create Project</button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {projects.map(p => (
          <div key={p.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-200">{p.name}</h3>
              <span className={`text-xs px-2 py-0.5 rounded-full ${p.project_type === 'client' ? 'bg-purple-600/30 text-purple-400' : 'bg-blue-600/30 text-blue-400'}`}>{p.project_type}</span>
            </div>
            {p.repo_url && <p className="text-xs text-gray-500 mb-1">{p.repo_url}</p>}
            <p className="text-xs text-gray-600">Created {p.created_at?.replace('T', ' ').substring(0, 16)}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

function NewWorkItem({ onCreated }) {
  const [projects, setProjects] = useState([])
  const [form, setForm] = useState({ project_id: '', title: '', description: '', work_type: 'feature', priority: 'medium' })

  useEffect(() => { fetch('/api/projects').then(r => r.json()).then(setProjects) }, [])

  const submit = async () => {
    const r = await fetch('/api/work-items', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
    const data = await r.json()
    if (data.id) onCreated({ id: data.id })
  }

  return (
    <div>
      <h2 className="text-xl font-bold text-blue-400 mb-6">New Work Item</h2>
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-6 max-w-lg">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Project</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm" value={form.project_id} onChange={e => setForm({ ...form, project_id: e.target.value })}>
              <option value="">Select...</option>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Type</label>
            <select className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm" value={form.work_type} onChange={e => setForm({ ...form, work_type: e.target.value })}>
              <option value="feature">Feature</option><option value="bug">Bug</option><option value="research">Research</option><option value="maintenance">Maintenance</option>
            </select>
          </div>
        </div>
        <div className="mb-4">
          <label className="block text-xs text-gray-500 mb-1">Title</label>
          <input className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm" placeholder="What needs to be done?" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
        </div>
        <div className="mb-4">
          <label className="block text-xs text-gray-500 mb-1">Description</label>
          <textarea className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm h-24" placeholder="Full details of the requirement..." value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
        </div>
        <button onClick={submit} className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-md text-sm font-medium">Create & Start Pipeline</button>
      </div>
    </div>
  )
}