import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { Database } from '@/lib/database.types'

type WordPair = Database['public']['Tables']['word_pairs']['Row']

const ITEMS_PER_PAGE = 20

export function useWordPairs() {
  const [wordPairs, setWordPairs] = useState<WordPair[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [mutationLoading, setMutationLoading] = useState(false)
  const [mutationError, setMutationError] = useState<Error | null>(null)

  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)

  useEffect(() => {
    fetchWordPairs()
  }, [currentPage])

  const fetchWordPairs = async () => {
    try {
      setLoading(true)

      const { count } = await supabase
        .from('word_pairs')
        .select('*', { count: 'exact', head: true })

      setTotalCount(count || 0)

      const from = (currentPage - 1) * ITEMS_PER_PAGE
      const to = from + ITEMS_PER_PAGE - 1

      const { data, error } = await supabase
        .from('word_pairs')
        .select('*')
        .order('created_at', { ascending: false })
        .range(from, to)

      if (error) {
        console.error('Error fetching word pairs:', error)
        return
      }

      setWordPairs(data || [])
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const refresh = () => {
    fetchWordPairs()
  }

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages))
  }

  const goToPreviousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1))
  }

  const addWordPair = async (
    word1: string,
    word2: string
  ): Promise<{ error: Error | null }> => {
    setMutationError(null)
    setMutationLoading(true)
    try {
      const { data: { user } } = await supabase.auth.getUser()
      if (!user) {
        setMutationError(new Error('You must be signed in to add word pairs'))
        return { error: new Error('You must be signed in to add word pairs') }
      }
      const { error } = await supabase.from('word_pairs').insert({
        user_id: user.id,
        word1: word1.trim(),
        word2: word2.trim(),
      })
      if (error) {
        const err = new Error(error.message)
        setMutationError(err)
        return { error: err }
      }
      refresh()
      return { error: null }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to add word pair')
      setMutationError(error)
      return { error }
    } finally {
      setMutationLoading(false)
    }
  }

  const updateWordPair = async (
    id: string,
    word1: string,
    word2: string
  ): Promise<{ error: Error | null }> => {
    setMutationError(null)
    setMutationLoading(true)
    try {
      const { error } = await supabase
        .from('word_pairs')
        .update({ word1: word1.trim(), word2: word2.trim() })
        .eq('id', id)
      if (error) {
        const err = new Error(error.message)
        setMutationError(err)
        return { error: err }
      }
      refresh()
      return { error: null }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to update word pair')
      setMutationError(error)
      return { error }
    } finally {
      setMutationLoading(false)
    }
  }

  const deleteWordPair = async (id: string): Promise<{ error: Error | null }> => {
    setMutationError(null)
    setMutationLoading(true)
    try {
      const { error } = await supabase.from('word_pairs').delete().eq('id', id)
      if (error) {
        const err = new Error(error.message)
        setMutationError(err)
        return { error: err }
      }
      refresh()
      return { error: null }
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to delete word pair')
      setMutationError(error)
      return { error }
    } finally {
      setMutationLoading(false)
    }
  }

  return {
    wordPairs,
    loading,
    currentPage,
    totalPages,
    totalCount,
    goToNextPage,
    goToPreviousPage,
    refresh,
    addWordPair,
    updateWordPair,
    deleteWordPair,
    mutationLoading,
    mutationError,
  }
}
