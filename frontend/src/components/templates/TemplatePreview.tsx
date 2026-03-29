import { useState, useCallback } from 'react';
import type { Topic, Decision, ActionItem, Question } from '@/types';
import { api } from '@/api';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import SummaryTab from '@/components/notes/SummaryTab';
import { Play, Loader2, ChevronRight } from 'lucide-react';

interface Props {
  promptText: string;
}

export default function TemplatePreview({ promptText }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{
    topics: Topic[]; decisions: Decision[]; action_items: ActionItem[]; questions: Question[];
  } | null>(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(true);

  const handleRender = useCallback(async () => {
    setError('');
    setResult(null);
    setLoading(true);
    try {
      const data = await api.renderExample(promptText);
      setResult(data);
      setOpen(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Render failed');
    } finally {
      setLoading(false);
    }
  }, [promptText]);

  return (
    <>
      <div className="pt-2">
        <Button
          variant="outline"
          onClick={handleRender}
          disabled={loading || !promptText.trim()}
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Running example (this may take up to 60s)...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Render Example
            </>
          )}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && (
        <Collapsible open={open} onOpenChange={setOpen}>
          <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 text-left cursor-pointer hover:bg-muted/50 rounded-md px-1 -mx-1 transition-colors group">
            <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-data-[panel-open]:rotate-90" />
            <span className="font-medium text-sm">Example Output Preview</span>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="border rounded-md p-4 mt-2 bg-muted/30">
              <SummaryTab
                topics={result.topics}
                decisions={result.decisions}
                actionItems={result.action_items}
                questions={result.questions}
                apply={(text) => text}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
      )}
    </>
  );
}
