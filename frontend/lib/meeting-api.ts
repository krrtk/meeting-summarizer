export type MeetingStatus = 'processing' | 'completed' | 'failed'

export interface Meeting {
  id: string
  filename: string
  created_at: string
  status: MeetingStatus
  duration?: number
  error_message?: string | null
}

export interface ActionItem {
  task: string
  owner?: string | null
  deadline?: string | null
  priority?: string | null
}

export interface MeetingResult {
  meeting_title: string
  summary: string
  key_decisions: string[]
  action_items: ActionItem[]
  open_questions: string[]
  next_steps: string[]
}

export interface TranscriptSegment { start: number; end: number; text: string }
export interface Transcript { text: string; segments?: TranscriptSegment[] }
export interface MeetingDetail { meeting: Meeting; result: MeetingResult; transcript: Transcript }

export const acceptedAudioTypes = ['audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/mp4', 'audio/ogg', 'audio/webm']
export const acceptedAudioExtensions = ['.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.webm']

// Determine base API URL dynamically from Vite or Next.js environment variables, defaulting to local port 8000
const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.VITE_API_BASE_URL ||
  'http://localhost:8000'

export async function uploadMeeting(file: File): Promise<{ meeting_id: string }> {
  const formData = new FormData()
  formData.append('file', file)
  
  const res = await fetch(`${API_BASE_URL}/api/meetings`, {
    method: 'POST',
    body: formData
  })
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    const errorMessage = errorData.detail?.message || 'Failed to upload and process meeting audio.'
    throw new Error(errorMessage)
  }
  
  const data = await res.json()
  return { meeting_id: String(data.id) }
}

export async function getMeeting(id: string): Promise<MeetingDetail> {
  const res = await fetch(`${API_BASE_URL}/api/meetings/${id}`)
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    const errorMessage = errorData.detail?.message || 'Failed to fetch meeting details.'
    throw new Error(errorMessage)
  }
  
  const data = await res.json()
  
  const meeting: Meeting = {
    id: String(data.id),
    filename: data.filename,
    created_at: data.created_at,
    status: data.status as MeetingStatus,
    duration: undefined
  }
  
  const result: MeetingResult = data.result || {
    meeting_title: data.filename.replace(/\.(mp3|wav|m4a|mp4|ogg|webm)$/i, ''),
    summary: data.error_message || 'No summary available.',
    key_decisions: [],
    action_items: [],
    open_questions: [],
    next_steps: []
  }
  
  const transcript: Transcript = {
    text: data.transcript || '',
    segments: [] // SQLite stores raw text transcript; return empty segments array
  }
  
  return { meeting, result, transcript }
}

export async function getMeetings(): Promise<Meeting[]> {
  const res = await fetch(`${API_BASE_URL}/api/meetings`)
  
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    const errorMessage = errorData.detail?.message || 'Failed to retrieve meeting history.'
    throw new Error(errorMessage)
  }
  
  const data = await res.json()
  return data.map((item: any) => ({
    id: String(item.id),
    filename: item.filename,
    created_at: item.created_at,
    status: item.status as MeetingStatus,
    error_message: item.error_message,
    duration: undefined
  }))
}

export function formatMeetingDate(value: string) { 
  try {
    return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) 
  } catch (e) {
    return value
  }
}

export function formatFileSize(bytes: number) { 
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB` 
}

export function formatTimestamp(seconds: number) { 
  return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}` 
}

export function validateAudio(file: File) {
  const lastDotIndex = file.name.lastIndexOf('.')
  const extension = lastDotIndex !== -1 ? file.name.slice(lastDotIndex).toLowerCase() : ''
  if (!acceptedAudioTypes.includes(file.type) && !acceptedAudioExtensions.includes(extension)) {
    return 'Please choose a supported audio file (MP3, WAV, M4A, MP4, OGG, WEBM).'
  }
  if (file.size === 0) return 'This file is empty. Please choose a different recording.'
  if (file.size > 100 * 1024 * 1024) return 'Files must be smaller than 100 MB.'
  return null
}

export function getHistoryPreview(status: MeetingStatus, errorMessage?: string | null) { 
  if (status === 'failed') return errorMessage || 'Processing failed.'
  if (status === 'processing') return 'Meeting is being transcribed and analyzed...'
  return 'Review the generated summary, decisions, and next steps from this meeting.' 
}

export function getPriorityClass(priority?: string | null) { 
  return priority?.toLowerCase() === 'high' ? 'high' : priority?.toLowerCase() === 'medium' ? 'medium' : 'low' 
}

export const api = { uploadMeeting, getMeeting, getMeetings }
export default api
