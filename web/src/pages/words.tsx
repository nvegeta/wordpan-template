import { useState } from 'react'
import { useWords } from '@/hooks/use-words'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
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

export default function WordsPage() {
  const [addOpen, setAddOpen] = useState(false)
  const [newWord, setNewWord] = useState('')
  const {
    words,
    loading,
    currentPage,
    totalPages,
    totalCount,
    goToNextPage,
    goToPreviousPage,
    addWord,
    addLoading,
    addError,
  } = useWords()

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleAddWord = async (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = newWord.trim()
    if (!trimmed) return
    const { error } = await addWord(trimmed)
    if (!error) {
      setAddOpen(false)
      setNewWord('')
    }
  }

  const handleCloseAdd = () => {
    setAddOpen(false)
    setNewWord('')
  }

  return (
    <div className="container mx-auto py-8">
      <Card>
        <CardHeader className="flex flex-row items-start justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle>Words</CardTitle>
            <CardDescription>
              All words from the database (showing {words.length} of {totalCount} words)
            </CardDescription>
          </div>
          <Button onClick={() => setAddOpen(true)}>Add word</Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">Loading words...</p>
            </div>
          ) : words.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <p className="text-muted-foreground">No words found</p>
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">ID</TableHead>
                      <TableHead>Word</TableHead>
                      <TableHead className="text-right">Created At</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {words.map((word) => (
                      <TableRow key={word.id}>
                        <TableCell className="font-mono text-xs">
                          {word.id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className="font-medium">{word.word}</TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {formatDate(word.created_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Pagination Controls */}
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
        open={addOpen}
        onOpenChange={(open) => {
          setAddOpen(open)
          if (!open) setNewWord('')
        }}
      >
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>Add new word</SheetTitle>
          </SheetHeader>
          <form onSubmit={handleAddWord} className="flex flex-col gap-4 py-4">
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="new-word">Word</FieldLabel>
                <Input
                  id="new-word"
                  value={newWord}
                  onChange={(e) => setNewWord(e.target.value)}
                  placeholder="Enter a word"
                  disabled={addLoading}
                  autoFocus
                />
                {addError && <FieldError>{addError.message}</FieldError>}
              </Field>
            </FieldGroup>
            <SheetFooter className="flex gap-2 sm:gap-0">
              <Button type="button" variant="outline" onClick={handleCloseAdd} disabled={addLoading}>
                Cancel
              </Button>
              <Button type="submit" disabled={addLoading || !newWord.trim()}>
                {addLoading ? 'Adding...' : 'Add'}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </div>
  )
}
