import { useState } from 'react'
import { useWordPairs } from '@/hooks/use-word-pairs'
import { getSimilarWords } from '@/lib/ai-service'
import type { Database } from '@/lib/database.types'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetFooter,
} from '@/components/ui/sheet'
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldError,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

type WordPair = Database['public']['Tables']['word_pairs']['Row']

export default function WordPairsPage() {
  const [sheetOpen, setSheetOpen] = useState(false)
  const [editingPair, setEditingPair] = useState<WordPair | null>(null)
  const [word1, setWord1] = useState('')
  const [word2, setWord2] = useState('')
  const [similarWords, setSimilarWords] = useState<string[] | null>(null)
  const [similarWordsLoading, setSimilarWordsLoading] = useState(false)
  const [similarWordsError, setSimilarWordsError] = useState<Error | null>(null)

  const {
    wordPairs,
    loading,
    currentPage,
    totalPages,
    totalCount,
    goToNextPage,
    goToPreviousPage,
    addWordPair,
    updateWordPair,
    deleteWordPair,
    mutationLoading,
    mutationError,
  } = useWordPairs()

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const openAdd = () => {
    setEditingPair(null)
    setWord1('')
    setWord2('')
    setSheetOpen(true)
  }

  const openEdit = (pair: WordPair) => {
    setEditingPair(pair)
    setWord1(pair.word1)
    setWord2(pair.word2)
    setSheetOpen(true)
  }

  const handleCloseSheet = () => {
    setSheetOpen(false)
    setEditingPair(null)
    setWord1('')
    setWord2('')
    setSimilarWords(null)
    setSimilarWordsError(null)
  }

  const fetchSimilarWords = async () => {
    const w1 = (editingPair?.word1 ?? word1).trim()
    const w2 = (editingPair?.word2 ?? word2).trim()
    if (!w1 || !w2) return
    setSimilarWordsLoading(true)
    setSimilarWordsError(null)
    setSimilarWords(null)
    try {
      const res = await getSimilarWords(w1, w2)
      setSimilarWords(res.similar_words)
    } catch (err) {
      setSimilarWordsError(err instanceof Error ? err : new Error('Failed to load similar words'))
    } finally {
      setSimilarWordsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const w1 = word1.trim()
    const w2 = word2.trim()
    if (!w1 || !w2) return

    if (editingPair) {
      const { error } = await updateWordPair(editingPair.id, w1, w2)
      if (!error) handleCloseSheet()
    } else {
      const { error } = await addWordPair(w1, w2)
      if (!error) handleCloseSheet()
    }
  }

  const handleDelete = async (pair: WordPair) => {
    if (!window.confirm(`Delete "${pair.word1}" – "${pair.word2}"?`)) return
    await deleteWordPair(pair.id)
  }

  const canSubmit = word1.trim() && word2.trim()

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle>Word Pairs</CardTitle>
            <CardDescription>
              Manage word pairs (showing {wordPairs.length} of {totalCount})
            </CardDescription>
          </div>
          <Button onClick={openAdd}>Add word pair</Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">Loading word pairs...</p>
            </div>
          ) : wordPairs.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">No word pairs found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Word 1</TableHead>
                      <TableHead>Word 2</TableHead>
                      <TableHead className="text-right">Created At</TableHead>
                      <TableHead className="w-[140px] text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {wordPairs.map((pair) => (
                      <TableRow key={pair.id}>
                        <TableCell className="font-medium">{pair.word1}</TableCell>
                        <TableCell className="font-medium">{pair.word2}</TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatDate(pair.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => openEdit(pair)}
                              disabled={mutationLoading}
                            >
                              Edit
                            </Button>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => handleDelete(pair)}
                              disabled={mutationLoading}
                            >
                              Delete
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex items-center justify-between px-2 py-4">
                <div className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={goToPreviousPage}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={goToNextPage}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Sheet
        open={sheetOpen}
        onOpenChange={(open) => {
          setSheetOpen(open)
          if (!open) {
            setEditingPair(null)
            setWord1('')
            setWord2('')
          }
        }}
      >
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>
              {editingPair ? 'Edit word pair' : 'Add new word pair'}
            </SheetTitle>
          </SheetHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4 py-4">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="word1">Word 1</FieldLabel>
                <Input
                  id="word1"
                  value={word1}
                  onChange={(e) => setWord1(e.target.value)}
                  placeholder="First word"
                  disabled={mutationLoading}
                  autoFocus
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="word2">Word 2</FieldLabel>
                <Input
                  id="word2"
                  value={word2}
                  onChange={(e) => setWord2(e.target.value)}
                  placeholder="Second word"
                  disabled={mutationLoading}
                />
              </Field>
              {mutationError && (
                <FieldError>{mutationError.message}</FieldError>
              )}
            </FieldGroup>

            {(editingPair || (word1.trim() && word2.trim())) && (
              <div className="space-y-2 rounded-lg border bg-muted/30 p-3">
                <h4 className="text-sm font-medium">Similar words</h4>
                <p className="text-xs text-muted-foreground">
                  Get AI-suggested related words for this pair
                </p>
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={fetchSimilarWords}
                  disabled={similarWordsLoading}
                >
                  {similarWordsLoading ? 'Loading…' : 'Suggest similar words'}
                </Button>
                {similarWordsLoading && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    <Skeleton className="h-5 w-16" />
                    <Skeleton className="h-5 w-20" />
                    <Skeleton className="h-5 w-14" />
                    <Skeleton className="h-5 w-20" />
                  </div>
                )}
                {similarWordsError && !similarWordsLoading && (
                  <p className="text-sm text-destructive">{similarWordsError.message}</p>
                )}
                {similarWords && similarWords.length > 0 && !similarWordsLoading && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {similarWords.map((w) => (
                      <Badge key={w} variant="secondary" className="text-xs">
                        {w}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            )}

            <SheetFooter className="flex gap-2 sm:gap-0">
              <Button
                type="button"
                variant="outline"
                onClick={handleCloseSheet}
                disabled={mutationLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={mutationLoading || !canSubmit}>
                {mutationLoading
                  ? 'Saving...'
                  : editingPair
                    ? 'Save'
                    : 'Add'}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  )
}
