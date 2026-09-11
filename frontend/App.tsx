import { useEffect, useState } from 'react'
import { Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native'
import { StatusBar } from 'expo-status-bar'
import { api, Dashboard, MatchResult, ReviewItem, ScheduleItem } from './src/api'
import './global.css'

type Role = 'manager' | 'worker'
type LoadState = 'loading' | 'ready' | 'error'

const sampleReport = 'Completed pipe welding near tank 3 in Zone A today.'

export default function App() {
  const [role, setRole] = useState<Role | null>(null)

  if (!role) return <RolePicker onSelect={setRole} />
  if (role === 'worker') return <WorkerPlaceholder onBack={() => setRole(null)} />
  return <ManagerHome onBack={() => setRole(null)} />
}

function RolePicker({ onSelect }: { onSelect: (role: Role) => void }) {
  return (
    <View className="flex-1 bg-[#edf3f1] px-6 pt-20">
      <StatusBar style="dark" />
      <View className="mb-16 flex-row items-center gap-3">
        <View className="h-12 w-12 items-center justify-center rounded-2xl bg-[#0e6871]"><Text className="text-base font-extrabold tracking-widest text-white">SIH</Text></View>
        <View><Text className="font-mono text-[10px] uppercase tracking-[2px] text-[#738087]">Field intelligence</Text><Text className="mt-1 text-lg font-extrabold text-[#18212b]">Project pulse</Text></View>
      </View>
      <Text className="font-mono text-[10px] uppercase tracking-[2px] text-[#738087]">Welcome back</Text>
      <Text className="mt-3 max-w-[340px] text-[38px] font-extrabold leading-[43px] tracking-[-1.5px] text-[#18212b]">Choose your workspace.</Text>
      <Text className="mt-4 max-w-[330px] text-[15px] leading-6 text-[#68777a]">One project view for the people planning the work and the people doing it.</Text>
      <View className="mt-12 gap-4">
        <RoleCard title="Manager side" subtitle="Monitor schedule, reports, and exceptions" icon="↗" accent="bg-[#0e6871]" onPress={() => onSelect('manager')} />
        <RoleCard title="Worker side" subtitle="Field updates and daily activity capture" icon="＋" accent="bg-[#829896]" onPress={() => onSelect('worker')} />
      </View>
      <Text className="mt-auto pb-8 text-center font-mono text-[10px] uppercase tracking-[1.5px] text-[#9aa7a5]">Schedule-linked operations · v0.1</Text>
    </View>
  )
}

function RoleCard({ title, subtitle, icon, accent, onPress }: { title: string; subtitle: string; icon: string; accent: string; onPress: () => void }) {
  return <Pressable onPress={onPress} className="flex-row items-center rounded-2xl border border-[#d5e0dd] bg-[#fbfcfb] p-4 active:opacity-80"><View className={`mr-4 h-12 w-12 items-center justify-center rounded-xl ${accent}`}><Text className="text-2xl text-white">{icon}</Text></View><View className="flex-1"><Text className="text-[17px] font-bold text-[#26363a]">{title}</Text><Text className="mt-1 text-[12px] leading-[18px] text-[#788685]">{subtitle}</Text></View><Text className="text-xl text-[#8ea09d">›</Text></Pressable>
}

function ManagerHome({ onBack }: { onBack: () => void }) {
  const [loadState, setLoadState] = useState<LoadState>('loading')
  const [error, setError] = useState('')
  const [dashboard, setDashboard] = useState<Dashboard | null>(null)
  const [schedule, setSchedule] = useState<ScheduleItem[]>([])
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([])
  const [reportText, setReportText] = useState(sampleReport)
  const [result, setResult] = useState<MatchResult | null>(null)
  const [issues, setIssues] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [filter, setFilter] = useState<'all' | ScheduleItem['status']>('all')

  async function refresh() {
    setLoadState('loading')
    setError('')
    try {
      const [health, nextDashboard, nextSchedule, nextReview] = await Promise.all([api.ping(), api.dashboard(), api.schedule(), api.reviewQueue()])
      if (health.status !== 'ok') throw new Error('Backend health check failed')
      setDashboard(nextDashboard)
      setSchedule(nextSchedule)
      setReviewQueue(nextReview)
      setLoadState('ready')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect to the backend')
      setLoadState('error')
    }
  }

  useEffect(() => { void refresh() }, [])

  async function submitReport() {
    if (!reportText.trim()) return
    setIsSubmitting(true); setResult(null); setIssues([])
    try {
      const response = await api.submit(reportText.trim())
      setResult(response.results[0] ?? null)
      setIssues(response.issues)
      await refresh()
    } catch (cause) { setIssues([cause instanceof Error ? cause.message : 'Submission failed']) } finally { setIsSubmitting(false) }
  }

  const taskCounts = dashboard?.tasks ?? {}
  const reportCounts = dashboard?.reports ?? {}
  const completionPercent = schedule.length ? Math.round(((taskCounts.done ?? 0) / schedule.length) * 100) : 0
  const visibleSchedule = filter === 'all' ? schedule : schedule.filter((item) => item.status === filter)

  return <View className="flex-1 bg-[#edf3f1]"><StatusBar style="dark" /><ScrollView className="flex-1" contentContainerStyle={{ paddingBottom: 42 }} refreshControl={<RefreshControl refreshing={loadState === 'loading'} onRefresh={() => void refresh()} tintColor="#0e6871" />}>
    <View className="px-5 pt-14">
      <View className="mb-7 flex-row items-center justify-between"><View className="flex-row items-center gap-3"><View className="h-10 w-10 items-center justify-center rounded-xl bg-[#0e6871]"><Text className="text-xs font-extrabold tracking-widest text-white">SIH</Text></View><View><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#738087]">Manager workspace</Text><Text className="mt-1 text-base font-extrabold text-[#18212b]">Project pulse</Text></View></View><Pressable onPress={onBack} className="rounded-full border border-[#ccd9d6] px-3 py-2"><Text className="text-[11px] font-bold text-[#52706d]">Switch role</Text></Pressable></View>
      <View className="mb-6 flex-row items-end justify-between"><View className="flex-1 pr-4"><Text className="font-mono text-[10px] uppercase tracking-[2px] text-[#738087]">Schedule-linked operations</Text><Text className="mt-2 text-[31px] font-extrabold leading-9 tracking-[-1px] text-[#18212b]">Know what needs attention.</Text></View><View className="mb-1 flex-row items-center gap-1.5"><View className={`h-2 w-2 rounded-full ${loadState === 'ready' ? 'bg-[#35a87b]' : loadState === 'error' ? 'bg-[#c76c76]' : 'bg-[#e5a83c]'}`} /><Text className="text-[10px] text-[#71807f]">{loadState === 'ready' ? 'Live' : loadState === 'error' ? 'Offline' : 'Syncing'}</Text></View></View>
      {error ? <View className="mb-5 rounded-xl border-l-4 border-[#c76c76] bg-[#fff0f1] p-3"><Text className="text-xs leading-5 text-[#864b53]">{error}</Text><Text className="mt-1 font-mono text-[10px] text-[#864b53]">Start the API on port 8001.</Text></View> : null}
      <View className="mb-5 rounded-2xl border border-[#c8dcd7] bg-[#e8f3f0] p-4"><View className="flex-row items-center justify-between"><View><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#66817c]">Today at a glance</Text><Text className="mt-1 text-sm font-bold text-[#194d50]">Baseline is moving</Text></View><Text className="text-2xl font-extrabold text-[#227b63]">{completionPercent}%</Text></View><View className="mt-3 h-2 overflow-hidden rounded-full bg-[#c8dcd7]"><View className="h-full rounded-full bg-[#2c9a79]" style={{ width: `${completionPercent}%` }} /></View><View className="mt-3 flex-row gap-5"><PulseStat value={taskCounts.done ?? 0} label="complete" /><PulseStat value={taskCounts.in_progress ?? 0} label="active" /><PulseStat value={taskCounts.flagged ?? 0} label="flagged" warning /></View></View>
      <View className="mb-5 flex-row gap-2.5"><Metric label="Tasks" value={schedule.length} tone="border-[#77aeb1]" /><Metric label="Review" value={reportCounts.needs_review ?? 0} tone="border-[#cf7880]" /><Metric label="Auto-applied" value={reportCounts.auto_applied ?? 0} tone="border-[#47a478]" /></View>
      <View className="mb-5 rounded-2xl border border-[#d8e1df] bg-[#fbfcfb] p-4"><View className="mb-4 flex-row items-center justify-between"><View><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#738087]">Capture</Text><Text className="mt-1 text-lg font-extrabold tracking-[-.5px] text-[#26363a]">Submit field report</Text></View><Text className="font-mono text-[10px] text-[#849092]">01 / 02</Text></View><TextInput value={reportText} onChangeText={setReportText} multiline numberOfLines={4} placeholder="Describe the work completed on site..." placeholderTextColor="#9aa7a5" className="min-h-[105px] rounded-xl border border-[#cedbd8] bg-[#f5f9f8] p-3 text-[13px] leading-5 text-[#243338]" /><Pressable onPress={() => void submitReport()} disabled={isSubmitting || loadState !== 'ready'} className={`mt-3 items-center rounded-xl py-3 ${isSubmitting || loadState !== 'ready' ? 'bg-[#9ab7b4]' : 'bg-[#0e6871]'}`}><Text className="text-xs font-bold text-white">{isSubmitting ? 'Processing...' : 'Process report  →'}</Text></Pressable>{result ? <MatchCard result={result} /> : null}{issues.length ? <Text className="mt-3 text-[11px] leading-4 text-[#9a6b2d]">{issues[0]}</Text> : null}</View>
      <ReviewQueue items={reviewQueue} />
      <View className="mb-3 mt-6 flex-row items-end justify-between"><View><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#738087]">Baseline view</Text><Text className="mt-1 text-lg font-extrabold tracking-[-.5px] text-[#26363a]">Schedule activity</Text></View><Text className="text-[11px] text-[#849092]">{visibleSchedule.length} shown</Text></View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} className="mb-3"><View className="flex-row gap-2">{(['all', 'pending', 'in_progress', 'flagged', 'done'] as const).map((value) => <Pressable key={value} onPress={() => setFilter(value)} className={`rounded-full border px-3 py-2 ${filter === value ? 'border-[#bbd5d1] bg-[#e8f3f0]' : 'border-[#d5e0dd] bg-[#fbfcfb]'}`}><Text className={`text-[10px] capitalize ${filter === value ? 'font-bold text-[#0e6871]' : 'text-[#849092]'}`}>{value.replace('_', ' ')}</Text></Pressable>)}</View></ScrollView>
      <View className="overflow-hidden rounded-2xl border border-[#d8e1df] bg-[#fbfcfb]">{visibleSchedule.slice(0, 12).map((item) => <ScheduleRow key={item.id} item={item} />)}{visibleSchedule.length === 0 ? <Text className="p-6 text-center text-xs text-[#849092]">No rows match this filter.</Text> : null}</View>
    </View>
  </ScrollView></View>
}

function Metric({ label, value, tone }: { label: string; value: number; tone: string }) { return <View className={`flex-1 rounded-xl border-t-2 bg-[#fbfcfb] p-3 ${tone}`}><Text className="text-[10px] text-[#748083]">{label}</Text><Text className="mt-2 text-2xl font-extrabold tracking-[-1px] text-[#26363a]">{value}</Text></View> }
function PulseStat({ value, label, warning }: { value: number; label: string; warning?: boolean }) { return <View><Text className={`text-lg font-extrabold ${warning ? 'text-[#ad6e27]' : 'text-[#227b63]'}`}>{value}</Text><Text className="font-mono text-[9px] uppercase tracking-wider text-[#66817c]">{label}</Text></View> }
function MatchCard({ result }: { result: MatchResult }) { return <View className="mt-4 flex-row items-center justify-between rounded-xl border-l-4 border-[#35a87b] bg-[#eef8f3] p-3"><View className="flex-1 pr-3"><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#4d7667]">Match result</Text><Text className="mt-1 text-xs font-bold text-[#26363a]">{result.matched_activity_name}</Text><Text className="mt-1 font-mono text-[9px] text-[#5f7c73]">{result.matched_activity_id}</Text></View><Text className="text-xl font-extrabold text-[#188262]">{Math.round(result.confidence_score)}%</Text></View> }
function ReviewQueue({ items }: { items: ReviewItem[] }) { return <View className="rounded-2xl border border-[#d8e1df] bg-[#fbfcfb] p-4"><View className="mb-3 flex-row items-center justify-between"><View><Text className="font-mono text-[9px] uppercase tracking-[1.5px] text-[#738087]">Human in the loop</Text><Text className="mt-1 text-lg font-extrabold tracking-[-.5px] text-[#26363a]">Review queue</Text></View><View className="h-7 w-7 items-center justify-center rounded-full bg-[#e3f0ee]"><Text className="font-mono text-[10px] font-bold text-[#0e6871]">{items.length}</Text></View></View>{items.length ? items.slice(0, 3).map((item) => <View key={item.id} className="border-t border-[#e2e9e7] py-3"><Text className="text-xs font-bold text-[#26363a]">{item.extracted_task ?? item.raw_text}</Text><Text className="mt-1 text-[10px] text-[#889394]">{item.candidate_location ?? 'Location pending'} · report #{item.id}</Text></View>) : <Text className="py-4 text-center text-xs text-[#849092]">No reports waiting for review.</Text>}</View> }
function ScheduleRow({ item }: { item: ScheduleItem }) { const color = item.status === 'done' ? 'bg-[#dff3e9] text-[#277b61]' : item.status === 'in_progress' ? 'bg-[#fff0ce] text-[#966b1b]' : item.status === 'flagged' ? 'bg-[#fae5e7] text-[#a15b64]' : 'bg-[#e8efed] text-[#58716e]'; return <View className="border-b border-[#edf1ef] p-3"><View className="flex-row items-start justify-between gap-2"><View className="flex-1 pr-2"><Text className="text-xs font-bold text-[#26363a]">{item.task_name}</Text><Text className="mt-1 text-[10px] text-[#8b9796]">{item.discipline ?? 'General'} · {item.location ?? 'Location pending'}</Text></View><Text className={`rounded px-2 py-1 text-[9px] font-bold uppercase ${color}`}>{item.status.replace('_', ' ')}</Text></View><Text className="mt-2 font-mono text-[9px] text-[#9ca7a7]">{item.planned_start}  →  {item.planned_end}</Text></View> }
function WorkerPlaceholder({ onBack }: { onBack: () => void }) { return <View className="flex-1 items-center justify-center bg-[#edf3f1] px-7"><StatusBar style="dark" /><View className="mb-5 h-16 w-16 items-center justify-center rounded-2xl bg-[#829896]"><Text className="text-3xl text-white">＋</Text></View><Text className="text-center text-2xl font-extrabold tracking-[-.5px] text-[#18212b]">Worker workspace</Text><Text className="mt-3 text-center text-sm leading-6 text-[#68777a]">Daily updates, voice notes, and field activity capture are coming next.</Text><Pressable onPress={onBack} className="mt-8 rounded-xl bg-[#0e6871] px-6 py-3"><Text className="text-xs font-bold text-white">Back to role selection</Text></Pressable></View> }
