import { useState, useEffect } from 'react'

const PIPELINE_LABELS = {
  architect: 'Architect', reviewer: 'Reviewer', backend: 'Backend',
  frontend: 'Frontend', database: 'Database', tests: 'Tests', qa: 'QA'
}

export default function WorkItemDetail({ item, onBack }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    fetch(`/api/work-items/${item.id}`).then(r => r.json()).then(setData)
    const t = setInterval(() => fetch(`/api/work-items/${item.id}`).then(r => r.json()).then(setData), 8000)
    return () => clearInterval(t)
  }, [item.id])

  const runPhase = async (phaseId) => {
    await fetch(`/api/pipeline/${phaseId}/run`, { method: 'POST' })
    const r = await fetch(`/api/work-items/${item.id}`)
    setData(await r.json())
  }

  if (!data) return <div className="text-gray-500">Loading...</div>

  return (
    <div>
      <button onClick={onBack} className="text-blue-400 hover:text-blue-300 text-sm mb-4 flex items-center gap-1">← Back to Dashboard</button>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-100">{data.title}</h2>
          <div className="flex items-center gap-2 mt-1">
            <span className={`text-xs px-2 py-0.5 rounded-full ${data.work_type === 'bug' ? 'bg-red-600/30 text-red-400' : data.work_type === 'feature' ? 'bg-blue-600/30 text-blue-400' : 'bg-gray-600/30 text-gray-400'}`}>{data.work_type}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${data.status === 'done' ? 'bg-green-600/20 text-green-400' : 'bg-yellow-600/20 text-yellow-400'}`}>{data.status}</span>
            {data.project_name && <span className="text-xs text-gray-500">{data.project_name}</span>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Pipeline</h3>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center justify-between px-2">
              {data.phases?.map((phase, i) => (
                <div key={phase.id} className="flex flex-col items-center flex-1">
                  <div className="flex flex-col items-center">
                    <div className={`phase-dot ${phase.status}`} />
                    <span className="text-xs text-gray-500 mt-1">{PIPELINE_LABELS[phase.role]}</span>
                    <span className="text-xs text-gray-600">{phase.status}</span>
                    {phase.duration_s && <span className="text-xs text-gray-600">{phase.duration_s}s</span>}
                  </div>
                  {phase.status === 'queued' && (
                    <button onClick={() => runPhase(phase.id)} className="mt-2 bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded-md">
                      Run
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <h3 className="text-sm font-semibold text-gray-400 mt-6 mb-4">Comments</h3>
          <div className="space-y-2">
            {data.comments?.map(c => (
              <div key={c.id} className="bg-gray-900 border border-gray-800 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-blue-400">{c.author}</span>
                  <span className="text-xs text-gray-600">{c.comment_type}</span>
                  <span className="text-xs text-gray-600">{c.created_at?.replace('T', ' ').substring(0, 16)}</span>
                </div>
                <p className="text-sm text-gray-300">{c.content}</p>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-400 mb-4">Details</h3>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 space-y-3">
            <div><span className="text-xs text-gray-500">Type</span><p className="text-sm text-gray-300">{data.work_type}</p></div>
            <div><span className="text-xs text-gray-500">Status</span><p className="text-sm text-gray-300">{data.status}</p></div>
            <div><span className="text-xs text-gray-500">Priority</span><p className="text-sm text-gray-300">{data.priority}</p></div>
            <div><span className="text-xs text-gray-500">Created</span><p className="text-sm text-gray-300">{data.created_at?.replace('T', ' ').substring(0, 16)}</p></div>
            {data.completed_at && <div><span className="text-xs text-gray-500">Completed</span><p className="text-sm text-gray-300">{data.completed_at?.replace('T', ' ').substring(0, 16)}</p></div>}
          </div>
        </div>
      </div>
    </div>
  )
}