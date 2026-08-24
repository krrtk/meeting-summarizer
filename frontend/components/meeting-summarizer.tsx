'use client'

import { useRef, useState, useEffect } from 'react'
import { Activity, AlertCircle, ArrowLeft, CalendarDays, Check, ChevronDown, Clock3, FileAudio, FileText, FolderOpen, Headphones, ListChecks, Loader2, MessageSquare, MoreHorizontal, Play, Sparkles, Target, UploadCloud, Users, X } from 'lucide-react'
import { formatFileSize, formatMeetingDate, formatTimestamp, getHistoryPreview, getPriorityClass, validateAudio, uploadMeeting, getMeeting, getMeetings, type MeetingDetail, type Meeting } from '@/lib/meeting-api'

const stages = ['Uploading', 'Transcribing', 'Generating Summary', 'Extracting Action Items', 'Complete']
type View = 'dashboard' | 'results'

function StatusPill({ status }: { status: 'completed' | 'processing' | 'failed' }) {
  const styles = { completed: 'bg-emerald-50 text-emerald-700', processing: 'bg-amber-50 text-amber-700', failed: 'bg-rose-50 text-rose-700' }
  const labels = { completed: 'Ready', processing: 'Processing', failed: 'Failed' }
  return <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${styles[status]}`}><span className={`h-1.5 w-1.5 rounded-full ${status === 'completed' ? 'bg-emerald-500' : status === 'processing' ? 'bg-amber-500' : 'bg-rose-500'}`} />{labels[status]}</span>
}

function UploadPanel({ onComplete }: { onComplete: (detail: MeetingDetail) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  type ProcessingState = 'idle' | 'uploading' | 'transcribing' | 'summarizing' | 'completed' | 'failed'
  const [processingState, setProcessingState] = useState<ProcessingState>('idle')

  const chooseFile = (nextFile?: File) => {
    if (!nextFile) return
    const validation = validateAudio(nextFile)
    setError(validation ?? '')
    setFile(validation ? null : nextFile)
  }

  const upload = async () => {
    if (!file) return
    setProcessingState('uploading')
    setError('')
    
    try {
      // 1. Upload audio file and receive the database-generated meeting ID
      const { meeting_id } = await uploadMeeting(file)
      
      // 2. Transition visual state to transcribing
      setProcessingState('transcribing')
      
      // 3. Poll for the meeting status until complete or failed
      const poll = async () => {
        try {
          const detail = await getMeeting(meeting_id)
          const status = detail.meeting.status
          
          if (status === 'completed') {
            setProcessingState('completed')
            onComplete(detail)
          } else if (status === 'failed') {
            setProcessingState('failed')
            setError(detail.meeting.error_message || 'Processing failed. Please try a different recording.')
          } else {
            // Update visual progress state dynamically based on processing status
            if (detail.transcript && detail.transcript.text) {
              setProcessingState('summarizing')
            }
            // Poll again in 2 seconds
            setTimeout(poll, 2000)
          }
        } catch (err: any) {
          setProcessingState('failed')
          setError(err.message || 'Error occurred while verifying processing status.')
        }
      }
      
      setTimeout(poll, 2000)
    } catch (err: any) {
      setProcessingState('failed')
      setError(err.message || 'Failed to upload file to backend.')
    }
  }

  return (
    <section className="rounded-2xl border-2 border-primary/20 bg-card p-6 shadow-sm sm:p-10" aria-labelledby="upload-heading">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-primary">New meeting</p>
          <h2 id="upload-heading" className="font-serif text-2xl font-semibold tracking-tight text-card-foreground">Turn conversation into clarity.</h2>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">Upload a recording and get a structured summary, decisions, and follow-ups.</p>
        </div>
        <div className="hidden rounded-xl bg-primary/10 p-3 text-primary sm:block">
          <Headphones size={22} />
        </div>
      </div>
      
      {processingState !== 'idle' ? (
        <div className="rounded-xl border border-primary/20 bg-primary/[0.04] p-5">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="font-medium text-card-foreground">Processing your meeting</p>
              <p className="mt-1 text-sm text-muted-foreground">Generating transcript and summaries. Please don&apos;t close this page.</p>
            </div>
            {processingState === 'failed' ? (
              <AlertCircle className="text-destructive" size={20} />
            ) : processingState === 'completed' ? (
              <Check className="text-primary" size={20} />
            ) : (
              <Loader2 className="animate-spin text-primary" size={20} />
            )}
          </div>
          <div className="space-y-4" aria-live="polite">
            {stages.map((item, index) => {
              const activeIndex =
                processingState === 'uploading'
                  ? 0
                  : processingState === 'transcribing'
                  ? 1
                  : processingState === 'summarizing'
                  ? 2
                  : 4
              const done = processingState === 'completed' || index < activeIndex
              const active = processingState !== 'completed' && index === activeIndex
              
              return (
                <div key={item} className="flex items-center gap-3 text-sm">
                  <span className={`flex h-6 w-6 items-center justify-center rounded-full border text-xs font-semibold ${done ? 'border-primary bg-primary text-primary-foreground' : active ? 'border-primary text-primary' : 'border-border text-muted-foreground'}`}>
                    {done ? <Check size={14} /> : index + 1}
                  </span>
                  <span className={done || active ? 'font-medium text-card-foreground' : 'text-muted-foreground'}>
                    {item}
                  </span>
                  {active && <span className="text-xs text-primary">In progress</span>}
                </div>
              )
            })}
          </div>
          {processingState === 'failed' && error && (
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
              <AlertCircle size={17} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>
      ) : (
        <>
          <button
            type="button"
            className={`group flex w-full flex-col items-center justify-center rounded-xl border border-dashed p-8 text-center transition-colors ${dragging ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/40'}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0]) }}
          >
            <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted text-primary">
              <UploadCloud size={22} />
            </span>
            <span className="font-medium text-card-foreground">Drop an audio file here</span>
            <span className="mt-1 text-sm text-muted-foreground">or <span className="font-medium text-primary">browse from your computer</span></span>
            <span className="mt-4 text-xs text-muted-foreground">MP3, WAV, or M4A · up to 100 MB</span>
            <input
              ref={inputRef}
              type="file"
              accept=".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/x-m4a,audio/mp4,audio/ogg,audio/webm"
              className="sr-only"
              onChange={(event) => chooseFile(event.target.files?.[0])}
            />
          </button>
          
          {error && (
            <div role="alert" className="mt-4 flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">
              <AlertCircle size={17} className="mt-0.5 shrink-0" />
              {error}
            </div>
          )}
          
          {file && (
            <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-border bg-muted/35 p-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="rounded-lg bg-primary/10 p-2 text-primary">
                  <FileAudio size={18} />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-card-foreground">{file.name}</p>
                  <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <button
                type="button"
                aria-label="Remove selected file"
                className="rounded-md p-1.5 text-muted-foreground hover:bg-background hover:text-foreground"
                onClick={() => setFile(null)}
              >
                <X size={16} />
              </button>
            </div>
          )}
          
          <button
            type="button"
            disabled={!file}
            onClick={upload}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-45"
          >
            <Sparkles size={16} />
            Upload and summarize
          </button>
        </>
      )}
    </section>
  )
}

function History({ meetings, loading, error, onSelect }: { meetings: Meeting[]; loading: boolean; error: string; onSelect: (id: string) => void }) {
  if (loading) {
    return (
      <section className="mt-10" aria-labelledby="history-heading">
        <div className="mb-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Your workspace</p>
          <h2 id="history-heading" className="font-serif text-2xl font-semibold tracking-tight">Recent meetings</h2>
        </div>
        <div className="flex items-center gap-2.5 rounded-2xl border border-border bg-card p-10 text-sm text-muted-foreground justify-center">
          <Loader2 className="animate-spin text-primary" size={20} />
          <span>Loading workspace history...</span>
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="mt-10" aria-labelledby="history-heading">
        <div className="mb-4">
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Your workspace</p>
          <h2 id="history-heading" className="font-serif text-2xl font-semibold tracking-tight">Recent meetings</h2>
        </div>
        <div className="flex items-center gap-2 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
          <AlertCircle size={18} className="shrink-0" />
          <span>{error}</span>
        </div>
      </section>
    )
  }

  return (
    <section className="mt-10" aria-labelledby="history-heading">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">Your workspace</p>
          <h2 id="history-heading" className="font-serif text-2xl font-semibold tracking-tight">Recent meetings</h2>
        </div>
      </div>
      
      {meetings.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-border bg-card p-10 text-center text-sm text-muted-foreground">
          No meetings processed yet. Upload your first meeting recording above.
        </div>
      ) : (
        <div className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {meetings.map((meeting) => (
            <button
              type="button"
              key={meeting.id}
              onClick={() => onSelect(meeting.id)}
              className="flex w-full items-center gap-4 p-4 text-left transition-colors hover:bg-muted/35 sm:p-5"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted text-primary">
                <FileAudio size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="truncate text-sm font-semibold text-card-foreground">{meeting.filename}</h3>
                  <StatusPill status={meeting.status} />
                </div>
                <p className="mt-1 truncate text-sm text-muted-foreground">
                  {getHistoryPreview(meeting.status, meeting.error_message)}
                </p>
                <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="inline-flex items-center gap-1">
                    <CalendarDays size={13} />
                    {formatMeetingDate(meeting.created_at)}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Clock3 size={13} />
                    —
                  </span>
                </div>
              </div>
              <MoreHorizontal size={18} className="shrink-0 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

function SectionCard({ icon: Icon, title, children, className = '' }: { icon: typeof ListChecks; title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-border bg-card p-5 ${className}`}>
      <div className="mb-4 flex items-center gap-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted text-primary">
          <Icon size={16} />
        </span>
        <h2 className="font-serif text-xl font-semibold tracking-tight">{title}</h2>
      </div>
      {children}
    </section>
  )
}

function Results({ detail, onBack }: { detail: MeetingDetail; onBack: () => void }) {
  const [transcriptOpen, setTranscriptOpen] = useState(true)
  return (
    <div className="results-page mx-auto max-w-6xl px-4 py-7 sm:px-6 lg:px-8">
      <button type="button" onClick={onBack} className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground">
        <ArrowLeft size={16} />
        Back to dashboard
      </button>
      
      <header className="mb-8 flex flex-col justify-between gap-4 border-b border-border pb-7 sm:flex-row sm:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-primary">Meeting results</p>
          <h1 className="max-w-3xl font-serif text-3xl font-semibold tracking-tight text-balance sm:text-4xl">{detail.result.meeting_title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <StatusPill status={detail.meeting.status} />
            <span>{formatMeetingDate(detail.meeting.created_at)}</span>
            <span>—</span>
          </div>
        </div>
        <button type="button" className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-semibold text-card-foreground hover:bg-muted">
          <FolderOpen size={16} />
          Export results
        </button>
      </header>
      
      <div className="grid gap-5 lg:grid-cols-[1.3fr_0.7fr]">
        <SectionCard icon={Sparkles} title="Summary" className="border-primary/25 bg-primary/[0.025] p-6 sm:p-8 lg:col-span-2">
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-primary">At a glance</p>
          <p className="text-[15px] leading-7 text-muted-foreground">{detail.result.summary}</p>
        </SectionCard>
        
        <SectionCard icon={Target} title="Key decisions">
          <ul className="space-y-3">
            {detail.result.key_decisions.length === 0 ? (
              <li className="text-sm text-muted-foreground italic">No key decisions recorded.</li>
            ) : (
              detail.result.key_decisions.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-muted-foreground">
                  <Check size={16} className="mt-1 shrink-0 text-primary" />
                  {item}
                </li>
              ))
            )}
          </ul>
        </SectionCard>
        
        <SectionCard icon={ListChecks} title="Action items">
          <div className="space-y-3">
            {detail.result.action_items.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">No action items recorded.</p>
            ) : (
              detail.result.action_items.map((item) => (
                <div key={item.task} className="rounded-xl border border-border p-4">
                  <p className="text-sm font-medium leading-6 text-card-foreground">{item.task}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-md bg-muted px-2 py-1 text-muted-foreground">
                      <Users size={12} className="mr-1 inline" />
                      {item.owner || 'Unassigned'}
                    </span>
                    <span className="rounded-md bg-muted px-2 py-1 text-muted-foreground">
                      <CalendarDays size={12} className="mr-1 inline" />
                      {item.deadline || 'No deadline'}
                    </span>
                    <span className={`rounded-md px-2 py-1 ${getPriorityClass(item.priority) === 'high' ? 'bg-rose-50 text-rose-700' : getPriorityClass(item.priority) === 'medium' ? 'bg-amber-50 text-amber-700' : 'bg-muted text-muted-foreground'}`}>
                      {item.priority || 'Unspecified'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </SectionCard>
        
        <div className="space-y-5">
          <SectionCard icon={MessageSquare} title="Open questions">
            <ul className="space-y-3">
              {detail.result.open_questions.length === 0 ? (
                <li className="text-sm text-muted-foreground italic">No open questions.</li>
              ) : (
                detail.result.open_questions.map((item) => (
                  <li key={item} className="flex gap-3 text-sm leading-6 text-muted-foreground">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    {item}
                  </li>
                ))
              )}
            </ul>
          </SectionCard>
          
          <SectionCard icon={Play} title="Next steps">
            <ol className="space-y-3">
              {detail.result.next_steps.length === 0 ? (
                <li className="text-sm text-muted-foreground italic">No immediate next steps.</li>
              ) : (
                detail.result.next_steps.map((item, index) => (
                  <li key={item} className="flex gap-3 text-sm leading-6 text-muted-foreground">
                    <span className="font-mono text-xs font-semibold text-primary">0{index + 1}</span>
                    {item}
                  </li>
                ))
              )}
            </ol>
          </SectionCard>
        </div>
      </div>
      
      <section className="mt-5 overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
        <button
          type="button"
          className="flex w-full items-center justify-between p-5 text-left sm:p-6"
          aria-expanded={transcriptOpen}
          onClick={() => setTranscriptOpen(!transcriptOpen)}
        >
          <span className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <FileText size={16} />
            </span>
            <span>
              <span className="block font-serif text-xl font-semibold tracking-tight">Transcript</span>
              <span className="mt-1 block text-sm text-muted-foreground">Full processed conversation text</span>
            </span>
          </span>
          <ChevronDown size={19} className={`text-muted-foreground transition-transform ${transcriptOpen ? 'rotate-180' : ''}`} />
        </button>
        
        {transcriptOpen && (
          <div className="border-t border-border p-5 sm:p-6">
            {detail.transcript.segments?.length ? (
              <div className="space-y-5">
                {detail.transcript.segments.map((segment) => (
                  <div key={`${segment.start}-${segment.text}`} className="flex gap-4">
                    <span className="w-12 shrink-0 pt-1 font-mono text-xs text-primary">{formatTimestamp(segment.start)}</span>
                    <p className="text-sm leading-7 text-muted-foreground">{segment.text}</p>
                  </div>
                ))}
              </div>
            ) : detail.transcript.text ? (
              <p className="whitespace-pre-line text-sm leading-7 text-muted-foreground">{detail.transcript.text}</p>
            ) : (
              <p className="text-sm text-muted-foreground italic">No transcript content was returned for this meeting.</p>
            )}
          </div>
        )}
      </section>
    </div>
  )
}

export default function MeetingSummarizer() {
  const [view, setView] = useState<View>('dashboard')
  const [detail, setDetail] = useState<MeetingDetail | null>(null)
  
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [historyError, setHistoryError] = useState('')

  const loadHistory = async () => {
    setLoadingHistory(true)
    setHistoryError('')
    try {
      const list = await getMeetings()
      setMeetings(list)
    } catch (err: any) {
      setHistoryError(err.message || 'Failed to load workspace history.')
    } finally {
      setLoadingHistory(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  const openMeeting = async (id: string) => {
    try {
      const next = await getMeeting(id)
      setDetail(next)
      setView('results')
    } catch (err: any) {
      alert(err.message || 'Failed to retrieve meeting details.')
    }
  }

  const handleProcessComplete = (nextDetail: MeetingDetail) => {
    setDetail(nextDetail)
    setView('results')
    loadHistory() // Refresh meeting history list
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <button
            type="button"
            onClick={() => { setView('dashboard'); setDetail(null); loadHistory() }}
            className="flex items-center gap-2.5 text-left"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Activity size={17} />
            </span>
            <span>
              <span className="block text-sm font-semibold tracking-tight">Meeting Summarizer</span>
              <span className="hidden text-xs text-muted-foreground sm:block">Clearer conversations, faster follow-through.</span>
            </span>
          </button>
          <span className="rounded-full border border-border bg-muted/50 px-3 py-1.5 text-xs font-medium text-muted-foreground">
            Workspace Active
          </span>
        </div>
      </header>
      
      {view === 'dashboard' ? (
        <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
          <div className="mb-9 max-w-2xl">
            <p className="mb-3 text-sm font-medium text-primary">Good morning</p>
            <h1 className="font-serif text-4xl font-semibold tracking-tight text-balance sm:text-5xl">Make every meeting easier to act on.</h1>
            <p className="mt-4 max-w-xl text-[15px] leading-7 text-muted-foreground">Upload your meeting audio to turn a long conversation into a focused summary your team can use right away.</p>
          </div>
          
          <div className="grid gap-12 lg:grid-cols-[1.35fr_0.65fr] lg:items-start">
            <UploadPanel onComplete={handleProcessComplete} />
            
            <aside className="rounded-2xl border border-border bg-muted/35 p-6">
              <div className="mb-5 flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-card text-primary shadow-sm">
                  <Sparkles size={17} />
                </span>
                <div>
                  <h2 className="text-sm font-semibold">What you&apos;ll get</h2>
                  <p className="text-xs text-muted-foreground">A structured view of the conversation.</p>
                </div>
              </div>
              <ul className="space-y-4">
                {[
                  ['Summary', 'A concise overview of what was discussed.'],
                  ['Decisions', 'The choices and agreements worth remembering.'],
                  ['Action items', 'Tasks with owners, deadlines, and priority.'],
                  ['Transcript', 'A full transcript record from the meeting audio.']
                ].map(([title, copy]) => (
                  <li key={title} className="flex gap-3">
                    <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                    <div>
                      <p className="text-sm font-medium">{title}</p>
                      <p className="mt-1 text-sm leading-6 text-muted-foreground">{copy}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </aside>
          </div>
          
          <History meetings={meetings} loading={loadingHistory} error={historyError} onSelect={openMeeting} />
        </main>
      ) : (
        detail && <Results detail={detail} onBack={() => { setView('dashboard'); loadHistory() }} />
      )}
    </div>
  )
}
