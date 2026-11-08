import { useState, useEffect } from 'react'

export default function Dashboard({ onSelect }) {
  const [items, setItems] = useState([])
  const [projects, setProjects] = useState([])

  useEffect(() => {
    fetch('/api/tasks').then(r => r.json()).then(setItems)
    fetch('/api/projects').then(r => r.json()).then(setProjects)
    const t = setInterval(() => fetch('/api/tasks').then(r => r.json()).then(setItems), 10000)
    return () => clearInterval(t)
  }, [])

  const active = items.filter(i => i.status === 'active' || i.status === 'in_progress').length
  const done = items.filter(i => i.status === 'done' || i.status === 'merged').length
  const features = items.filter(i => i.task_type === 'feature').length
  const bugs = items.filter(i => i.task_type === 'bug').length

  return (
    <div>
      <h2 className="text-xl font-bold text-blue-400 mb-6">Dashboard</h2>
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="Active" value={active} color="text-yellow-400" />
        <StatCard label="Completed" value={done} color="text-green-400" />
        <StatCard label="Features" value={features} color="text-blue-400" />
        <StatCard label="Bugs" value={bugs} color="text-red-400" />
      </div>
      <h3 className="text-lg font-semibold text-gray-200 mb-4">Work Items</h3>
      <div className="space-y-2">
        {items.map(item => (
          <div key={item.id} onClick={() => onSelect(item)} className="bg-gray-900 border border-gray-800 rounded-lg p-4 cursor-pointer hover:border-gray-700 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`text-xs px-2 py-0.5 rounded-full ${item.work_type === 'bug' ? 'bg-red-600/30 text-red-400' : item.work_type === 'feature' ? 'bg-blue-600/30 text-blue-400' : item.work_type === 'research' ? 'bg-purple-600/30 text-purple-400' : 'bg-gray-600/30 text-gray-400'}`}>
                  {item.work_type}
                </span>
                <span className="font-medium text-gray-200">{item.title}</span>
                {item.project_name && <span className="text-xs text-gray-600">{item.project_name}</span>}
              </div>
              <span className={`text-xs px-2 py-1 rounded-full ${
                item.status === 'done' ? 'bg-green-600/20 text-green-400' :
                item.status === 'intake' ? 'bg-gray-600/20 text-gray-400' :
                'bg-yellow-600/20 text-yellow-400'
              }`}>{item.status}</span>
            </div>
          </div>
        ))}
        {items.length === 0 && <p className="text-gray-600 text-center py-8">No work items yet. Create one to start.</p>}
      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  )
}