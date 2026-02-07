import { useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import { generateRandomPhrase, type RandomPhraseResponse } from '@/lib/ai-service'
import type { Database } from '@/lib/database.types'

type Word = Database['public']['Tables']['words']['Row']

export interface UseRandomPhraseReturn {
  phrase: string | null
  words: Word[]
  loading: boolean
  error: Error | null
  generatePhrase: () => Promise<void>
}

/**
 * Custom hook to fetch three random words from Supabase and generate a phrase using AI
 */
export function useRandomPhrase(): UseRandomPhraseReturn {
  const [phrase, setPhrase] = useState<string | null>(null)
  const [words, setWords] = useState<Word[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const generatePhrase = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      setPhrase(null)

      // Fetch three random words from Supabase
      // Using a random ordering approach with limit
      const { data: randomWords, error: wordsError } = await supabase
        .from('words')
        .select('*')
        .limit(100) // Get a sample to pick from

      if (wordsError) {
        throw new Error(`Failed to fetch words: ${wordsError.message}`)
      }

      if (!randomWords || randomWords.length === 0) {
        throw new Error('No words found in the database')
      }

      // Pick 3 random words from the sample
      const shuffled = [...randomWords].sort(() => 0.5 - Math.random())
      const selectedWords = shuffled.slice(0, Math.min(3, randomWords.length))

      setWords(selectedWords)

      // Generate phrase using the AI service
      const wordStrings = selectedWords.map(w => w.word)
      const response: RandomPhraseResponse = await generateRandomPhrase(wordStrings)

      setPhrase(response.phrase)

    } catch (err) {
      const error = err instanceof Error ? err : new Error('An unknown error occurred')
      setError(error)
      console.error('Error generating phrase:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    phrase,
    words,
    loading,
    error,
    generatePhrase,
  }
}
