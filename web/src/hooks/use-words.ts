import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'
import type { Database } from '@/lib/database.types'

type Word = Database['public']['Tables']['words']['Row']

const ITEMS_PER_PAGE = 20

export function useWords() {
  const [words, setWords] = useState<Word[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  const totalPages = Math.ceil(totalCount / ITEMS_PER_PAGE)

  useEffect(() => {
    fetchWords()
  }, [currentPage])

  const fetchWords = async () => {
    try {
      setLoading(true)

      // Get total count
      const { count } = await supabase
        .from('words')
        .select('*', { count: 'exact', head: true })

      setTotalCount(count || 0)

      // Get paginated data
      const from = (currentPage - 1) * ITEMS_PER_PAGE
      const to = from + ITEMS_PER_PAGE - 1

      const { data, error } = await supabase
        .from('words')
        .select('*')
        .order('created_at', { ascending: false })
        .range(from, to)

      if (error) {
        console.error('Error fetching words:', error)
        return
      }

      setWords(data || [])
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  const goToNextPage = () => {
    setCurrentPage((prev) => Math.min(prev + 1, totalPages))
  }

  const goToPreviousPage = () => {
    setCurrentPage((prev) => Math.max(prev - 1, 1))
  }

  const goToPage = (page: number) => {
    setCurrentPage(Math.max(1, Math.min(page, totalPages)))
  }

  const refresh = () => {
    fetchWords()
  }

  return {
    words,
    loading,
    currentPage,
    totalPages,
    totalCount,
    goToNextPage,
    goToPreviousPage,
    goToPage,
    refresh,
  }
}
