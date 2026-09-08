/* ============================================================
   FIELDTRACK — App Shell & Screens
   State-based prototype router. Every route reachable, every
   action functional against the mock data layer.
   ============================================================ */

import { useEffect, useState } from 'react';
import {
  ACTIVITIES, AUDIT_TRAIL, PROJECT, REVIEW_QUEUE, SUBMISSIONS, WORKER,
  simulateMatch, statusCounts, formatDate,
  type Activity, type AuditEntry, type MatchResult, type ReviewItem, type Submission,
} from './data/mock';

type Role = 'worker' | 'manager';
type Route =
  | 'login'
  | 'w-home' | 'w-voice' | 'w-processing' | 'w-match' | 'w-success'
  | 'w-history' | 'w-submission' | 'w-profile'
  | 'm-dashboard' | 'm-activities' | 'm-activity' | 'm-review'
  | 'm-unplanned' | 'm-audit' | 'm-settings';

const STATUS_BADGE: Record<string, string> = {
  'Completed': 'badge badge-ok',
  'In Progress': 'badge badge-info',
  'Delayed': 'badge badge-danger',
  'Not Started': 'badge badge-neutral',
  'Unplanned': 'badge badge-warn',
};

function StatusBadge({ status }: { status: string }) {
  return <span className={STATUS_BADGE[status] ?? 'badge badge-neutral'}>{status}</span>;
}

/* ---------------- Icons (minimal, one style) ---------------- */

const Icon = {
  home: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M3 10.5 12 3l9 7.5V21H3z" strokeLinejoin="round" /></svg>,
  history: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" strokeLinecap="round" /></svg>,
  user: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 5-5.5 8-5.5s6.5 1.5 8 5.5" strokeLinecap="round" /></svg>,
  mic: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" strokeLinecap="round" /></svg>,
};

/* ---------------- Worker chrome ---------------- */

function TopBar({ lang, setLang }: { lang: 'EN' | 'HI'; setLang: (l: 'EN' | 'HI') => void }) {
  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <div className="brand-mark">FT</div>
          <div>
            <div className="brand-name">FIELDTRACK</div>
            <div className="brand-sub">SIH26122 · REFINERY</div>
          </div>
        </div>
        <div className="row" style={{ gap: 'var(--s2)' }}>
          <span className="t-11 text-muted mono">● ONLINE</span>
          <div className="lang-toggle">
            {(['EN', 'HI'] as const).map(l => (
              <button key={l} className={l === lang ? 'active' : ''} onClick={() => setLang(l)}>{l === 'EN' ? 'EN' : 'हिं'}</button>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}

function TabBar({ route, go }: { route: Route; go: (r: Route) => void }) {
  const tabs: { r: Route; label: string; icon: JSX.Element }[] = [
    { r: 'w-home', label: 'Home', icon: Icon.home },
    { r: 'w-history', label: 'History', icon: Icon.history },
    { r: 'w-profile', label: 'Profile', icon: Icon.user },
  ];
  return (
    <nav className="tabbar">
      <div className="tabbar-inner">
        {tabs.map(t => (
          <button key={t.r} className={`tab ${route === t.r ? 'active' : ''}`} onClick={() => go(t.r)}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>
    </nav>
  );
}

/* ---------------- Login ---------------- */

function Login({ onLogin }: { onLogin: (role: Role) => void }) {
  const [role, setRole] = useState<Role>('worker');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = () => {
    if (loading) return;
    setLoading(true);
    setTimeout(() => onLogin(role), 700);
  };

  return (
    <div style={{ minHeight: '100dvh', display: 'grid', placeItems: 'center', padding: 'var(--s4)' }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div className="row-between" style={{ marginBottom: 'var(--s5)' }}>
          <span className="t-11 text-muted mono">● SYSTEM ONLINE</span>
          <span className="t-11 text-faint mono">REL-4.0.2</span>
        </div>

        <div className="stack" style={{ marginBottom: 'var(--s5)' }}>
          <div className="badge badge-neutral" style={{ alignSelf: 'flex-start' }}>{PROJECT.code} · {PROJECT.name}</div>
          <h1 className="t-28">Welcome back</h1>
          <p className="t-13 text-muted">Field Operations & Shift Access</p>
        </div>

        <div className="panel">
          <div className="panel-body stack">
            <div className="stack-sm">
              <div className="label">Select account role</div>
              <div className="stack-sm">
                <button className={`role-card ${role === 'worker' ? 'active' : ''}`} onClick={() => { setRole('worker'); setEmail('rahul.sharma@oilindia.in'); }}>
                  <div>
                    <div className="t-13" style={{ fontWeight: 600 }}>Site Worker</div>
                    <div className="t-12 text-muted">Field mobile · voice reporting</div>
                  </div>
                  <span className="badge badge-ink" style={{ marginLeft: 'auto' }}>FIELD MOBILE</span>
                </button>
                <button className={`role-card ${role === 'manager' ? 'active' : ''}`} onClick={() => { setRole('manager'); setEmail('manager@oilindia.in'); }}>
                  <div>
                    <div className="t-13" style={{ fontWeight: 600 }}>Project Manager</div>
                    <div className="t-12 text-muted">Review queue · schedule control</div>
                  </div>
                  <span className="badge badge-neutral" style={{ marginLeft: 'auto' }}>CONSOLE</span>
                </button>
              </div>
            </div>

            <div className="field">
              <label className="label" htmlFor="ft-email">Institutional email</label>
              <input id="ft-email" className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="name@oilindia.in" />
            </div>
            <div className="field">
              <label className="label" htmlFor="ft-pass">Shift security credential</label>
              <input id="ft-pass" className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Enter password" />
            </div>

            <button className={`btn btn-primary btn-lg btn-block ${loading ? 'is-loading' : ''}`} onClick={submit} disabled={loading}>
              Authenticate Session →
            </button>
          </div>
        </div>

        <div className="row-between" style={{ marginTop: 'var(--s4)' }}>
          <span className="t-11 text-faint">Terminal location · Numaligarh, Assam</span>
          <span className="t-11 text-faint mono">REF-AS-8942</span>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Worker: Home ---------------- */

function WorkerHome({ submissions, go, openSubmission }: {
  submissions: Submission[]; go: (r: Route) => void; openSubmission: (id: string) => void;
}) {
  return (
    <div className="page-mobile stack-lg">
      <div className="panel panel-ink" style={{ padding: 'var(--s4)' }}>
        <div className="label" style={{ marginBottom: 'var(--s2)' }}>Shift assignment · Active</div>
        <div className="t-16" style={{ fontWeight: 600 }}>{WORKER.name} · {WORKER.badge}</div>
        <div className="t-12" style={{ opacity: 0.7, marginTop: 2 }}>{WORKER.sector}</div>
        <div className="row" style={{ marginTop: 'var(--s3)', gap: 'var(--s2)' }}>
          <span className="badge badge-ok">● ON SHIFT</span>
          <span className="badge" style={{ background: 'rgba(255,255,255,0.14)', color: '#fff' }}>{WORKER.contractor}</span>
        </div>
      </div>

      <div className="stack">
        <div className="label">Report today's work</div>
        <button className="btn btn-primary btn-lg btn-block" onClick={() => go('w-voice')}>
          {Icon.mic} Describe Your Work
        </button>
        <p className="t-12 text-muted" style={{ textAlign: 'center' }}>
          Speak or type — English or Hindi. FIELDTRACK matches it to the Primavera P6 schedule.
        </p>
      </div>

      <div className="stack-sm">
        <div className="row-between">
          <div className="label">Recent submissions</div>
          <button className="btn btn-ghost btn-sm" onClick={() => go('w-history')}>View all</button>
        </div>
        <div className="panel">
          {submissions.slice(0, 3).map((s, i) => (
            <button key={s.id} onClick={() => openSubmission(s.id)}
              style={{ display: 'block', width: '100%', textAlign: 'left', padding: 'var(--s3) var(--s4)', borderTop: i ? '1px solid var(--border)' : 'none' }}>
              <div className="row-between">
                <span className="t-13" style={{ fontWeight: 600 }}>{s.activity}</span>
                <span className={s.syncState === 'synced' ? 'badge badge-ok' : 'badge badge-warn'}>
                  {s.syncState === 'synced' ? 'SYNCED' : 'PENDING'}
                </span>
              </div>
              <div className="row-between" style={{ marginTop: 4 }}>
                <span className="t-11 text-faint mono">{s.id}</span>
                <span className="t-11 text-faint">{s.timestamp} · {s.confidence}%</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Worker: Voice input ---------------- */

function VoiceInput({ onProcess, goBack }: { onProcess: (text: string) => void; goBack: () => void }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [text, setText] = useState('');
  const SAMPLE_EN = 'Laid 40m of conduit on Level 3 east wing from 2 to 3 PM.';
  const SAMPLE_HI = 'मैंने बेस 3 के पास पाइप वेल्डिंग पूरी की, दोपहर 2 से 3 बजे तक।';

  useEffect(() => {
    if (!recording) return;
    setSeconds(0);
    const tick = setInterval(() => setSeconds(s => s + 1), 1000);
    const auto = setTimeout(() => { setText(SAMPLE_EN); setRecording(false); }, 3000);
    return () => { clearInterval(tick); clearTimeout(auto); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recording]);

  const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
  const ss = String(seconds % 60).padStart(2, '0');

  return (
    <div className="page-mobile stack-lg">
      <div className="row-between">
        <button className="btn btn-ghost btn-sm" onClick={goBack}>← Back</button>
        <span className="t-11 text-muted mono">WORK LOG MODE</span>
      </div>

      <div className="stack">
        <h1 className="t-22">Voice Input</h1>
        <p className="t-13 text-muted">Describe what you completed — activity, quantity, location, time.</p>
      </div>

      <div className="panel">
        <div className="panel-body" style={{ display: 'grid', placeItems: 'center', padding: 'var(--s6) var(--s4)' }}>
          <button
            className={`fab-record ${recording ? 'recording' : ''}`}
            onClick={() => setRecording(r => !r)}
            aria-label={recording ? 'Stop recording' : 'Start recording'}
          >
            <span style={{ width: 24, height: 24 }}>{Icon.mic}</span>
          </button>
          <div className="row" style={{ marginTop: 'var(--s4)', gap: 'var(--s2)' }}>
            <span className={`dot ${recording ? 'dot-live' : ''}`} style={{ background: recording ? undefined : 'var(--text-faint)' }} />
            <span className="t-13" style={{ fontWeight: 600 }}>{recording ? 'Listening Active' : 'Tap to record'}</span>
            <span className="t-13 mono text-muted">{recording ? `${mm}:${ss}` : '00:00'}</span>
          </div>
        </div>
      </div>

      <div className="field">
        <div className="label">Live transcription</div>
        <textarea
          className="textarea"
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Speak, or type your update here…"
        />
        <div className="row" style={{ gap: 'var(--s2)' }}>
          <button className="btn btn-secondary btn-sm" onClick={() => setText(SAMPLE_EN)}>Sample · English</button>
          <button className="btn btn-secondary btn-sm" onClick={() => setText(SAMPLE_HI)}>Sample · हिंदी</button>
        </div>
      </div>

      <button className="btn btn-primary btn-lg btn-block" disabled={!text.trim()} onClick={() => onProcess(text.trim())}>
        Process Update →
      </button>
    </div>
  );
}

/* ---------------- Worker: Processing ---------------- */

const PIPELINE = [
  { name: 'Voice Ingestion', desc: 'Received field audio binary' },
  { name: 'Tokenization', desc: 'Speech-to-text acoustic tokenization' },
  { name: 'Entity & Metric Extraction', desc: 'Extracting discipline & quantity metrics' },
  { name: 'Primavera Schedule Sync', desc: 'Cross-referencing P6 Rev 4.2 baseline' },
];

function Processing({ onDone }: { onDone: () => void }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = PIPELINE.map((_, i) => setTimeout(() => setStep(i + 1), 700 * (i + 1)));
    const finish = setTimeout(onDone, 700 * PIPELINE.length + 400);
    return () => { timers.forEach(clearTimeout); clearTimeout(finish); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="page-mobile stack-lg">
      <div className="stack">
        <h1 className="t-22">Processing Submission</h1>
        <p className="t-13 text-muted">NLP engine extracting field parameters and Primavera P6 alignment…</p>
      </div>
      <div className="panel">
        <div className="panel-body">
          {PIPELINE.map((p, i) => (
            <div key={p.name} className="row-between" style={{ padding: 'var(--s2) 0', opacity: i < step ? 1 : 0.4 }}>
              <div className="row" style={{ gap: 'var(--s2)' }}>
                <span className={`dot ${i < step ? 'dot-ok' : ''}`} style={{ background: i < step ? undefined : 'var(--border-strong)' }} />
                <div>
                  <div className="t-13" style={{ fontWeight: 600 }}>{p.name}</div>
                  <div className="t-11 text-muted">{p.desc}</div>
                </div>
              </div>
              <span className={i < step ? 'badge badge-ok' : 'badge badge-neutral'}>{i < step ? 'DONE' : 'QUEUED'}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="t-11 text-faint mono" style={{ textAlign: 'center' }}>EXTRACTION SEQUENCE · STAGE {Math.min(step + 1, 4)} OF 4</p>
    </div>
  );
}

/* ---------------- Worker: Match result ---------------- */

function MatchResultView({ match, onSubmit }: { match: MatchResult; onSubmit: () => void }) {
  const e = match.extracted;
  const headline = {
    'auto-linked': { title: 'Schedule Match Found', cls: 'callout callout-ok', label: 'AUTO-LINK', badge: 'badge badge-ok' },
    'review': { title: 'Low Confidence — Review Required', cls: 'callout callout-warn', label: 'MANAGER REVIEW', badge: 'badge badge-warn' },
    'unplanned': { title: 'No Direct WBS Match Found', cls: 'callout callout-danger', label: 'UNPLANNED', badge: 'badge badge-danger' },
  }[match.outcome];

  const cta = {
    'auto-linked': 'Confirm & Submit',
    'review': 'Submit for Manager Review',
    'unplanned': 'Submit as Unplanned Work',
  }[match.outcome];

  return (
    <div className="page-mobile stack-lg">
      <div className={headline.cls}>
        <div>
          <div className="t-13" style={{ fontWeight: 600 }}>{headline.title}</div>
          <div className="t-12 text-muted">
            {match.outcome === 'auto-linked' && 'Report matched a scheduled activity with high confidence.'}
            {match.outcome === 'review' && 'Confidence below threshold. A manager will confirm the match.'}
            {match.outcome === 'unplanned' && 'This work is not in the baseline. It will be logged as unplanned.'}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <span className="label">Extracted parameters</span>
          <span className={headline.badge}>{headline.label}</span>
        </div>
        <div className="panel-body">
          <dl style={{ margin: 0 }}>
            <div className="kv"><dt>Activity</dt><dd>{e.activity}</dd></div>
            <div className="kv"><dt>Discipline</dt><dd>{e.discipline}</dd></div>
            <div className="kv"><dt>Quantity</dt><dd className="mono">{e.quantity} {e.unit}</dd></div>
            <div className="kv"><dt>Location</dt><dd>{e.location}</dd></div>
            <div className="kv"><dt>Work window</dt><dd className="mono">{e.timeWindow}</dd></div>
          </dl>
        </div>
      </div>

      {match.suggestedActivity && (
        <div className="panel">
          <div className="panel-header">
            <span className="label">Primavera P6 link</span>
            <span className="t-11 mono text-faint">{match.suggestedActivity.wbs}</span>
          </div>
          <div className="panel-body stack-sm">
            <div className="t-14" style={{ fontWeight: 600 }}>
              {match.suggestedActivity.id} · {match.suggestedActivity.name}
            </div>
            <div className="t-12 text-muted">{match.suggestedActivity.location}</div>
            <div className="row" style={{ gap: 'var(--s2)' }}>
              <StatusBadge status={match.suggestedActivity.status} />
              <span className="t-12 text-muted mono">{formatDate(match.suggestedActivity.start)} → {formatDate(match.suggestedActivity.end)}</span>
            </div>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-body">
          <div className="row-between">
            <span className="label">Match confidence</span>
            <span className="confidence-value">{match.confidence}%</span>
          </div>
          <div className="progress" style={{ marginTop: 'var(--s2)' }}>
            <div
              className={`progress-bar ${match.confidence >= 85 ? 'ok' : match.confidence >= 60 ? 'warn' : 'danger'}`}
              style={{ width: `${match.confidence}%` }}
            />
          </div>
        </div>
      </div>

      <button className="btn btn-primary btn-lg btn-block" onClick={onSubmit}>{cta} →</button>
    </div>
  );
}

/* ---------------- Worker: Success & Detail ---------------- */

function SubmissionSuccess({ submission, go, openSubmission }: {
  submission: Submission | undefined; go: (r: Route) => void; openSubmission: (id: string) => void;
}) {
  if (!submission) return null;
  return (
    <div className="page-mobile stack-lg">
      <div className="panel panel-ink" style={{ padding: 'var(--s5) var(--s4)' }}>
        <div className="label" style={{ marginBottom: 'var(--s3)' }}>Dispatch receipt · Ledger sync</div>
        <div className="t-18" style={{ fontWeight: 600 }}>
          {submission.outcome === 'auto-linked' && 'Work log synced to Primavera P6 baseline'}
          {submission.outcome === 'review' && 'Submitted — awaiting manager review'}
          {submission.outcome === 'unplanned' && 'Logged as unplanned work'}
        </div>
        <div className="t-12 mono" style={{ opacity: 0.7, marginTop: 'var(--s2)' }}>{submission.id} · {submission.timestamp}</div>
      </div>

      <div className="panel">
        <div className="panel-body">
          <dl style={{ margin: 0 }}>
            <div className="kv"><dt>Operator</dt><dd>{WORKER.name} · {WORKER.badge}</dd></div>
            <div className="kv"><dt>Activity</dt><dd>{submission.activity}</dd></div>
            <div className="kv"><dt>Quantity</dt><dd className="mono">{submission.quantity} {submission.unit}</dd></div>
            <div className="kv"><dt>Location</dt><dd>{submission.location}</dd></div>
            <div className="kv"><dt>Confidence</dt><dd className="confidence-value">{submission.confidence}%</dd></div>
          </dl>
        </div>
      </div>

      <div className="grid grid-2">
        <button className="btn btn-secondary btn-lg" onClick={() => openSubmission(submission.id)}>View Detail</button>
        <button className="btn btn-primary btn-lg" onClick={() => go('w-home')}>New Report</button>
      </div>
    </div>
  );
}

function SubmissionDetail({ submission, goBack }: { submission: Submission | undefined; goBack: () => void }) {
  if (!submission) return null;
  const lifecycle = [
    { t: submission.timestamp, e: 'Submission received from field mobile' },
    { t: submission.timestamp, e: `NLP match — ${submission.confidence}% confidence (${submission.outcome})` },
    { t: submission.timestamp, e: submission.syncState === 'synced' ? 'Synced to Primavera P6 ledger' : 'Queued — pending synchronization' },
  ];
  return (
    <div className="page-mobile stack-lg">
      <div className="row-between">
        <button className="btn btn-ghost btn-sm" onClick={goBack}>← History</button>
        <span className={submission.syncState === 'synced' ? 'badge badge-ok' : 'badge badge-warn'}>
          {submission.syncState === 'synced' ? 'AUTO-LINKED' : 'PENDING SYNC'}
        </span>
      </div>

      <div className="stack-sm">
        <span className="t-11 mono text-faint">{submission.id} · {submission.timestamp}</span>
        <h1 className="t-22">{submission.activity}</h1>
      </div>

      <div className="panel">
        <div className="panel-header"><span className="label">Your update</span></div>
        <div className="panel-body">
          <p className="t-13">“{submission.input}”</p>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><span className="label">Field parameters</span></div>
        <div className="panel-body">
          <dl style={{ margin: 0 }}>
            <div className="kv"><dt>Discipline</dt><dd>{submission.discipline}</dd></div>
            <div className="kv"><dt>Quantity</dt><dd className="mono">{submission.quantity} {submission.unit}</dd></div>
            <div className="kv"><dt>Location</dt><dd>{submission.location}</dd></div>
            <div className="kv"><dt>Work window</dt><dd className="mono">{submission.timeWindow}</dd></div>
            <div className="kv"><dt>Schedule ref</dt><dd className="mono">{submission.activityId ?? '— none —'}</dd></div>
          </dl>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header"><span className="label">Audit lifecycle</span></div>
        <div className="panel-body stack-sm">
          {lifecycle.map((l, i) => (
            <div key={i} className="row" style={{ gap: 'var(--s2)', alignItems: 'flex-start' }}>
              <span className="dot dot-ok" style={{ marginTop: 5 }} />
              <div>
                <div className="t-13">{l.e}</div>
                <div className="t-11 text-faint mono">{l.t}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Worker: History & Profile ---------------- */

function WorkerHistory({ submissions, openSubmission }: { submissions: Submission[]; openSubmission: (id: string) => void }) {
  return (
    <div className="page-mobile stack-lg">
      <h1 className="t-22">History</h1>
      <div className="panel">
        {submissions.length === 0 && <div className="panel-body t-13 text-muted">No submissions yet.</div>}
        {submissions.map((s, i) => (
          <button key={s.id} onClick={() => openSubmission(s.id)}
            style={{ display: 'block', width: '100%', textAlign: 'left', padding: 'var(--s3) var(--s4)', borderTop: i ? '1px solid var(--border)' : 'none' }}>
            <div className="row-between">
              <span className="t-13" style={{ fontWeight: 600 }}>{s.activity}</span>
              <span className={s.outcome === 'auto-linked' ? 'badge badge-ok' : s.outcome === 'review' ? 'badge badge-warn' : 'badge badge-danger'}>
                {s.outcome.toUpperCase()}
              </span>
            </div>
            <div className="row-between" style={{ marginTop: 4 }}>
              <span className="t-11 text-faint mono">{s.id} · {s.quantity} {s.unit}</span>
              <span className="t-11 text-faint">{s.timestamp}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function WorkerProfile({ onSignOut }: { onSignOut: () => void }) {
  return (
    <div className="page-mobile stack-lg">
      <h1 className="t-22">Profile</h1>
      <div className="panel">
        <div className="panel-header">
          <span className="label">Operator identity</span>
          {WORKER.certified && <span className="badge badge-ok">CERTIFIED</span>}
        </div>
        <div className="panel-body">
          <dl style={{ margin: 0 }}>
            <div className="kv"><dt>Name</dt><dd>{WORKER.name}</dd></div>
            <div className="kv"><dt>Badge</dt><dd className="mono">{WORKER.badge}</dd></div>
            <div className="kv"><dt>Role</dt><dd>{WORKER.role}</dd></div>
            <div className="kv"><dt>Project</dt><dd>{WORKER.project}</dd></div>
            <div className="kv"><dt>Sector</dt><dd>{WORKER.sector}</dd></div>
            <div className="kv"><dt>Contractor</dt><dd>{WORKER.contractor}</dd></div>
          </dl>
        </div>
      </div>
      <button className="btn btn-secondary btn-block" onClick={onSignOut}>Sign Out</button>
    </div>
  );
}

/* ---------------- Manager chrome ---------------- */

function ManagerShell({ route, go, children }: { route: Route; go: (r: Route) => void; children: React.ReactNode }) {
  const nav: { r: Route; label: string; count?: number }[] = [
    { r: 'm-dashboard', label: 'Dashboard' },
    { r: 'm-activities', label: 'Activities' },
    { r: 'm-review', label: 'Review Queue', count: 0 },
    { r: 'm-unplanned', label: 'Unplanned' },
    { r: 'm-audit', label: 'Audit Trail' },
    { r: 'm-settings', label: 'Settings' },
  ];
  return (
    <div className="mgr">
      <aside className="mgr-side">
        <div className="brand">
          <div className="brand-mark">FT</div>
          <div>
            <div className="brand-name">FIELDTRACK</div>
            <div className="brand-sub">MANAGER CONSOLE</div>
          </div>
        </div>
        {nav.map(n => (
          <button key={n.r} className={`mgr-nav-btn ${route === n.r ? 'active' : ''}`} onClick={() => go(n.r)}>
            {n.label}
          </button>
        ))}
        <div className="mgr-side-footer">
          <div className="t-11 text-faint mono" style={{ padding: '0 var(--s3) var(--s2)' }}>● SYSTEM ONLINE</div>
        </div>
      </aside>
      <main className="mgr-main">{children}</main>
    </div>
  );
}

function ManagerHeader({ title, sub, action }: { title: string; sub: string; action?: React.ReactNode }) {
  return (
    <div className="row-between" style={{ marginBottom: 'var(--s5)' }}>
      <div>
        <div className="label" style={{ marginBottom: 2 }}>{sub}</div>
        <h1 className="t-22">{title}</h1>
      </div>
      {action}
    </div>
  );
}

/* ---------------- Manager: Dashboard ---------------- */

function ManagerDashboard({ queue, audit, go }: {
  queue: ReviewItem[]; audit: AuditEntry[]; go: (r: Route) => void;
}) {
  const counts = statusCounts();
  return (
    <>
      <ManagerHeader
        sub={`${PROJECT.code} · ${PROJECT.location}`}
        title={PROJECT.name}
        action={<button className="btn btn-secondary" onClick={() => go('m-activities')}>View Schedule</button>}
      />

      <div className="panel" style={{ marginBottom: 'var(--s5)' }}>
        <div className="grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
          {[
            { l: 'Total activities', v: counts.total },
            { l: 'Completed', v: counts.completed },
            { l: 'In progress', v: counts.inProgress },
            { l: 'Delayed', v: counts.delayed },
            { l: 'Unplanned', v: counts.unplanned },
          ].map((s, i) => (
            <div key={s.l} className="stat" style={{ borderLeft: i ? '1px solid var(--border)' : 'none' }}>
              <div className="label">{s.l}</div>
              <div className="stat-value" style={{ marginTop: 4 }}>{s.v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: '1.4fr 1fr', alignItems: 'start' }}>
        <div className="panel">
          <div className="panel-header">
            <span className="label">Activity status board</span>
            <button className="btn btn-ghost btn-sm" onClick={() => go('m-activities')}>View all</button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr><th>ID</th><th>Activity</th><th>Status</th><th>Progress</th></tr>
              </thead>
              <tbody>
                {ACTIVITIES.slice(0, 6).map(a => (
                  <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => go('m-activities')}>
                    <td className="num">{a.id}</td>
                    <td>{a.name}</td>
                    <td><StatusBadge status={a.status} /></td>
                    <td style={{ minWidth: 120 }}>
                      <div className="row" style={{ gap: 'var(--s2)' }}>
                        <div className="progress" style={{ flex: 1 }}>
                          <div className={`progress-bar ${a.status === 'Delayed' ? 'danger' : a.progress === 100 ? 'ok' : ''}`} style={{ width: `${a.progress}%` }} />
                        </div>
                        <span className="t-12 mono text-muted">{a.progress}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="stack-lg">
          <div className="panel">
            <div className="panel-header">
              <span className="label">Review queue</span>
              <span className="badge badge-warn">{queue.length} PENDING</span>
            </div>
            <div className="panel-body stack-sm">
              {queue.length === 0 && <p className="t-13 text-muted">Queue is clear.</p>}
              {queue.slice(0, 3).map(q => (
                <div key={q.id} className="stack-sm" style={{ paddingBottom: 'var(--s2)', borderBottom: '1px solid var(--border)' }}>
                  <div className="row-between">
                    <span className="t-13" style={{ fontWeight: 600 }}>{q.worker}</span>
                    <span className="t-12 mono text-muted">{q.confidence}%</span>
                  </div>
                  <div className="t-12 text-muted">{q.extracted}</div>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm btn-block" onClick={() => go('m-review')}>Open Review Queue</button>
            </div>
          </div>

          <div className="panel">
            <div className="panel-header">
              <span className="label">Latest audit entries</span>
              <button className="btn btn-ghost btn-sm" onClick={() => go('m-audit')}>View all</button>
            </div>
            <div className="panel-body stack-sm">
              {audit.slice(-3).reverse().map(a => (
                <div key={a.id} className="stack-sm">
                  <div className="row-between">
                    <span className="t-12" style={{ fontWeight: 600 }}>{a.worker}</span>
                    <span className="t-11 mono text-faint">{a.timestamp}</span>
                  </div>
                  <div className="t-12 text-muted">{a.input}</div>
                  <span className="badge badge-neutral" style={{ alignSelf: 'flex-start' }}>{a.resolution}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

/* ---------------- Manager: Activities & Detail ---------------- */

function ManagerActivities({ go, openActivity }: { go: (r: Route) => void; openActivity: (id: string) => void }) {
  const [discipline, setDiscipline] = useState('All');
  const [status, setStatus] = useState('All');
  const [query, setQuery] = useState('');
  const disciplines = ['All', ...Array.from(new Set(ACTIVITIES.map(a => a.discipline)))];
  const statuses = ['All', 'Not Started', 'In Progress', 'Completed', 'Delayed', 'Unplanned'];

  const rows = ACTIVITIES.filter(a =>
    (discipline === 'All' || a.discipline === discipline) &&
    (status === 'All' || a.status === status) &&
    (query === '' || `${a.id} ${a.name} ${a.location}`.toLowerCase().includes(query.toLowerCase()))
  );

  return (
    <>
      <ManagerHeader sub="Primavera P6 baseline" title="Activities" />
      <div className="row row-wrap" style={{ marginBottom: 'var(--s4)' }}>
        <select className="select" style={{ width: 170 }} value={discipline} onChange={e => setDiscipline(e.target.value)}>
          {disciplines.map(d => <option key={d}>{d}</option>)}
        </select>
        <select className="select" style={{ width: 150 }} value={status} onChange={e => setStatus(e.target.value)}>
          {statuses.map(s => <option key={s}>{s}</option>)}
        </select>
        <input className="input" style={{ flex: 1, minWidth: 180 }} placeholder="Search activity, ID or location…" value={query} onChange={e => setQuery(e.target.value)} />
      </div>

      <div className="panel">
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr><th>ID</th><th>Activity</th><th>Discipline</th><th>Location</th><th>Dates</th><th>Status</th><th>Progress</th></tr>
            </thead>
            <tbody>
              {rows.map(a => (
                <tr key={a.id} style={{ cursor: 'pointer' }} onClick={() => openActivity(a.id)}>
                  <td className="num">{a.id}</td>
                  <td style={{ fontWeight: 500 }}>{a.name}</td>
                  <td className="text-muted">{a.discipline}</td>
                  <td className="text-muted">{a.location}</td>
                  <td className="num text-muted">{a.start === '—' ? '—' : `${formatDate(a.start)} → ${formatDate(a.end)}`}</td>
                  <td><StatusBadge status={a.status} /></td>
                  <td style={{ minWidth: 120 }}>
                    <div className="row" style={{ gap: 'var(--s2)' }}>
                      <div className="progress" style={{ flex: 1 }}>
                        <div className={`progress-bar ${a.status === 'Delayed' ? 'danger' : a.progress === 100 ? 'ok' : ''}`} style={{ width: `${a.progress}%` }} />
                      </div>
                      <span className="t-12 mono text-muted">{a.progress}%</span>
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={7} className="text-muted" style={{ padding: 'var(--s5)', textAlign: 'center' }}>No activities match the current filters.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function ManagerActivityDetail({ activity, goBack }: { activity: Activity | undefined; goBack: () => void }) {
  if (!activity) return null;
  const related = AUDIT_TRAIL.filter(a => a.matchedActivityId === activity.id);
  return (
    <>
      <button className="btn btn-ghost btn-sm" style={{ marginBottom: 'var(--s4)' }} onClick={goBack}>← Activities</button>
      <div className="stack-lg">
        <div className="stack-sm">
          <span className="t-11 mono text-faint">{activity.wbs} · {activity.discipline}</span>
          <h1 className="t-22">{activity.name}</h1>
          <div className="row" style={{ gap: 'var(--s2)' }}>
            <StatusBadge status={activity.status} />
            <span className="t-12 text-muted mono">{activity.location}</span>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header"><span className="label">Schedule data</span></div>
          <div className="panel-body">
            <dl style={{ margin: 0 }}>
              <div className="kv"><dt>Activity ID</dt><dd className="mono">{activity.id}</dd></div>
              <div className="kv"><dt>WBS code</dt><dd className="mono">{activity.wbs}</dd></div>
              <div className="kv"><dt>Planned window</dt><dd className="mono">{activity.start === '—' ? '—' : `${formatDate(activity.start)} → ${formatDate(activity.end)}`}</dd></div>
              <div className="kv"><dt>Planned</dt><dd>{activity.planned ? 'Yes — in baseline' : 'No — unplanned registry'}</dd></div>
            </dl>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header"><span className="label">Progress</span><span className="t-13 mono">{activity.progress}%</span></div>
          <div className="panel-body">
            <div className="progress">
              <div className={`progress-bar ${activity.status === 'Delayed' ? 'danger' : activity.progress === 100 ? 'ok' : ''}`} style={{ width: `${activity.progress}%` }} />
            </div>
          </div>
        </div>

        <div className="panel">
          <div className="panel-header"><span className="label">Linked field reports</span></div>
          <div className="panel-body stack-sm">
            {related.length === 0 && <p className="t-13 text-muted">No field reports linked to this activity yet.</p>}
            {related.map(a => (
              <div key={a.id} className="stack-sm" style={{ paddingBottom: 'var(--s2)', borderBottom: '1px solid var(--border)' }}>
                <div className="row-between">
                  <span className="t-13">{a.input}</span>
                  <span className="badge badge-neutral">{a.resolution}</span>
                </div>
                <span className="t-11 text-faint mono">{a.worker} · {a.timestamp} · score {a.score}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

/* ---------------- Manager: Review Queue ---------------- */

function ManagerReview({ queue, onConfirm, onReassign, onUnplanned }: {
  queue: ReviewItem[];
  onConfirm: (id: string) => void;
  onReassign: (id: string, activityId: string) => void;
  onUnplanned: (id: string) => void;
}) {
  const [reassigning, setReassigning] = useState<string | null>(null);
  return (
    <>
      <ManagerHeader sub="Matching review" title="Review Queue" />
      {queue.length === 0 && (
        <div className="panel"><div className="panel-body t-13 text-muted">Queue is clear. All submissions have been resolved.</div></div>
      )}
      <div className="stack-lg">
        {queue.map(q => (
          <div className="panel" key={q.id}>
            <div className="panel-header">
              <div className="row" style={{ gap: 'var(--s2)' }}>
                <span className="t-13" style={{ fontWeight: 600 }}>{q.worker}</span>
                <span className="t-11 mono text-faint">{q.badge} · {q.submittedAt}</span>
              </div>
              <span className={q.confidence >= 80 ? 'badge badge-warn' : 'badge badge-danger'}>{q.confidence}% CONFIDENCE</span>
            </div>
            <div className="panel-body stack">
              <div className="stack-sm">
                <div className="label">Original field input</div>
                <p className="t-13">“{q.originalInput}”</p>
              </div>
              <div className="stack-sm">
                <div className="label">Extracted</div>
                <p className="t-13">{q.extracted}</p>
              </div>
              <div className="stack-sm">
                <div className="label">Suggested schedule match</div>
                <p className="t-13 mono">{q.suggestedActivityId ?? 'None'}</p>
              </div>

              {reassigning === q.id ? (
                <div className="row row-wrap">
                  <select className="select" style={{ width: 280 }} defaultValue=""
                    onChange={e => { if (e.target.value) { onReassign(q.id, e.target.value); setReassigning(null); } }}>
                    <option value="" disabled>Reassign to activity…</option>
                    {ACTIVITIES.filter(a => a.planned).map(a => <option key={a.id} value={a.id}>{a.id} — {a.name}</option>)}
                  </select>
                  <button className="btn btn-ghost btn-sm" onClick={() => setReassigning(null)}>Cancel</button>
                </div>
              ) : (
                <div className="row row-wrap">
                  <button className="btn btn-primary btn-sm" onClick={() => onConfirm(q.id)}>Confirm Match</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setReassigning(q.id)}>Reassign</button>
                  <button className="btn btn-danger btn-sm" onClick={() => onUnplanned(q.id)}>Mark Unplanned</button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

/* ---------------- Manager: Unplanned, Audit, Settings ---------------- */

function ManagerUnplanned({ unplanned, onAccept }: { unplanned: Activity[]; onAccept: (id: string) => void }) {
  return (
    <>
      <ManagerHeader sub="Out-of-baseline work" title="Unplanned Registry" />
      <div className="stack-lg">
        {unplanned.length === 0 && (
          <div className="panel"><div className="panel-body t-13 text-muted">No unplanned work registered.</div></div>
        )}
        {unplanned.map(u => (
          <div className="panel" key={u.id}>
            <div className="panel-header">
              <div className="row" style={{ gap: 'var(--s2)' }}>
                <span className="t-13 mono" style={{ fontWeight: 600 }}>{u.id}</span>
                <StatusBadge status={u.status} />
              </div>
              <span className="t-11 text-faint mono">{u.location}</span>
            </div>
            <div className="panel-body stack">
              <div className="t-14" style={{ fontWeight: 600 }}>{u.name}</div>
              <div className="t-12 text-muted">{u.discipline} · reported from field, no P6 baseline entry</div>
              <div className="row">
                <button className="btn btn-primary btn-sm" onClick={() => onAccept(u.id)}>Accept into Baseline</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function ManagerAudit({ audit }: { audit: AuditEntry[] }) {
  return (
    <>
      <ManagerHeader sub="Immutable lifecycle log" title="Audit Trail" />
      <div className="panel">
        <div style={{ overflowX: 'auto' }}>
          <table className="table">
            <thead>
              <tr><th>Time</th><th>Worker</th><th>Input</th><th>Matched</th><th>Score</th><th>Resolution</th></tr>
            </thead>
            <tbody>
              {[...audit].reverse().map(a => (
                <tr key={a.id}>
                  <td className="num text-muted">{a.timestamp}</td>
                  <td style={{ fontWeight: 500 }}>{a.worker}</td>
                  <td className="text-muted">{a.input}</td>
                  <td className="num">{a.matchedActivityId ?? '—'}</td>
                  <td className="num">{a.score}%</td>
                  <td>
                    <span className={a.resolution === 'Auto-linked' ? 'badge badge-ok' : a.resolution === 'Unplanned' ? 'badge badge-danger' : 'badge badge-info'}>
                      {a.resolution}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

function ManagerSettings() {
  const [reviewThreshold, setReviewThreshold] = useState(true);
  const [autoSync, setAutoSync] = useState(true);
  return (
    <>
      <ManagerHeader sub="Console configuration" title="Settings" />
      <div className="stack-lg" style={{ maxWidth: 560 }}>
        <div className="panel">
          <div className="panel-header"><span className="label">Project</span></div>
          <div className="panel-body">
            <dl style={{ margin: 0 }}>
              <div className="kv"><dt>Name</dt><dd>{PROJECT.name}</dd></div>
              <div className="kv"><dt>Code</dt><dd className="mono">{PROJECT.code}</dd></div>
              <div className="kv"><dt>Location</dt><dd>{PROJECT.location}</dd></div>
              <div className="kv"><dt>Sector</dt><dd>{PROJECT.sector}</dd></div>
            </dl>
          </div>
        </div>
        <div className="panel">
          <div className="panel-header"><span className="label">Matching policy</span></div>
          <div className="panel-body stack">
            <label className="row-between" style={{ cursor: 'pointer' }}>
              <div>
                <div className="t-13" style={{ fontWeight: 500 }}>Send low-confidence matches to review</div>
                <div className="t-12 text-muted">Submissions below 75% confidence require manager confirmation</div>
              </div>
              <input type="checkbox" checked={reviewThreshold} onChange={e => setReviewThreshold(e.target.checked)} />
            </label>
            <hr className="divider" />
            <label className="row-between" style={{ cursor: 'pointer' }}>
              <div>
                <div className="t-13" style={{ fontWeight: 500 }}>Auto-sync confirmed submissions</div>
                <div className="t-12 text-muted">Push confirmed work logs to the P6 baseline automatically</div>
              </div>
              <input type="checkbox" checked={autoSync} onChange={e => setAutoSync(e.target.checked)} />
            </label>
          </div>
        </div>
      </div>
    </>
  );
}

/* ---------------- App ---------------- */

export default function App() {
  const [role, setRole] = useState<Role | null>(null);
  const [route, setRoute] = useState<Route>('login');
  const [lang, setLang] = useState<'EN' | 'HI'>('EN');

  const [submissions, setSubmissions] = useState<Submission[]>(SUBMISSIONS);
  const [audit, setAudit] = useState<AuditEntry[]>(AUDIT_TRAIL);
  const [queue, setQueue] = useState<ReviewItem[]>(REVIEW_QUEUE);
  const [unplanned, setUnplanned] = useState<Activity[]>(ACTIVITIES.filter(a => !a.planned));

  const [pendingInput, setPendingInput] = useState('');
  const [pendingMatch, setPendingMatch] = useState<MatchResult | null>(null);
  const [lastSubmissionId, setLastSubmissionId] = useState('');
  const [selActivity, setSelActivity] = useState('');
  const [selSubmission, setSelSubmission] = useState('');

  const go = (r: Route) => setRoute(r);
  const openActivity = (id: string) => { setSelActivity(id); setRoute('m-activity'); };
  const openSubmission = (id: string) => { setSelSubmission(id); setRoute('w-submission'); };
  const addAudit = (entry: Omit<AuditEntry, 'id'>) =>
    setAudit(a => [...a, { ...entry, id: `AUD-${String(a.length + 1).padStart(3, '0')}` }]);

  /* ----- auth ----- */
  if (role === null || route === 'login') {
    return (
      <Login onLogin={r => {
        setRole(r);
        setRoute(r === 'worker' ? 'w-home' : 'm-dashboard');
      }} />
    );
  }

  /* ----- worker action handlers ----- */
  const startProcessing = (text: string) => { setPendingInput(text); setRoute('w-processing'); };
  const finishProcessing = () => { setPendingMatch(simulateMatch(pendingInput)); setRoute('w-match'); };
  const submitMatch = () => {
    if (!pendingMatch) return;
    const e = pendingMatch.extracted;
    const id = `SUB-${String(846 + submissions.length - SUBMISSIONS.length).padStart(5, '0')}`;
    const sub: Submission = {
      id,
      activityId: pendingMatch.suggestedActivity?.id ?? null,
      outcome: pendingMatch.outcome,
      input: pendingInput,
      activity: e.activity,
      discipline: e.discipline,
      quantity: e.quantity,
      unit: e.unit,
      location: e.location,
      timeWindow: e.timeWindow,
      confidence: pendingMatch.confidence,
      timestamp: 'Today · ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      syncState: pendingMatch.outcome === 'auto-linked' ? 'synced' : 'pending',
    };
    setSubmissions(s => [sub, ...s]);
    setLastSubmissionId(id);
    addAudit({
      worker: WORKER.name, timestamp: sub.timestamp, input: pendingInput,
      activity: e.activity, discipline: e.discipline, location: e.location,
      matchedActivityId: sub.activityId, score: pendingMatch.confidence,
      resolution: pendingMatch.outcome === 'auto-linked' ? 'Auto-linked'
        : pendingMatch.outcome === 'review' ? 'Pending Review' : 'Unplanned',
    });
    if (pendingMatch.outcome === 'unplanned') {
      setUnplanned(u => [...u, {
        id: `UNPL-${String(u.length + 1).padStart(3, '0')}`, wbs: '—',
        name: e.activity, discipline: e.discipline, location: e.location,
        start: '—', end: '—', status: 'Unplanned', progress: 0, planned: false,
      }]);
    }
    setPendingMatch(null);
    setRoute('w-success');
  };

  /* ----- manager review handlers ----- */
  const reviewConfirm = (id: string) => {
    const item = queue.find(q => q.id === id);
    if (!item) return;
    setQueue(q => q.filter(x => x.id !== id));
    addAudit({
      worker: item.worker, timestamp: 'Today · ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      input: item.originalInput, activity: item.extracted, discipline: 'Civil', location: '—',
      matchedActivityId: item.suggestedActivityId, score: item.confidence, resolution: 'Manual Confirmed',
    });
  };
  const reviewReassign = (id: string, activityId: string) => {
    const item = queue.find(q => q.id === id);
    if (!item) return;
    setQueue(q => q.filter(x => x.id !== id));
    addAudit({
      worker: item.worker, timestamp: 'Today · ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      input: item.originalInput, activity: `Reassigned to ${activityId}`, discipline: 'Civil', location: '—',
      matchedActivityId: activityId, score: item.confidence, resolution: 'Manual Confirmed',
    });
  };
  const reviewUnplanned = (id: string) => {
    const item = queue.find(q => q.id === id);
    if (!item) return;
    setQueue(q => q.filter(x => x.id !== id));
    setUnplanned(u => [...u, {
      id: `UNPL-${String(u.length + 1).padStart(3, '0')}`, wbs: '—',
      name: item.extracted, discipline: 'Civil', location: '—',
      start: '—', end: '—', status: 'Unplanned', progress: 0, planned: false,
    }]);
    addAudit({
      worker: item.worker, timestamp: 'Today · ' + new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      input: item.originalInput, activity: item.extracted, discipline: 'Civil', location: '—',
      matchedActivityId: null, score: item.confidence, resolution: 'Unplanned',
    });
  };
  const acceptUnplanned = (id: string) => {
    setUnplanned(list => list.map(u => u.id === id ? { ...u, status: 'Not Started' as const, planned: true } : u));
  };

  /* ----- worker render ----- */
  if (role === 'worker') {
    const last = submissions.find(s => s.id === lastSubmissionId);
    return (
      <>
        <TopBar lang={lang} setLang={setLang} />
        {route === 'w-home' && <WorkerHome submissions={submissions} go={go} openSubmission={openSubmission} />}
        {route === 'w-voice' && <VoiceInput onProcess={startProcessing} goBack={() => go('w-home')} />}
        {route === 'w-processing' && <Processing onDone={finishProcessing} />}
        {route === 'w-match' && <MatchResultView match={pendingMatch!} onSubmit={submitMatch} />}
        {route === 'w-success' && <SubmissionSuccess submission={last} go={go} openSubmission={openSubmission} />}
        {route === 'w-history' && <WorkerHistory submissions={submissions} openSubmission={openSubmission} />}
        {route === 'w-submission' && <SubmissionDetail submission={submissions.find(s => s.id === selSubmission)} goBack={() => go('w-history')} />}
        {route === 'w-profile' && <WorkerProfile onSignOut={() => { setRole(null); go('login'); }} />}
        <TabBar route={route} go={go} />
      </>
    );
  }

  /* ----- manager render ----- */
  return (
    <ManagerShell route={route} go={go}>
      {route === 'm-dashboard' && <ManagerDashboard queue={queue} audit={audit} go={go} />}
      {route === 'm-activities' && <ManagerActivities go={go} openActivity={openActivity} />}
      {route === 'm-activity' && <ManagerActivityDetail activity={ACTIVITIES.find(a => a.id === selActivity)} goBack={() => go('m-activities')} />}
      {route === 'm-review' && <ManagerReview queue={queue} onConfirm={reviewConfirm} onReassign={reviewReassign} onUnplanned={reviewUnplanned} />}
      {route === 'm-unplanned' && <ManagerUnplanned unplanned={unplanned} onAccept={acceptUnplanned} />}
      {route === 'm-audit' && <ManagerAudit audit={audit} />}
      {route === 'm-settings' && <ManagerSettings />}
      {(route === 'w-home' || route === 'login') && <ManagerDashboard queue={queue} audit={audit} go={go} />}
    </ManagerShell>
  );
}