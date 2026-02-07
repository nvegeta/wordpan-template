import { useEffect } from 'react'
import { useRandomPhrase } from '@/hooks/use-random-phrase'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

export default function RandomPhrasePage() {
  const { phrase, words, loading, error, generatePhrase } = useRandomPhrase()

  // Generate initial phrase on component mount
  useEffect(() => {
    generatePhrase()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="container mx-auto py-8">
      <div className="max-w-3xl mx-auto space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Random Phrase Generator</CardTitle>
            <CardDescription>
              Generate creative phrases using three random words from the database
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Random Words Section */}
            <div>
              <h3 className="text-sm font-medium mb-3">Selected Words:</h3>
              <div className="flex gap-2 flex-wrap">
                {loading && words.length === 0 ? (
                  <>
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-6 w-20" />
                    <Skeleton className="h-6 w-20" />
                  </>
                ) : (
                  words.map((word) => (
                    <Badge key={word.id} variant="secondary" className="text-base px-3 py-1">
                      {word.word}
                    </Badge>
                  ))
                )}
              </div>
            </div>

            {/* Generated Phrase Section */}
            <div>
              <h3 className="text-sm font-medium mb-3">Generated Phrase:</h3>
              <div className="rounded-lg border bg-muted/50 p-6 min-h-[120px] flex items-center justify-center">
                {loading ? (
                  <div className="space-y-2 w-full">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-4 w-5/6" />
                  </div>
                ) : error ? (
                  <div className="text-center space-y-2">
                    <p className="text-destructive font-medium">Error generating phrase</p>
                    <p className="text-sm text-muted-foreground">{error.message}</p>
                  </div>
                ) : phrase ? (
                  <p className="text-lg text-center leading-relaxed">{phrase}</p>
                ) : (
                  <p className="text-muted-foreground text-center">
                    Click "Generate New Phrase" to start
                  </p>
                )}
              </div>
            </div>

            {/* Action Button */}
            <div className="flex justify-center pt-4">
              <Button
                size="lg"
                onClick={generatePhrase}
                disabled={loading}
              >
                {loading ? 'Generating...' : 'Generate New Phrase'}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Info Card */}
        <Card className="border-muted">
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground space-y-2">
              <p>
                This feature pulls three random words from the database and uses AI to create
                a creative phrase that incorporates all three words.
              </p>
              <p>
                Each generation is personalized based on your user profile context for a unique
                experience.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
