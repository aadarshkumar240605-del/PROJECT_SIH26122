/* ============================================================
   FIELDTRACK — Mock Data Layer
   Single source of truth for the frontend prototype.
   Backend integration later replaces the fetch layer only;
   these types and shapes are the contract.
   ============================================================ */

// ---------- Types ----------

export type Discipline = 'Civil' | 'Piping' | 'Electrical' | 'Instrumentation' | 'HSE';

export type ActivityStatus = 'Not Started' | 'In Progress' | 'Completed' | 'Delayed' | 'Unplanned';

export interface Activity {
    id: string;               // e.g. "CIV-101"
    wbs: string;              // Primavera WBS code, e.g. "WS-CIV-101"
    name: string;
    discipline: Discipline;
    location: string;
    start: string;            // ISO date
    end: string;              // ISO date
    status: ActivityStatus;
    progress: number;         // 0–100
    planned: boolean;
}

export type MatchOutcome = 'auto-linked' | 'review' | 'unplanned';

export interface ReviewItem {
    id: string;
    worker: string;
    badge: string;
    confidence: number;
    originalInput: string;
    extracted: string;
    suggestedActivityId: string | null;
    submittedAt: string;
}

export interface AuditEntry {
    id: string;
    worker: string;
    timestamp: string;
    input: string;
    activity: string;
    discipline: Discipline;
    location: string;
    matchedActivityId: string | null;
    score: number;
    resolution: 'Auto-linked' | 'Manual Confirmed' | 'Unplanned' | 'Pending Review';
}

export interface Submission {
    id: string;
    activityId: string | null;
    outcome: MatchOutcome;
    input: string;
    activity: string;
    discipline: Discipline;
    quantity: number;
    unit: string;
    location: string;
    timeWindow: string;
    confidence: number;
    timestamp: string;
    syncState: 'synced' | 'pending';
}

export interface Worker {
    name: string;
    badge: string;
    role: string;
    project: string;
    projectCode: string;
    sector: string;
    unit: string;
    contractor: string;
    certified: boolean;
}

// ---------- Project & worker ----------

export const PROJECT = {
    name: 'Oil India Refinery Expansion',
    code: 'SIH26122',
    location: 'Numaligarh, Assam',
    sector: 'Sector 04 · CDU',
} as const;

export const WORKER: Worker = {
    name: 'Rahul Sharma',
    badge: 'TK-4091',
    role: 'Site Worker · Field Mobile',
    project: 'Oil India Refinery Expansion (SIH26122)',
    projectCode: 'SIH26122',
    sector: 'Sector 04 · Crude Distillation Unit (CDU) B',
    unit: 'Unit 4 · Crude Distillation Unit (CDU) B',
    contractor: 'EPC-B',
    certified: true,
};

// ---------- Activities (Primavera P6 baseline) ----------

export const ACTIVITIES: Activity[] = [
    { id: 'CIV-101', wbs: 'WS-CIV-101', name: 'Excavation for tank foundation', discipline: 'Civil', location: 'Zone A - Tank Farm', start: '2026-09-01', end: '2026-09-07', status: 'In Progress', progress: 72, planned: true },
    { id: 'CIV-102', wbs: 'WS-CIV-102', name: 'Concrete pouring for tank base', discipline: 'Civil', location: 'Zone A - Tank Farm', start: '2026-09-03', end: '2026-09-10', status: 'Completed', progress: 100, planned: true },
    { id: 'CIV-205', wbs: 'WS-CIV-205', name: 'Foundation work for control room', discipline: 'Civil', location: 'Zone D - Control Room', start: '2026-09-02', end: '2026-09-09', status: 'Delayed', progress: 45, planned: true },
    { id: 'PIP-110', wbs: 'WS-PIP-110', name: 'Pipe welding near tank 3', discipline: 'Piping', location: 'Zone A - Tank Farm', start: '2026-09-04', end: '2026-09-11', status: 'Completed', progress: 100, planned: true },
    { id: 'PIP-210', wbs: 'WS-PIP-210', name: 'Pipeline laying in corridor', discipline: 'Piping', location: 'Zone B - Pipeline Corridor', start: '2026-09-03', end: '2026-09-12', status: 'In Progress', progress: 68, planned: true },
    { id: 'ELE-321', wbs: 'WS-ELE-321', name: 'Cable tray installation', discipline: 'Electrical', location: 'Zone C - Substation', start: '2026-09-01', end: '2026-09-07', status: 'Not Started', progress: 12, planned: true },
    { id: 'ELE-420', wbs: 'WS-ELE-420', name: 'HT cable pulling', discipline: 'Electrical', location: 'Zone C - Substation', start: '2026-09-03', end: '2026-09-10', status: 'Delayed', progress: 52, planned: true },
    { id: 'INS-510', wbs: 'WS-INS-510', name: 'Instrument cable routing', discipline: 'Instrumentation', location: 'Zone D - Control Room', start: '2026-09-06', end: '2026-09-15', status: 'Not Started', progress: 0, planned: true },
    { id: 'HSE-010', wbs: 'WS-HSE-010', name: 'Safety barricade setup', discipline: 'HSE', location: 'All zones', start: '2026-09-01', end: '2026-09-10', status: 'Completed', progress: 100, planned: true },
    { id: 'UNPL-001', wbs: '—', name: 'Additional concrete patch work', discipline: 'Civil', location: 'Zone B', start: '—', end: '—', status: 'Unplanned', progress: 0, planned: false },
];

// ---------- Manager review queue ----------

export const REVIEW_QUEUE: ReviewItem[] = [
    {
        id: 'RQ-001',
        worker: 'A. Kumar',
        badge: 'TK-5112',
        confidence: 84,
        originalInput: 'Completed pipe welding near tank 3 after rain delay at Zone A',
        extracted: 'Pipe welding near tank 3 completed',
        suggestedActivityId: 'PIP-110',
        submittedAt: '2026-09-05 09:12',
    },
    {
        id: 'RQ-002',
        worker: 'S. Patel',
        badge: 'TK-4780',
        confidence: 71,
        originalInput: 'Cable tray installed in substation but a few supports remain pending',
        extracted: 'Cable tray installation at substation',
        suggestedActivityId: 'ELE-321',
        submittedAt: '2026-09-05 10:40',
    },
    {
        id: 'RQ-003',
        worker: 'R. Singh',
        badge: 'TK-3925',
        confidence: 63,
        originalInput: 'Temporary barricading added near pipeline crossing for safety',
        extracted: 'Temporary safety barricade near pipeline crossing',
        suggestedActivityId: 'HSE-010',
        submittedAt: '2026-09-05 12:05',
    },
];

// ---------- Audit trail ----------

export const AUDIT_TRAIL: AuditEntry[] = [
    {
        id: 'AUD-001', worker: 'A. Kumar', timestamp: '2026-09-05 08:20',
        input: 'Pipe welding near tank 3 done today',
        activity: 'Pipe welding near tank 3', discipline: 'Piping', location: 'Zone A',
        matchedActivityId: 'PIP-110', score: 87, resolution: 'Auto-linked',
    },
    {
        id: 'AUD-002', worker: 'S. Patel', timestamp: '2026-09-05 10:40',
        input: 'Cable tray installation completed in substation',
        activity: 'Cable tray installation', discipline: 'Electrical', location: 'Zone C',
        matchedActivityId: 'ELE-321', score: 79, resolution: 'Manual Confirmed',
    },
    {
        id: 'AUD-003', worker: 'R. Singh', timestamp: '2026-09-05 12:05',
        input: 'New concrete patch work on access road',
        activity: 'Concrete patch work', discipline: 'Civil', location: 'Zone B',
        matchedActivityId: 'UNPL-001', score: 44, resolution: 'Unplanned',
    },
];

// ---------- Worker submission history ----------

export const SUBMISSIONS: Submission[] = [
    {
        id: 'SUB-00845', activityId: 'EL-3042', outcome: 'auto-linked',
        input: 'Laid 40m of conduit on Level 3 east wing from 2 to 3 PM.',
        activity: 'Electrical Conduit Installation',
        discipline: 'Electrical',
        quantity: 40, unit: 'METERS',
        location: 'Level 3 · East Wing',
        timeWindow: '14:00 – 15:00 · Today',
        confidence: 94, timestamp: 'Today · 14:12', syncState: 'synced',
    },
    {
        id: 'SUB-00844', activityId: 'WS-CIV-101', outcome: 'auto-linked',
        input: 'Excavation done near tank foundation, roughly 30 cubic meters.',
        activity: 'Excavation for tank foundation',
        discipline: 'Civil',
        quantity: 30, unit: 'CUBIC METERS',
        location: 'Zone A · Tank Farm',
        timeWindow: '09:00 – 13:00 · Today',
        confidence: 88, timestamp: 'Today · 13:04', syncState: 'synced',
    },
    {
        id: 'SUB-00843', activityId: null, outcome: 'review',
        input: 'Fixed the support brackets near the pump area before lunch.',
        activity: 'Unidentified support work',
        discipline: 'Piping',
        quantity: 6, unit: 'BRACKETS',
        location: 'Zone B · Pump Area',
        timeWindow: '11:00 – 12:30 · Today',
        confidence: 58, timestamp: 'Today · 12:41', syncState: 'pending',
    },
];

// ---------- Voice-flow simulation ----------
// Deterministic prototype "NLP" — the three outcomes the UI must handle.

export interface MatchResult {
    outcome: MatchOutcome;
    confidence: number;
    extracted: {
        activity: string;
        discipline: Discipline;
        quantity: number;
        unit: string;
        location: string;
        timeWindow: string;
    };
    suggestedActivity: Activity | null;
}

const SAMPLE_RESULTS: Record<MatchOutcome, MatchResult> = {
    'auto-linked': {
        outcome: 'auto-linked',
        confidence: 94,
        extracted: {
            activity: 'Electrical Conduit Installation',
            discipline: 'Electrical',
            quantity: 40,
            unit: 'METERS',
            location: 'Level 3 · East Wing',
            timeWindow: '14:00 – 15:00',
        },
        suggestedActivity: ACTIVITIES.find(a => a.id === 'ELE-321') ?? null,
    },
    review: {
        outcome: 'review',
        confidence: 62,
        extracted: {
            activity: 'Support bracket installation',
            discipline: 'Piping',
            quantity: 6,
            unit: 'BRACKETS',
            location: 'Zone B · Pump Area',
            timeWindow: '11:00 – 12:30',
        },
        suggestedActivity: ACTIVITIES.find(a => a.id === 'PIP-210') ?? null,
    },
    unplanned: {
        outcome: 'unplanned',
        confidence: 41,
        extracted: {
            activity: 'Access road patch work',
            discipline: 'Civil',
            quantity: 12,
            unit: 'SQUARE METERS',
            location: 'Zone B · Access Road',
            timeWindow: '15:00 – 16:00',
        },
        suggestedActivity: null,
    },
};

/** Prototype matching engine. Cycles through the three outcomes
 *  so every UI path is demonstrable during a pitch. */
let matchCounter = 0;
export function simulateMatch(_input: string): MatchResult {
    const sequence: MatchOutcome[] = ['auto-linked', 'review', 'unplanned'];
    const outcome = sequence[matchCounter++ % sequence.length];
    return SAMPLE_RESULTS[outcome];
}

// ---------- Helpers ----------

export function getActivity(id: string): Activity | undefined {
    return ACTIVITIES.find(a => a.id === id);
}

export function statusCounts() {
    return {
        total: ACTIVITIES.length,
        completed: ACTIVITIES.filter(a => a.status === 'Completed').length,
        inProgress: ACTIVITIES.filter(a => a.status === 'In Progress').length,
        delayed: ACTIVITIES.filter(a => a.status === 'Delayed').length,
        unplanned: ACTIVITIES.filter(a => a.status === 'Unplanned').length,
    };
}

export function formatDate(iso: string): string {
    if (iso === '—') return '—';
    const d = new Date(iso + 'T00:00:00');
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}