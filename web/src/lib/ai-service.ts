import { supabase } from './supabase'

const AI_SERVICE_URL = import.meta.env.VITE_AI_SERVICE_URL || 'http://localhost:8000'

export interface RandomPhraseResponse {
  phrase: string
  words_used: string[]
}

export interface SimilarWordsResponse {
  similar_words: string[]
}

export type TutorIntent =
  | 'translation'
  | 'new_vocabulary'
  | 'grammar_explanation'
  | 'writing_correction'
  | 'cultural_context'
  | 'small_talk_language_related'
  | 'off_topic'

export interface TutorWordCard {
  word: string
  translation: string
  example_sentence: string
  explanation?: string | null
  part_of_speech?: string | null
}

export interface TutorAction {
  type: string
  payload: Record<string, unknown>
}

export interface TutorMessageResponse {
  role: 'assistant'
  content: string
  intent: TutorIntent
  word_card: TutorWordCard | null
  actions: TutorAction[]
  delegated_agent?: string | null
}

export interface LivekitTokenResponse {
  token: string
  url: string
  roomName: string
}

/**
 * Generate a random phrase using the AI service
 * @param words - Array of words to use in the phrase
 * @returns Promise with the generated phrase and words used
 */
export async function generateRandomPhrase(words: string[]): Promise<RandomPhraseResponse> {
  // Get the current session token
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('User must be authenticated to generate phrases')
  }

  const response = await fetch(`${AI_SERVICE_URL}/api/random-phrase`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ words }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `Failed to generate phrase: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get similar/related words for a word pair using the AI service
 * @param word1 - First word of the pair
 * @param word2 - Second word of the pair
 * @returns Promise with list of similar words
 */
export async function getSimilarWords(
  word1: string,
  word2: string
): Promise<SimilarWordsResponse> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('User must be authenticated to get similar words')
  }

  const response = await fetch(`${AI_SERVICE_URL}/api/similar-words`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ word1, word2 }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `Failed to get similar words: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Call the Smart Tutor chat endpoint with full conversation history.
 * @param messages - Conversation history as an array of { role, content }
 */
export async function callTutorChat(
  messages: Array<{ role: 'user' | 'assistant' | 'system'; content: string }>,
): Promise<TutorMessageResponse> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('User must be authenticated to chat with tutor')
  }

  const response = await fetch(`${AI_SERVICE_URL}/api/tutor-chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({ messages }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `Tutor chat failed: ${errorData.error || response.statusText}`)
  }

  return response.json()
}

/**
 * Request a LiveKit access token for the current user from the AI service.
 * The token is used by the frontend to join a LiveKit room with the voice agent.
 */
export async function getLivekitToken(roomName?: string): Promise<LivekitTokenResponse> {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    throw new Error('User must be authenticated to start a voice session')
  }

  const response = await fetch(`${AI_SERVICE_URL}/api/livekit-token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${session.access_token}`,
    },
    body: JSON.stringify({
      roomName,
    }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: 'Unknown error' }))
    throw new Error(errorData.error || `Failed to get LiveKit token: ${response.statusText}`)
  }

  return response.json()
}
