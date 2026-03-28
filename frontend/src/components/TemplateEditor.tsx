import { useState, useEffect, useCallback } from 'react';
import type { TemplateDetail, Topic, Decision, ActionItem, Question } from '@/types';
import { api } from '@/api';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import SummaryTab from '@/components/notes/SummaryTab';
import { X, Play, Loader2, ChevronRight } from 'lucide-react';
import { useCodeMirror } from '@/hooks/useCodeMirror';

interface Props {
  templateId: number | null;
  isNew: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const DEFAULT_PROMPT = `You are analyzing a meeting transcript. Extract structured information as JSON.
Only extract what is explicitly stated in the transcript. Do not infer or hallucinate.

Rules:
- For action items, look for future-oriented language: "I'll", "we need to", "let's", "will", "should", "going to"
- For questions, search for answers within 2 minutes after the question was asked
- If a question was not answered within 2 minutes, set answer to null
- Use speaker labels exactly as they appear (e.g., "Speaker 1")
- Use MM:SS format for all timestamps
- Include ALL items found, don't skip any

Return ONLY valid JSON, no explanation or markdown fences.`;

export default function TemplateEditor({ templateId, isNew, onClose, onSaved }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [promptText, setPromptText] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [loading, setLoading] = useState(!!templateId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const [renderLoading, setRenderLoading] = useState(false);
  const [renderResult, setRenderResult] = useState<{
    topics: Topic[]; decisions: Decision[]; action_items: ActionItem[]; questions: Question[];
  } | null>(null);
  const [renderError, setRenderError] = useState('');
  const [previewOpen, setPreviewOpen] = useState(true);

  useEffect(() => {
    if (templateId) {
      api.getTemplate(templateId).then((tmpl: TemplateDetail) => {
        setName(tmpl.name);
        setDescription(tmpl.description);
        setPromptText(tmpl.prompt_text);
        setIsDefault(!!tmpl.is_default);
        setLoading(false);
      }).catch(() => {
        setError('Failed to load template');
        setLoading(false);
      });
    } else if (isNew) {
      setPromptText(DEFAULT_PROMPT);
    }
  }, [templateId, isNew]);

  const editorRef = useCodeMirror({
    initialDoc: promptText,
    readOnly: isDefault,
    onChange: setPromptText,
  });

  const handleSave = useCallback(async () => {
    setError('');
    if (!name.trim()) {
      setError('Name is required');
      return;
    }
    setSaving(true);
    try {
      if (isNew) {
        await api.createTemplate({ name: name.trim(), description: description.trim(), prompt_text: promptText });
      } else if (templateId) {
        await api.updateTemplate(templateId, { name: name.trim(), description: description.trim(), prompt_text: promptText });
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [name, description, promptText, isNew, templateId, onSaved]);

  const handleRenderExample = useCallback(async () => {
    setRenderError('');
    setRenderResult(null);
    setRenderLoading(true);
    try {
      const result = await api.renderExample(promptText);
      setRenderResult(result);
      setPreviewOpen(true);
    } catch (err) {
      setRenderError(err instanceof Error ? err.message : 'Render failed');
    } finally {
      setRenderLoading(false);
    }
  }, [promptText]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div className="relative bg-card border rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              {isNew ? 'New Template' : isDefault ? 'View Template' : 'Edit Template'}
            </h2>
            {isDefault && <Badge variant="secondary">Read-only</Badge>}
          </div>
          <Button variant="ghost" size="icon-xs" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {loading ? (
          <div className="p-6 text-center text-muted-foreground">Loading...</div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {/* Name */}
            <div>
              <label className="text-sm font-medium block mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isDefault}
                className="w-full px-3 py-2 rounded-md border bg-background text-sm disabled:opacity-60"
                placeholder="Template name"
              />
            </div>

            {/* Description */}
            <div>
              <label className="text-sm font-medium block mb-1">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isDefault}
                className="w-full px-3 py-2 rounded-md border bg-background text-sm disabled:opacity-60"
                placeholder="Short description of what this template extracts"
              />
            </div>

            {/* Prompt editor */}
            <div>
              <label className="text-sm font-medium block mb-1">Prompt Instructions</label>
              <div
                ref={editorRef}
                className="border rounded-md overflow-hidden [&_.cm-editor]:min-h-[300px] [&_.cm-editor]:max-h-[400px] [&_.cm-scroller]:overflow-auto [&_.cm-editor.cm-focused]:outline-none"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Write your extraction instructions. The transcript and output schema are automatically injected.
              </p>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {/* Render Example */}
            <div className="pt-2">
              <Button
                variant="outline"
                onClick={handleRenderExample}
                disabled={renderLoading || !promptText.trim()}
              >
                {renderLoading ? (
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

            {renderError && (
              <Alert variant="destructive">
                <AlertDescription>{renderError}</AlertDescription>
              </Alert>
            )}

            {renderResult && (
              <Collapsible open={previewOpen} onOpenChange={setPreviewOpen}>
                <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 text-left cursor-pointer hover:bg-muted/50 rounded-md px-1 -mx-1 transition-colors group">
                  <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-data-[panel-open]:rotate-90" />
                  <span className="font-medium text-sm">Example Output Preview</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="border rounded-md p-4 mt-2 bg-muted/30">
                    <SummaryTab
                      topics={renderResult.topics}
                      decisions={renderResult.decisions}
                      actionItems={renderResult.action_items}
                      questions={renderResult.questions}
                      apply={(text) => text}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t">
          <Button variant="outline" onClick={onClose}>
            {isDefault ? 'Close' : 'Cancel'}
          </Button>
          {!isDefault && (
            <Button onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
