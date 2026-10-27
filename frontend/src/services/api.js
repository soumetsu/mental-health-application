export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, { token, ...options } = {}) {
  const headers = new Headers(options.headers || {})
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response
  try {
    response = await fetch(`/api${path}`, { ...options, headers })
  } catch {
    throw new ApiError('The app could not reach the server. Check that the backend is running.')
  }

  if (response.status === 204) return null
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(data?.detail || 'Something went wrong. Please try again.', response.status)
  return data
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  me: (token) => request('/auth/me', { token }),
  logout: (token) => request('/auth/logout', { method: 'POST', token }),
  getQuestionnaire: (token) => request('/questionnaire', { token }),
  saveQuestionnaire: (token, payload) => request('/questionnaire', { method: 'PUT', token, body: JSON.stringify(payload) }),
  dashboard: (token) => request('/dashboard', { token }),
  checkIns: (token) => request('/check-ins', { token }),
  createCheckIn: (token, payload) => request('/check-ins', { method: 'POST', token, body: JSON.stringify(payload) }),
  events: (token, month) => request(`/events${month ? `?month=${encodeURIComponent(month)}` : ''}`, { token }),
  createEvent: (token, payload) => request('/events', { method: 'POST', token, body: JSON.stringify(payload) }),
  deleteEvent: (token, id) => request(`/events/${encodeURIComponent(id)}`, { method: 'DELETE', token }),
  exercises: () => request('/exercises'),
  exerciseHistory: (token) => request('/exercise-history', { token }),
  startExercise: (token, exerciseId) => request('/exercise-history', {
    method: 'POST', token, body: JSON.stringify({ exercise_id: exerciseId }),
  }),
  updateExerciseHistory: (token, id, payload) => request(`/exercise-history/${encodeURIComponent(id)}`, {
    method: 'PATCH', token, body: JSON.stringify(payload),
  }),
  deleteExerciseHistory: (token, id) => request(`/exercise-history/${encodeURIComponent(id)}`, {
    method: 'DELETE', token,
  }),
  sendChatMessage: (token, message, history) => request('/chat', {
    method: 'POST', token, body: JSON.stringify({ message, history }),
  }),
}

