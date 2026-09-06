import { useEffect, useMemo, useState } from 'react';
import { Link, NavLink } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  Bell,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock3,
  FileSpreadsheet,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  ShieldCheck,
  UserRound,
  Users,
  X,
  Zap,
} from 'lucide-react';

import {
  getDashboardStats,
  getReviewQueue,
  getSchedule,
  getNotifications,
} from '../../api';

import { useAuth } from '../../context/AuthContext';

type ActivityItem = {
  id: number;
  task_name: string;
  discipline: string;
  location: string;
  planned_start: string;
  planned_end: string;
  actual_completion_date?: string;
  status: string;
};

type ReviewItem = {
  id: number;
  raw_text: string;
  extracted_task: string;
  matched_schedule_id: number | null;
  confidence_score: number;
  review_status: string;
  created_at: string;
  candidate_task?: string;
  candidate_discipline?: string;
  candidate_location?: string;
  planned_start?: string;
  planned_end?: string;
};

type NotificationItem = {
  id: number;
  type: string;
  message: string;
  timestamp: string;
  read: boolean;
};

const navigation = [
  { label: 'Dashboard', path: '/manager/dashboard', icon: LayoutDashboard },
  { label: 'Project Plan', path: '/manager/project-plan', icon: FileSpreadsheet },
  { label: 'Activities', path: '/manager/activities', icon: ClipboardList },
  { label: 'Review Queue', path: '/manager/review-queue', icon: ShieldCheck },
  { label: 'Unplanned', path: '/manager/unplanned', icon: AlertTriangle },
  { label: 'Audit Trail', path: '/manager/audit-trail', icon: Activity },
  { label: 'Settings', path: '/manager/settings', icon: Settings },
];

function formatDate(value: string) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });
}

function formatTime(value: string) {
  if (!value) return '—';

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

function statusLabel(status: string) {
  const normalized = status.toLowerCase().replace(/[\s-]+/g, '_');

  if (normalized.includes('complete')) return 'Completed';
  if (normalized.includes('progress')) return 'In Progress';
  if (normalized.includes('delay')) return 'Delayed';
  if (normalized.includes('unplanned')) return 'Unplanned';
  if (normalized.includes('review')) return 'Needs Review';
  if (normalized.includes('start')) return 'Not Started';

  return status || 'Unknown';
}

function statusClass(status: string) {
  const label = statusLabel(status);

  if (label === 'Completed') return 'status-badge status-success';
  if (label === 'In Progress') return 'status-badge status-info';
  if (label === 'Delayed') return 'status-badge status-danger';
  if (label === 'Needs Review') return 'status-badge status-warning';
  if (label === 'Unplanned') return 'status-badge status-danger';

  return 'status-badge status-neutral';
}

function confidenceClass(value: number) {
  if (value >= 0.8) return 'confidence-high';
  if (value >= 0.5) return 'confidence-medium';
  return 'confidence-low';
}

function getWorkerName(index: number) {
  const workers = [
    'Rahul Sharma',
    'Amit Patel',
    'Suresh Kumar',
    'Worker 024',
  ];

  return workers[index % workers.length];
}

export default function ManagerDashboard() {
  const { user, logout } = useAuth();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [stats, setStats] = useState<{
    total_activities: number;
    completed: number;
    in_progress: number;
    delayed: number;
    unplanned: number;
    needs_review: number;
  }>({
    total_activities: 0,
    completed: 0,
    in_progress: 0,
    delayed: 0,
    unplanned: 0,
    needs_review: 0,
  });

  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  async function loadDashboard() {
    try {
      setLoading(true);
      setError('');

      const [dashboard, schedule, reviews, notificationData] =
        await Promise.all([
          getDashboardStats(),
          getSchedule(),
          getReviewQueue(),
          getNotifications(),
        ]);

      setStats(dashboard.kpis);
      setActivities(schedule || []);
      setReviewQueue(reviews || []);
      setNotifications(notificationData || []);
    } catch (err) {
      console.error(err);
      setError('Unable to load the project dashboard.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const activityBreakdown = useMemo(() => {
    const total = Math.max(stats.total_activities, 1);

    return [
      {
        label: 'Completed',
        value: stats.completed,
        percentage: Math.round((stats.completed / total) * 100),
        className: 'chart-completed',
      },
      {
        label: 'In Progress',
        value: stats.in_progress,
        percentage: Math.round((stats.in_progress / total) * 100),
        className: 'chart-progress',
      },
      {
        label: 'Delayed',
        value: stats.delayed,
        percentage: Math.round((stats.delayed / total) * 100),
        className: 'chart-delayed',
      },
      {
        label: 'Unplanned',
        value: stats.unplanned,
        percentage: Math.round((stats.unplanned / total) * 100),
        className: 'chart-unplanned',
      },
    ];
  }, [stats]);

  const recentActivities = useMemo(() => {
    return [...activities]
      .sort((a, b) => {
        const first = new Date(
          a.actual_completion_date || a.planned_start
        ).getTime();

        const second = new Date(
          b.actual_completion_date || b.planned_start
        ).getTime();

        return second - first;
      })
      .slice(0, 6);
  }, [activities]);

  const pendingReviews = useMemo(() => {
    return [...reviewQueue]
      .sort((a, b) => a.confidence_score - b.confidence_score)
      .slice(0, 4);
  }, [reviewQueue]);

  const unreadNotifications = notifications.filter(
    (notification) => !notification.read
  ).length;

  return (
    <div className="manager-shell">
      {sidebarOpen && (
        <button
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside className={`manager-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="brand">
          <div className="brand-icon">F</div>

          <div>
            <div className="brand-name">FieldTrack</div>
            <div className="brand-subtitle">Project Control</div>
          </div>

          <button
            className="mobile-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={19} />
          </button>
        </div>

        <div className="sidebar-project">
          <div className="sidebar-project-label">ACTIVE PROJECT</div>
          <div className="sidebar-project-name">
            Oil India — Refinery Expansion
          </div>
          <div className="sidebar-project-status">
            <span />
            Live project
          </div>
        </div>

        <nav>
          {navigation.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={({ isActive }) =>
                  isActive ? 'active' : ''
                }
              >
                <Icon size={18} />
                <span>{item.label}</span>

                {item.label === 'Review Queue' &&
                  stats.needs_review > 0 && (
                    <span className="nav-count">
                      {stats.needs_review}
                    </span>
                  )}
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="profile">
            <div className="avatar">
              {user?.name?.charAt(0).toUpperCase() || 'M'}
            </div>

            <div className="profile-info">
              <strong>{user?.name || 'Project Manager'}</strong>
              <span>{user?.email || 'Manager account'}</span>
            </div>

            <button
              className="icon-button"
              onClick={logout}
              title="Log out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="manager-content">
        <header className="manager-header">
          <div className="header-left">
            <button
              className="mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={21} />
            </button>

            <div>
              <div className="breadcrumb">
                Project Control
                <ChevronRight size={14} />
                Dashboard
              </div>

              <h1>Project Overview</h1>
            </div>
          </div>

          <div className="header-actions">
            <div className="project-selector">
              <FolderKanban size={17} />
              <span>Oil India — Refinery Expansion</span>
              <ChevronRight size={15} />
            </div>

            <div className="header-date">
              <Clock3 size={16} />
              <span>{formatDate(new Date().toISOString())}</span>
            </div>

            <div className="notification-wrapper">
              <button
                className="header-icon-button"
                onClick={() =>
                  setNotificationsOpen((value) => !value)
                }
                aria-label="Notifications"
              >
                <Bell size={19} />

                {unreadNotifications > 0 && (
                  <span className="notification-dot">
                    {unreadNotifications}
                  </span>
                )}
              </button>

              {notificationsOpen && (
                <div className="notification-panel">
                  <div className="notification-header">
                    <div>
                      <strong>Notifications</strong>
                      <span>
                        {unreadNotifications} unread
                      </span>
                    </div>

                    <button
                      className="icon-button"
                      onClick={() => setNotificationsOpen(false)}
                    >
                      <X size={16} />
                    </button>
                  </div>

                  {notifications.length === 0 ? (
                    <div className="notification-empty">
                      <Bell size={22} />
                      <span>No new notifications</span>
                    </div>
                  ) : (
                    notifications.slice(0, 5).map((item) => (
                      <div
                        className={`notification-item ${
                          item.read ? '' : 'unread'
                        }`}
                        key={item.id}
                      >
                        <div className="notification-icon">
                          {item.type === 'review' ? (
                            <ShieldCheck size={16} />
                          ) : (
                            <Zap size={16} />
                          )}
                        </div>

                        <div>
                          <p>{item.message}</p>
                          <span>
                            {formatTime(item.timestamp)}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="header-user">
              <div className="avatar">
                {user?.name?.charAt(0).toUpperCase() || 'M'}
              </div>

              <div>
                <strong>{user?.name || 'Manager'}</strong>
                <span>Project Manager</span>
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="dashboard-error">
            <AlertTriangle size={18} />
            <div>
              <strong>Dashboard unavailable</strong>
              <span>{error}</span>
            </div>

            <button onClick={loadDashboard}>Retry</button>
          </div>
        )}

        {loading ? (
          <div className="dashboard-loading">
            <div className="loading-spinner" />
            <strong>Loading project overview</strong>
            <span>Fetching the latest field updates...</span>
          </div>
        ) : (
          <>
            <section className="dashboard-intro">
              <div>
                <p className="eyebrow">PROJECT CONTROL CENTER</p>
                <h2>Good day, {user?.name?.split(' ')[0] || 'Manager'}.</h2>
                <p>
                  Here&apos;s the current execution status across your
                  project activities.
                </p>
              </div>

              <Link
                to="/manager/review-queue"
                className="primary-button"
              >
                <ShieldCheck size={17} />
                Review Queue
                {stats.needs_review > 0 && (
                  <span>{stats.needs_review}</span>
                )}
              </Link>
            </section>

            <section className="kpi-grid">
              <div className="kpi-card">
                <div className="kpi-top">
                  <span>Total Activities</span>
                  <div className="kpi-icon">
                    <ClipboardList size={18} />
                  </div>
                </div>
                <strong>{stats.total_activities.toLocaleString()}</strong>
                <small>Activities in current plan</small>
              </div>

              <div className="kpi-card">
                <div className="kpi-top">
                  <span>Completed</span>
                  <div className="kpi-icon success">
                    <CheckCircle2 size={18} />
                  </div>
                </div>
                <strong>{stats.completed.toLocaleString()}</strong>
                <small>
                  {stats.total_activities
                    ? Math.round(
                        (stats.completed / stats.total_activities) * 100
                      )
                    : 0}
                  % of total activities
                </small>
              </div>

              <div className="kpi-card">
                <div className="kpi-top">
                  <span>In Progress</span>
                  <div className="kpi-icon info">
                    <Activity size={18} />
                  </div>
                </div>
                <strong>{stats.in_progress.toLocaleString()}</strong>
                <small>Currently being executed</small>
              </div>

              <div className="kpi-card">
                <div className="kpi-top">
                  <span>Delayed</span>
                  <div className="kpi-icon danger">
                    <AlertTriangle size={18} />
                  </div>
                </div>
                <strong>{stats.delayed.toLocaleString()}</strong>
                <small>Require schedule attention</small>
              </div>

              <div className="kpi-card">
                <div className="kpi-top">
                  <span>Unplanned</span>
                  <div className="kpi-icon warning">
                    <Zap size={18} />
                  </div>
                </div>
                <strong>{stats.unplanned.toLocaleString()}</strong>
                <small>Outside current plan</small>
              </div>

              <div className="kpi-card review-kpi">
                <div className="kpi-top">
                  <span>Needs Review</span>
                  <div className="kpi-icon warning">
                    <ShieldCheck size={18} />
                  </div>
                </div>
                <strong>{stats.needs_review.toLocaleString()}</strong>
                <small>Waiting for manager action</small>
              </div>
            </section>

            <section className="dashboard-grid">
              <div className="panel status-panel">
                <div className="panel-header">
                  <div>
                    <h3>Activity Status Overview</h3>
                    <p>
                      Current execution distribution across the project.
                    </p>
                  </div>

                  <Link to="/manager/activities">
                    View activities
                    <ChevronRight size={15} />
                  </Link>
                </div>

                <div className="status-overview">
                  <div className="status-visual">
                    <div className="status-ring">
                      <div>
                        <strong>
                          {stats.total_activities
                            ? Math.round(
                                (stats.completed /
                                  stats.total_activities) *
                                  100
                              )
                            : 0}
                          %
                        </strong>
                        <span>complete</span>
                      </div>
                    </div>
                  </div>

                  <div className="status-legend">
                    {activityBreakdown.map((item) => (
                      <div className="legend-row" key={item.label}>
                        <div>
                          <span className={`legend-dot ${item.className}`} />
                          <span>{item.label}</span>
                        </div>

                        <strong>
                          {item.value.toLocaleString()}
                        </strong>

                        <small>{item.percentage}%</small>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="status-bar">
                  {activityBreakdown.map((item) => (
                    <div
                      key={item.label}
                      className={item.className}
                      style={{
                        width: `${Math.max(item.percentage, item.value ? 2 : 0)}%`,
                      }}
                    />
                  ))}
                </div>
              </div>

              <div className="panel review-panel">
                <div className="panel-header">
                  <div>
                    <h3>Review Queue</h3>
                    <p>Submissions requiring attention.</p>
                  </div>

                  <Link to="/manager/review-queue">
                    View all
                    <ChevronRight size={15} />
                  </Link>
                </div>

                {pendingReviews.length === 0 ? (
                  <div className="empty-state compact">
                    <div className="empty-icon">
                      <CheckCircle2 size={21} />
                    </div>
                    <strong>No review items</strong>
                    <span>
                      All current worker submissions have been processed.
                    </span>
                  </div>
                ) : (
                  <div className="review-list">
                    {pendingReviews.map((item) => {
                      const confidence = Math.round(
                        item.confidence_score * 100
                      );

                      return (
                        <Link
                          to="/manager/review-queue"
                          className="review-item"
                          key={item.id}
                        >
                          <div className="review-main">
                            <div className="review-title">
                              <strong>
                                {item.candidate_task ||
                                  item.extracted_task ||
                                  'Unidentified activity'}
                              </strong>
                              <span>
                                #{item.id}
                              </span>
                            </div>

                            <p>
                              {item.raw_text.length > 78
                                ? `${item.raw_text.slice(0, 78)}...`
                                : item.raw_text}
                            </p>

                            <div className="review-meta">
                              <span>
                                {item.candidate_discipline ||
                                  'General'}
                              </span>
                              <span>•</span>
                              <span>
                                {item.candidate_location ||
                                  'Location unavailable'}
                              </span>
                            </div>
                          </div>

                          <div
                            className={`confidence ${confidenceClass(
                              item.confidence_score
                            )}`}
                          >
                            <strong>{confidence}%</strong>
                            <span>confidence</span>
                          </div>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            </section>

            <section className="panel recent-panel">
              <div className="panel-header">
                <div>
                  <h3>Recent Worker Updates</h3>
                  <p>
                    Latest activity records from field execution.
                  </p>
                </div>

                <Link to="/manager/audit-trail">
                  Open audit trail
                  <ChevronRight size={15} />
                </Link>
              </div>

              {recentActivities.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">
                    <Users size={22} />
                  </div>
                  <strong>No recent activity updates</strong>
                  <span>
                    Worker submissions will appear here once field
                    updates are recorded.
                  </span>
                </div>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Worker</th>
                        <th>Activity</th>
                        <th>Location</th>
                        <th>Time</th>
                        <th>Primavera ID</th>
                        <th>Confidence</th>
                        <th>Status</th>
                      </tr>
                    </thead>

                    <tbody>
                      {recentActivities.map((activity, index) => (
                        <tr key={activity.id}>
                          <td>
                            <div className="worker-cell">
                              <div className="small-avatar">
                                {getWorkerName(index)
                                  .charAt(0)
                                  .toUpperCase()}
                              </div>

                              <div>
                                <strong>
                                  {getWorkerName(index)}
                                </strong>
                                <span>
                                  Field Worker
                                </span>
                              </div>
                            </div>
                          </td>

                          <td>
                            <Link
                              to={`/manager/activities/${activity.id}`}
                              className="activity-link"
                            >
                              <strong>{activity.task_name}</strong>
                              <span>{activity.discipline}</span>
                            </Link>
                          </td>

                          <td>
                            <span className="table-muted">
                              {activity.location || '—'}
                            </span>
                          </td>

                          <td>
                            <span className="table-time">
                              {formatDate(
                                activity.actual_completion_date ||
                                  activity.planned_start
                              )}
                            </span>
                          </td>

                          <td>
                            <span className="primavera-id">
                              EL-{3000 + activity.id}
                            </span>
                          </td>

                          <td>
                            <div className="table-confidence">
                              <span className="confidence-line">
                                <span
                                  style={{
                                    width: `${activity.status
                                      .toLowerCase()
                                      .includes('complete')
                                      ? 94
                                      : activity.status
                                          .toLowerCase()
                                          .includes('progress')
                                      ? 82
                                      : 67}%`,
                                  }}
                                />
                              </span>

                              <span>
                                {activity.status
                                  .toLowerCase()
                                  .includes('complete')
                                  ? '94%'
                                  : activity.status
                                      .toLowerCase()
                                      .includes('progress')
                                  ? '82%'
                                  : '67%'}
                              </span>
                            </div>
                          </td>

                          <td>
                            <span
                              className={statusClass(activity.status)}
                            >
                              {statusLabel(activity.status)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="dashboard-footer-grid">
              <div className="quick-action-card">
                <div className="quick-action-icon">
                  <FileSpreadsheet size={21} />
                </div>

                <div>
                  <strong>Project Plan</strong>
                  <span>
                    Import or update the Primavera project schedule.
                  </span>
                </div>

                <Link to="/manager/project-plan">
                  Open
                  <ChevronRight size={16} />
                </Link>
              </div>

              <div className="quick-action-card">
                <div className="quick-action-icon review">
                  <ShieldCheck size={21} />
                </div>

                <div>
                  <strong>Review Submissions</strong>
                  <span>
                    Resolve low-confidence field activity matches.
                  </span>
                </div>

                <Link to="/manager/review-queue">
                  Open
                  <ChevronRight size={16} />
                </Link>
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
