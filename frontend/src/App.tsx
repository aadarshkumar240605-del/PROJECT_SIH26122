import { useState } from 'react';

type Screen =
  | 'login'
  | 'worker-home'
  | 'worker-voice'
  | 'worker-history'
  | 'worker-profile'
  | 'manager-dashboard'
  | 'manager-activities'
  | 'manager-review'
  | 'manager-unplanned'
  | 'manager-audit';

const workerScreens: Screen[] = [
  'worker-home',
  'worker-voice',
  'worker-history',
  'worker-profile',
];

const managerScreens: Screen[] = [
  'manager-dashboard',
  'manager-activities',
  'manager-review',
  'manager-unplanned',
  'manager-audit',
];

function Login({ onLogin }: { onLogin: (role: 'worker' | 'manager') => void }) {
  return (
    <div className="login-shell">
      <div className="login-panel">
        <div className="login-brand">
          <div className="fieldtrack-mark">F</div>
          <div>
            <div className="fieldtrack-name">FIELDTRACK</div>
            <div className="fieldtrack-subtitle">Field Operations System</div>
          </div>
        </div>

        <div className="login-heading">
          <div className="eyebrow">Secure access</div>
          <h1>Welcome back</h1>
          <p>
            Sign in to continue to your assigned field operations workspace.
          </p>
        </div>

        <div className="login-fields">
          <label>
            Institutional email
            <input
              type="email"
              placeholder="name@company.in"
              defaultValue="rahul.sharma@oilindia.in"
            />
          </label>

          <label>
            Access credential
            <input
              type="password"
              placeholder="Enter your credential"
              defaultValue="fieldtrack"
            />
          </label>

          <div className="login-options">
            <label className="checkbox-label">
              <input type="checkbox" defaultChecked />
              Keep device verified
            </label>

            <button type="button" className="text-button">
              Forgot credential?
            </button>
          </div>
        </div>

        <button
          className="primary-action"
          onClick={() => onLogin('worker')}
        >
          Sign in
          <span>→</span>
        </button>

        <div className="login-divider">
          <span>or</span>
        </div>

        <div className="role-buttons">
          <button
            className="role-button"
            onClick={() => onLogin('worker')}
          >
            <span>
              <strong>Site Worker</strong>
              <small>Field reporting & work logs</small>
            </span>
            <span>→</span>
          </button>

          <button
            className="role-button"
            onClick={() => onLogin('manager')}
          >
            <span>
              <strong>Project Manager</strong>
              <small>Planning & execution control</small>
            </span>
            <span>→</span>
          </button>
        </div>

        <div className="login-footer">
          FIELDTRACK · SIH26122 · OIL INDIA LIMITED
        </div>
      </div>
    </div>
  );
}

function WorkerShell({
  screen,
  setScreen,
}: {
  screen: Screen;
  setScreen: (screen: Screen) => void;
}) {
  const [recording, setRecording] = useState(false);

  return (
    <div className="worker-shell">
      <header className="worker-header">
        <button
          className="header-icon-button"
          onClick={() => setScreen('worker-home')}
          aria-label="Home"
        >
          F
        </button>

        <div className="worker-brand">
          <strong>FIELDTRACK</strong>
          <span>FIELD OPERATIONS</span>
        </div>

        <div className="worker-status">
          <span className="status-dot" />
          ONLINE
        </div>
      </header>

      <main className="worker-content">
        {screen === 'worker-home' && (
          <>
            <div className="screen-context">
              <span>SHIFT · DAY A</span>
              <span>SECTOR 04 · CDU</span>
            </div>

            <section className="worker-heading">
              <div>
                <div className="eyebrow">Current shift</div>
                <h1>Good morning, Rahul.</h1>
                <p>Record what was completed on site.</p>
              </div>
            </section>

            <section className="assignment-card">
              <div className="section-label">ACTIVE ASSIGNMENT</div>

              <div className="assignment-main">
                <div>
                  <strong>Electrical Conduit Installation</strong>
                  <span>Level 3 · East Wing</span>
                </div>

                <span className="assignment-code">EL-3042</span>
              </div>

              <div className="assignment-meta">
                <span>Today · 08:00–17:00</span>
                <span>Zone B4 Grid</span>
              </div>
            </section>

            <section className="work-entry">
              <div className="section-label">FIELD WORK LOG</div>

              <button
                className={`voice-action ${recording ? 'recording' : ''}`}
                onClick={() => {
                  setRecording(!recording);
                  if (!recording) {
                    setScreen('worker-voice');
                  }
                }}
              >
                <span className="voice-icon">●</span>

                <span>
                  <strong>{recording ? 'Listening…' : 'Describe your work'}</strong>
                  <small>Speak in English or Hindi</small>
                </span>

                <span className="voice-arrow">→</span>
              </button>

              <div className="text-entry">
                <input placeholder="Or type your update…" />
                <button
                  onClick={() => setScreen('worker-voice')}
                  aria-label="Submit typed update"
                >
                  →
                </button>
              </div>
            </section>

            <section className="worker-status-card">
              <div>
                <span className="section-label">SYNC STATUS</span>
                <strong>Connected</strong>
              </div>

              <span className="status-online">
                <span className="status-dot" />
                ONLINE
              </span>
            </section>
          </>
        )}

        {screen === 'worker-voice' && (
          <>
            <button
              className="back-button"
              onClick={() => setScreen('worker-home')}
            >
              ← Back
            </button>

            <div className="worker-heading">
              <div className="eyebrow">Work log · Voice input</div>
              <h1>What did you complete?</h1>
              <p>Describe the work naturally. FIELDTRACK will extract the activity, quantity and location.</p>
            </div>

            <div className="voice-record-panel">
              <button
                className={`record-button ${recording ? 'recording' : ''}`}
                onClick={() => setRecording(!recording)}
              >
                <span>{recording ? '■' : '●'}</span>
              </button>

              <strong>{recording ? 'Listening' : 'Tap to speak'}</strong>
              <small>English / हिन्दी</small>

              {recording && (
                <div className="waveform">
                  {Array.from({ length: 22 }).map((_, index) => (
                    <span
                      key={index}
                      style={{
                        height: `${12 + ((index * 17) % 28)}px`,
                      }}
                    />
                  ))}
                </div>
              )}
            </div>

            <div className="transcription-card">
              <div className="section-label">LIVE TRANSCRIPTION</div>
              <p>
                “Laid 40m of conduit on Level 3 east wing from 2 to 3 PM.”
              </p>
            </div>

            <button
              className="primary-action"
              onClick={() => setScreen('worker-home')}
            >
              Process work log
              <span>→</span>
            </button>
          </>
        )}

        {screen === 'worker-history' && (
          <>
            <div className="worker-heading">
              <div className="eyebrow">Records</div>
              <h1>Submission history</h1>
              <p>Your recent field updates and their schedule links.</p>
            </div>

            <div className="history-list">
              {[
                ['SUB-00845', 'Electrical Conduit Installation', 'Auto-linked', '94%'],
                ['SUB-00839', 'Pipe Support Alignment', 'Confirmed', '88%'],
                ['SUB-00832', 'Structural Inspection', 'Review required', '61%'],
              ].map(([id, activity, status, confidence]) => (
                <button
                  className="history-item"
                  key={id}
                  onClick={() => setScreen('worker-home')}
                >
                  <div>
                    <span>{id}</span>
                    <strong>{activity}</strong>
                    <small>Today · Level 3 · East Wing</small>
                  </div>

                  <div className="history-result">
                    <span>{status}</span>
                    <strong>{confidence}</strong>
                  </div>
                </button>
              ))}
            </div>
          </>
        )}

        {screen === 'worker-profile' && (
          <>
            <div className="worker-heading">
              <div className="eyebrow">Account</div>
              <h1>Profile</h1>
            </div>

            <section className="profile-card">
              <div className="profile-avatar">RS</div>
              <div>
                <strong>Rahul Sharma</strong>
                <span>Site Worker · Badge TK-4091</span>
              </div>
            </section>

            {[
              ['Terminal', 'Numaligarh, Assam'],
              ['Assigned sector', 'Sector 04 · CDU'],
              ['Language', 'English / हिन्दी'],
              ['Device status', 'Verified'],
            ].map(([label, value]) => (
              <div className="profile-row" key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </>
        )}
      </main>

      <nav className="worker-bottom-nav">
        <button
          className={screen === 'worker-home' ? 'active' : ''}
          onClick={() => setScreen('worker-home')}
        >
          <span>⌂</span>
          Home
        </button>

        <button
          className={screen === 'worker-history' ? 'active' : ''}
          onClick={() => setScreen('worker-history')}
        >
          <span>≡</span>
          History
        </button>

        <button
          className={screen === 'worker-profile' ? 'active' : ''}
          onClick={() => setScreen('worker-profile')}
        >
          <span>○</span>
          Profile
        </button>
      </nav>
    </div>
  );
}

function ManagerShell({
  screen,
  setScreen,
}: {
  screen: Screen;
  setScreen: (screen: Screen) => void;
}) {
  const [mobileNav, setMobileNav] = useState(false);

  const navItems: Array<[Screen, string, string]> = [
    ['manager-dashboard', 'Overview', '01'],
    ['manager-activities', 'Activities', '10'],
    ['manager-review', 'Review queue', '03'],
    ['manager-unplanned', 'Unplanned work', '01'],
    ['manager-audit', 'Audit trail', ''],
  ];

  return (
    <div className="manager-shell">
      {mobileNav && (
        <button
          className="sidebar-overlay"
          onClick={() => setMobileNav(false)}
          aria-label="Close navigation"
        />
      )}

      <aside className={`manager-sidebar ${mobileNav ? 'open' : ''}`}>
        <div className="manager-brand">
          <div className="fieldtrack-mark small">F</div>
          <div>
            <strong>FIELDTRACK</strong>
            <span>PROJECT CONTROL</span>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileNav(false)}
          >
            ×
          </button>
        </div>

        <div className="project-context">
          <span>ACTIVE PROJECT</span>
          <strong>Oil India Refinery Expansion</strong>
          <small>Block 4B · Numaligarh</small>
        </div>

        <nav className="manager-nav">
          {navItems.map(([target, label, count]) => (
            <button
              key={target}
              className={screen === target ? 'active' : ''}
              onClick={() => {
                setScreen(target);
                setMobileNav(false);
              }}
            >
              <span>{label}</span>
              {count && <small>{count}</small>}
            </button>
          ))}
        </nav>

        <div className="manager-sidebar-footer">
          <div className="manager-user">
            <div className="user-avatar">AK</div>
            <div>
              <strong>A. Kumar</strong>
              <span>Project Manager</span>
            </div>
          </div>

          <button
            className="signout-button"
            onClick={() => setScreen('login')}
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="manager-main">
        <header className="manager-topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileNav(true)}
            aria-label="Open navigation"
          >
            ☰
          </button>

          <div>
            <span className="manager-kicker">
              OIL INDIA · REFINERY EXPANSION
            </span>
            <strong>
              {screen === 'manager-dashboard'
                ? 'Project control'
                : navItems.find(([target]) => target === screen)?.[1]}
            </strong>
          </div>

          <div className="manager-topbar-right">
            <span className="sync-indicator">
              <span className="status-dot" />
              System online
            </span>

            <button
              className="user-avatar top-avatar"
              onClick={() => setScreen('login')}
            >
              AK
            </button>
          </div>
        </header>

        <section className="manager-content">
          {screen === 'manager-dashboard' && (
            <ManagerDashboard setScreen={setScreen} />
          )}

          {screen === 'manager-activities' && (
            <ManagerActivities setScreen={setScreen} />
          )}

          {screen === 'manager-review' && (
            <ManagerReview setScreen={setScreen} />
          )}

          {screen === 'manager-unplanned' && (
            <ManagerUnplanned setScreen={setScreen} />
          )}

          {screen === 'manager-audit' && (
            <ManagerAudit setScreen={setScreen} />
          )}
        </section>
      </main>
    </div>
  );
}

function ManagerDashboard({
  setScreen,
}: {
  setScreen: (screen: Screen) => void;
}) {
  const metrics = [
    ['Activities', '10', 'Plan baseline'],
    ['Completed', '3', '30% of baseline'],
    ['In progress', '2', 'On site'],
    ['Delayed', '2', 'Needs attention'],
    ['Unplanned', '1', 'Field reports'],
  ];

  return (
    <>
      <div className="page-heading-row">
        <div>
          <div className="eyebrow">Overview</div>
          <h1>Project control</h1>
          <p>Execution status against the current Primavera baseline.</p>
        </div>

        <button className="outline-action">
          Upload schedule
        </button>
      </div>

      <div className="metric-strip">
        {metrics.map(([label, value, description]) => (
          <div className="metric" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
            <small>{description}</small>
          </div>
        ))}
      </div>

      <section className="manager-section">
        <div className="section-heading-row">
          <div>
            <span className="eyebrow">Baseline vs actual</span>
            <h2>Execution status</h2>
          </div>

          <button
            className="text-button"
            onClick={() => setScreen('manager-activities')}
          >
            View activities →
          </button>
        </div>

        <div className="activity-table">
          {[
            ['CIV-101', 'Excavation for tank foundation', 'Civil', '72%', 'In Progress'],
            ['CIV-102', 'Concrete pouring for tank base', 'Civil', '100%', 'Completed'],
            ['CIV-205', 'Foundation work for control room', 'Civil', '45%', 'Delayed'],
            ['PIP-110', 'Pipe welding near tank 3', 'Piping', '100%', 'Completed'],
            ['PIP-210', 'Pipeline laying in corridor', 'Piping', '68%', 'In Progress'],
          ].map(([id, name, discipline, progress, status]) => (
            <button
              className="activity-row"
              key={id}
              onClick={() => setScreen('manager-activities')}
            >
              <span className="activity-id">{id}</span>
              <span className="activity-name">
                <strong>{name}</strong>
                <small>{discipline}</small>
              </span>
              <span className="activity-progress">
                <span className="mini-progress">
                  <i style={{ width: progress }} />
                </span>
                {progress}
              </span>
              <span className={`status-label ${status.toLowerCase().replace(' ', '-')}`}>
                {status}
              </span>
            </button>
          ))}
        </div>
      </section>

      <div className="manager-two-column">
        <section className="manager-section">
          <div className="section-heading-row">
            <div>
              <span className="eyebrow">Needs decision</span>
              <h2>Review queue</h2>
            </div>

            <button
              className="text-button"
              onClick={() => setScreen('manager-review')}
            >
              Open queue →
            </button>
          </div>

          <div className="review-summary">
            <strong>3</strong>
            <div>
              <span>field submissions</span>
              <small>awaiting manager confirmation</small>
            </div>
          </div>
        </section>

        <section className="manager-section">
          <div className="section-heading-row">
            <div>
              <span className="eyebrow">Recent</span>
              <h2>Field activity</h2>
            </div>

            <button
              className="text-button"
              onClick={() => setScreen('manager-audit')}
            >
              Audit trail →
            </button>
          </div>

          <div className="recent-event">
            <span>08:20</span>
            <div>
              <strong>Pipe welding near tank 3</strong>
              <small>Auto-linked · PIP-110 · A. Kumar</small>
            </div>
          </div>

          <div className="recent-event">
            <span>10:40</span>
            <div>
              <strong>Cable tray installation</strong>
              <small>Manual confirmed · ELE-321 · S. Patel</small>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}

function ManagerActivities({
  setScreen,
}: {
  setScreen: (screen: Screen) => void;
}) {
  return (
    <>
      <div className="page-heading-row">
        <div>
          <div className="eyebrow">Planning</div>
          <h1>Activities</h1>
          <p>Current Primavera baseline and actual field progress.</p>
        </div>

        <div className="inline-actions">
          <button className="outline-action">Filter</button>
          <button className="primary-small">Export</button>
        </div>
      </div>

      <div className="filter-bar">
        <input placeholder="Search activity or ID" />
        <select defaultValue="all">
          <option value="all">All disciplines</option>
          <option>Civil</option>
          <option>Piping</option>
          <option>Electrical</option>
          <option>Instrumentation</option>
        </select>
        <select defaultValue="all">
          <option value="all">All statuses</option>
          <option>Completed</option>
          <option>In Progress</option>
          <option>Delayed</option>
        </select>
      </div>

      <section className="manager-section table-section">
        <div className="activity-table detailed">
          {[
            ['CIV-101', 'Excavation for tank foundation', 'Civil', 'Zone A · Tank Farm', '01 Sep — 07 Sep', '72%', 'In Progress'],
            ['CIV-102', 'Concrete pouring for tank base', 'Civil', 'Zone A · Tank Farm', '03 Sep — 10 Sep', '100%', 'Completed'],
            ['CIV-205', 'Foundation work for control room', 'Civil', 'Zone D · Control Room', '02 Sep — 09 Sep', '45%', 'Delayed'],
            ['PIP-110', 'Pipe welding near tank 3', 'Piping', 'Zone A · Tank Farm', '04 Sep — 11 Sep', '100%', 'Completed'],
            ['PIP-210', 'Pipeline laying in corridor', 'Piping', 'Zone B · Pipeline Corridor', '03 Sep — 12 Sep', '68%', 'In Progress'],
            ['ELE-321', 'Cable tray installation', 'Electrical', 'Zone C · Substation', '01 Sep — 07 Sep', '12%', 'Not Started'],
            ['ELE-420', 'HT cable pulling', 'Electrical', 'Zone C · Substation', '03 Sep — 10 Sep', '52%', 'Delayed'],
          ].map(([id, name, discipline, location, dates, progress, status]) => (
            <button
              className="activity-row detailed-row"
              key={id}
              onClick={() => setScreen('manager-dashboard')}
            >
              <span className="activity-id">{id}</span>

              <span className="activity-name">
                <strong>{name}</strong>
                <small>{discipline} · {location}</small>
              </span>

              <span className="activity-dates">{dates}</span>

              <span className="activity-progress">
                <span className="mini-progress">
                  <i style={{ width: progress }} />
                </span>
                {progress}
              </span>

              <span className={`status-label ${status.toLowerCase().replace(' ', '-')}`}>
                {status}
              </span>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

function ManagerReview({
  setScreen,
}: {
  setScreen: (screen: Screen) => void;
}) {
  return (
    <>
      <div className="page-heading-row">
        <div>
          <div className="eyebrow">Matching</div>
          <h1>Review queue</h1>
          <p>Field submissions requiring manager confirmation.</p>
        </div>
      </div>

      <div className="review-list">
        {[
          ['SUB-00846', 'A. Kumar', 'Pipe welding near tank 3', 'PIP-110', '87%'],
          ['SUB-00847', 'S. Patel', 'Cable tray installation', 'ELE-321', '71%'],
          ['SUB-00848', 'R. Singh', 'Temporary safety barricade', 'HSE-010', '63%'],
        ].map(([id, worker, description, suggested, confidence]) => (
          <article className="review-card" key={id}>
            <div className="review-card-header">
              <div>
                <span>{id} · {worker}</span>
                <h2>{description}</h2>
              </div>

              <strong>{confidence}</strong>
            </div>

            <div className="review-match">
              <span>Suggested schedule activity</span>
              <strong>{suggested}</strong>
            </div>

            <p>
              The field report has been matched against the Primavera baseline.
              Confirm the suggested activity or route it elsewhere.
            </p>

            <div className="review-actions">
              <button
                className="primary-small"
                onClick={() => setScreen('manager-dashboard')}
              >
                Confirm match
              </button>

              <button
                className="outline-action"
                onClick={() => setScreen('manager-activities')}
              >
                Reassign
              </button>

              <button
                className="danger-action"
                onClick={() => setScreen('manager-unplanned')}
              >
                Mark unplanned
              </button>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

function ManagerUnplanned({
  setScreen,
}: {
  setScreen: (screen: Screen) => void;
}) {
  return (
    <>
      <div className="page-heading-row">
        <div>
          <div className="eyebrow">Exception register</div>
          <h1>Unplanned work</h1>
          <p>Field work reported outside the current schedule baseline.</p>
        </div>
      </div>

      <section className="manager-section">
        <div className="unplanned-record">
          <div>
            <span className="section-label">UNPL-001</span>
            <h2>Additional concrete patch work</h2>
            <p>
              Reported from Zone B following access-road damage. No direct
              Primavera activity match was found.
            </p>
          </div>

          <div className="unplanned-meta">
            <span>Reporter</span>
            <strong>R. Singh</strong>

            <span>Confidence</span>
            <strong>44%</strong>

            <span>Status</span>
            <strong>Pending decision</strong>
          </div>
        </div>

        <div className="review-actions">
          <button
            className="primary-small"
            onClick={() => setScreen('manager-dashboard')}
          >
            Accept record
          </button>

          <button className="outline-action">
            Create activity
          </button>
        </div>
      </section>
    </>
  );
}

function ManagerAudit({
  setScreen,
}: {
  setScreen: (screen: Screen) => void;
}) {
  return (
    <>
      <div className="page-heading-row">
        <div>
          <div className="eyebrow">Traceability</div>
          <h1>Audit trail</h1>
          <p>Immutable history of field submissions and schedule decisions.</p>
        </div>
      </div>

      <section className="manager-section">
        <div className="audit-table">
          {[
            ['05 Sep · 08:20', 'A. Kumar', 'Pipe welding near tank 3', 'PIP-110', 'Auto-linked', '87%'],
            ['05 Sep · 10:40', 'S. Patel', 'Cable tray installation', 'ELE-321', 'Manual confirmed', '79%'],
            ['05 Sep · 12:05', 'R. Singh', 'New concrete patch work', 'UNPL-001', 'Unplanned', '44%'],
          ].map(([time, worker, input, activity, result, score]) => (
            <button
              className="audit-row"
              key={`${time}-${worker}`}
              onClick={() => setScreen('manager-dashboard')}
            >
              <span>{time}</span>
              <strong>{worker}</strong>
              <span>{input}</span>
              <strong>{activity}</strong>
              <span>{result}</span>
              <strong>{score}</strong>
            </button>
          ))}
        </div>
      </section>
    </>
  );
}

export default function App() {
  const [screen, setScreen] = useState<Screen>('login');

  if (screen === 'login') {
    return <Login onLogin={(role) => setScreen(role === 'worker' ? 'worker-home' : 'manager-dashboard')} />;
  }

  if (workerScreens.includes(screen)) {
    return <WorkerShell screen={screen} setScreen={setScreen} />;
  }

  if (managerScreens.includes(screen)) {
    return <ManagerShell screen={screen} setScreen={setScreen} />;
  }

  return null;
}
