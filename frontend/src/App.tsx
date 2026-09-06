import { useMemo, useState } from 'react';

type Status = 'Completed' | 'In Progress' | 'Delayed' | 'Not Started' | 'Unplanned';
type Discipline = 'Civil' | 'Piping' | 'Electrical' | 'Instrumentation' | 'HSE';

type Activity = {
  id: string;
  name: string;
  discipline: Discipline;
  location: string;
  plannedStart: string;
  plannedEnd: string;
  status: Status;
  progress: number;
};

type ReviewItem = {
  id: number;
  originalInput: string;
  extractedDescription: string;
  suggestedActivityId: string;
  confidence: number;
  worker: string;
};

type AuditEntry = {
  id: number;
  timestamp: string;
  worker: string;
  originalInput: string;
  extractedData: string;
  matchedId: string;
  confidence: number;
  status: 'Auto-linked' | 'Manual Confirmed' | 'Unplanned';
};

const activities: Activity[] = [
  { id: 'CIV-101', name: 'Excavation for tank foundation', discipline: 'Civil', location: 'Zone A - Tank Farm', plannedStart: '2026-09-01', plannedEnd: '2026-09-07', status: 'In Progress', progress: 72 },
  { id: 'CIV-102', name: 'Concrete pouring for tank base', discipline: 'Civil', location: 'Zone A - Tank Farm', plannedStart: '2026-09-03', plannedEnd: '2026-09-10', status: 'Completed', progress: 100 },
  { id: 'CIV-205', name: 'Foundation work for control room', discipline: 'Civil', location: 'Zone D - Control Room', plannedStart: '2026-09-02', plannedEnd: '2026-09-09', status: 'Delayed', progress: 45 },
  { id: 'PIP-110', name: 'Pipe welding near tank 3', discipline: 'Piping', location: 'Zone A - Tank Farm', plannedStart: '2026-09-04', plannedEnd: '2026-09-11', status: 'Completed', progress: 100 },
  { id: 'PIP-210', name: 'Pipeline laying in corridor', discipline: 'Piping', location: 'Zone B - Pipeline Corridor', plannedStart: '2026-09-03', plannedEnd: '2026-09-12', status: 'In Progress', progress: 68 },
  { id: 'ELE-321', name: 'Cable tray installation', discipline: 'Electrical', location: 'Zone C - Substation', plannedStart: '2026-09-01', plannedEnd: '2026-09-07', status: 'Not Started', progress: 12 },
  { id: 'ELE-420', name: 'HT cable pulling', discipline: 'Electrical', location: 'Zone C - Substation', plannedStart: '2026-09-03', plannedEnd: '2026-09-10', status: 'Delayed', progress: 52 },
  { id: 'INS-510', name: 'Instrument cable routing', discipline: 'Instrumentation', location: 'Zone D - Control Room', plannedStart: '2026-09-06', plannedEnd: '2026-09-15', status: 'Not Started', progress: 0 },
  { id: 'HSE-010', name: 'Safety barricade setup', discipline: 'HSE', location: 'All zones', plannedStart: '2026-09-01', plannedEnd: '2026-09-10', status: 'Completed', progress: 100 },
  { id: 'UNPL-001', name: 'Additional concrete patch work', discipline: 'Civil', location: 'Zone B', plannedStart: '-', plannedEnd: '-', status: 'Unplanned', progress: 0 },
];

const reviewQueue: ReviewItem[] = [
  {
    id: 1,
    originalInput: 'Completed pipe welding near tank 3 after rain delay at Zone A',
    extractedDescription: 'Pipe welding near tank 3 completed',
    suggestedActivityId: 'PIP-110',
    confidence: 84,
    worker: 'A. Kumar'
  },
  {
    id: 2,
    originalInput: 'Cable tray installed in substation but a few supports remain pending',
    extractedDescription: 'Cable tray installation at substation',
    suggestedActivityId: 'ELE-321',
    confidence: 71,
    worker: 'S. Patel'
  },
  {
    id: 3,
    originalInput: 'Temporary barricading added near pipeline crossing for safety',
    extractedDescription: 'Temporary safety barricade near pipeline crossing',
    suggestedActivityId: 'HSE-010',
    confidence: 63,
    worker: 'R. Singh'
  },
];

const auditEntries: AuditEntry[] = [
  {
    id: 1,
    timestamp: '2026-09-05 08:20',
    worker: 'A. Kumar',
    originalInput: 'Pipe welding near tank 3 done today',
    extractedData: 'Activity: Pipe welding near tank 3 | Discipline: Piping | Location: Zone A',
    matchedId: 'PIP-110',
    confidence: 87,
    status: 'Auto-linked'
  },
  {
    id: 2,
    timestamp: '2026-09-05 10:40',
    worker: 'S. Patel',
    originalInput: 'Cable tray installation completed in substation',
    extractedData: 'Activity: Cable tray installation | Discipline: Electrical | Location: Zone C',
    matchedId: 'ELE-321',
    confidence: 79,
    status: 'Manual Confirmed'
  },
  {
    id: 3,
    timestamp: '2026-09-05 12:05',
    worker: 'R. Singh',
    originalInput: 'New concrete patch work on access road',
    extractedData: 'Activity: Concrete patch work | Discipline: Civil | Location: Zone B',
    matchedId: 'UNPL-001',
    confidence: 44,
    status: 'Unplanned'
  },
];

const statusColors: Record<Status, string> = {
  Completed: '#10b981',
  'In Progress': '#f59e0b',
  Delayed: '#ef4444',
  'Not Started': '#94a3b8',
  Unplanned: '#8b5cf6'
};

const disciplineOptions: Array<'All' | Discipline> = ['All', 'Civil', 'Piping', 'Electrical', 'Instrumentation', 'HSE'];
const statusOptions: Array<'All' | Status> = ['All', 'Completed', 'In Progress', 'Delayed', 'Not Started', 'Unplanned'];

export default function App() {
  const [selectedDiscipline, setSelectedDiscipline] = useState<'All' | Discipline>('All');
  const [selectedStatus, setSelectedStatus] = useState<'All' | Status>('All');
  const [search, setSearch] = useState('');

  const filteredActivities = useMemo(() => {
    return activities.filter((activity) => {
      const disciplineMatch = selectedDiscipline === 'All' || activity.discipline === selectedDiscipline;
      const statusMatch = selectedStatus === 'All' || activity.status === selectedStatus;
      const searchMatch = activity.name.toLowerCase().includes(search.toLowerCase()) || activity.id.toLowerCase().includes(search.toLowerCase());
      return disciplineMatch && statusMatch && searchMatch;
    });
  }, [selectedDiscipline, selectedStatus, search]);

  const totalActivities = activities.length;
  const completed = activities.filter((a) => a.status === 'Completed').length;
  const inProgress = activities.filter((a) => a.status === 'In Progress').length;
  const delayed = activities.filter((a) => a.status === 'Delayed').length;
  const unplanned = activities.filter((a) => a.status === 'Unplanned').length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-icon">P</div>
          <div>
            <div className="eyebrow">Project Manager</div>
            <h2>ScheduleLink</h2>
          </div>
        </div>

        <nav className="nav-list">
          <button className="nav-item active">
            <span>Dashboard</span>
          </button>
          <button className="nav-item">
            <span>Activities</span>
          </button>
          <button className="nav-item">
            <span>Review Queue</span>
          </button>
          <button className="nav-item">
            <span>Audit Trail</span>
          </button>
          <button className="nav-item">
            <span>Unplanned</span>
          </button>
        </nav>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Overview</p>
            <h1>Project Control Dashboard</h1>
          </div>
          <button className="primary-btn">Upload Primavera</button>
        </header>

        <section className="stats-grid">
          <div className="stat-card">
            <span>Total Activities</span>
            <strong>{totalActivities}</strong>
            <small>Plan baseline</small>
          </div>
          <div className="stat-card success">
            <span>Completed</span>
            <strong>{completed}</strong>
            <small>Delivered</small>
          </div>
          <div className="stat-card warning">
            <span>In Progress</span>
            <strong>{inProgress}</strong>
            <small>On site</small>
          </div>
          <div className="stat-card danger">
            <span>Delayed</span>
            <strong>{delayed}</strong>
            <small>Needs attention</small>
          </div>
          <div className="stat-card purple">
            <span>Unplanned</span>
            <strong>{unplanned}</strong>
            <small>Field reports</small>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <h3>Activity Status Board</h3>
            <div className="filters">
              <select value={selectedDiscipline} onChange={(e) => setSelectedDiscipline(e.target.value as 'All' | Discipline)}>
                {disciplineOptions.map((discipline) => (
                  <option key={discipline} value={discipline}>{discipline}</option>
                ))}
              </select>
              <select value={selectedStatus} onChange={(e) => setSelectedStatus(e.target.value as 'All' | Status)}>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>{status}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Search activity or ID"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Activity</th>
                  <th>Discipline</th>
                  <th>Location</th>
                  <th>Dates</th>
                  <th>Status</th>
                  <th>Progress</th>
                </tr>
              </thead>
              <tbody>
                {filteredActivities.map((activity) => (
                  <tr key={activity.id}>
                    <td>{activity.id}</td>
                    <td>{activity.name}</td>
                    <td>{activity.discipline}</td>
                    <td>{activity.location}</td>
                    <td>{activity.plannedStart} – {activity.plannedEnd}</td>
                    <td>
                      <span className="pill" style={{ backgroundColor: `${statusColors[activity.status]}22`, color: statusColors[activity.status] }}>
                        {activity.status}
                      </span>
                    </td>
                    <td>
                      <div className="progress-cell">
                        <div className="progress-bar">
                          <span style={{ width: `${activity.progress}%` }} />
                        </div>
                        <small>{activity.progress}%</small>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="lower-grid">
          <div className="panel queue-panel">
            <div className="panel-header compact">
              <h3>Matching Review Queue</h3>
              <button className="ghost-btn">View all</button>
            </div>

            {reviewQueue.map((item) => (
              <div key={item.id} className="queue-item">
                <div className="queue-meta">
                  <span>{item.worker}</span>
                  <span>Confidence {item.confidence}%</span>
                </div>
                <p><strong>Original input:</strong> {item.originalInput}</p>
                <p><strong>Extracted:</strong> {item.extractedDescription}</p>
                <p><strong>Suggested ID:</strong> {item.suggestedActivityId}</p>
                <div className="queue-actions">
                  <button className="confirm-btn">Confirm Match</button>
                  <button className="secondary-btn">Reassign</button>
                  <button className="danger-btn">Unplanned</button>
                </div>
              </div>
            ))}
          </div>

          <div className="panel audit-panel">
            <div className="panel-header compact">
              <h3>Audit Trail</h3>
              <button className="ghost-btn">Search</button>
            </div>

            <div className="audit-list">
              {auditEntries.map((entry) => (
                <div key={entry.id} className="audit-entry">
                  <div className="audit-topline">
                    <strong>{entry.worker}</strong>
                    <span>{entry.timestamp}</span>
                  </div>
                  <p>{entry.originalInput}</p>
                  <small>{entry.extractedData}</small>
                  <div className="audit-footer">
                    <span>Matched: {entry.matchedId}</span>
                    <span>Score: {entry.confidence}%</span>
                    <span className="audit-status">{entry.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
