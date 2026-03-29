import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import { useCodeMirror } from '@/hooks/useCodeMirror';
import { useTemplateForm } from '@/hooks/useTemplateForm';
import TemplatePreview from './TemplatePreview';

interface Props {
  templateId: number | null;
  isNew: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export default function TemplateEditor({ templateId, isNew, onClose, onSaved }: Props) {
  const form = useTemplateForm({ templateId, isNew, onSaved });

  const editorRef = useCodeMirror({
    initialDoc: form.promptText,
    readOnly: form.isDefault,
    onChange: form.setPromptText,
  });

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
              {isNew ? 'New Template' : form.isDefault ? 'View Template' : 'Edit Template'}
            </h2>
            {form.isDefault && <Badge variant="secondary">Read-only</Badge>}
          </div>
          <Button variant="ghost" size="icon-xs" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {form.loading ? (
          <div className="p-6 text-center text-muted-foreground">Loading...</div>
        ) : (
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {/* Name */}
            <div>
              <label className="text-sm font-medium block mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => form.setName(e.target.value)}
                disabled={form.isDefault}
                className="w-full px-3 py-2 rounded-md border bg-background text-sm disabled:opacity-60"
                placeholder="Template name"
              />
            </div>

            {/* Description */}
            <div>
              <label className="text-sm font-medium block mb-1">Description</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => form.setDescription(e.target.value)}
                disabled={form.isDefault}
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

            {form.error && (
              <Alert variant="destructive">
                <AlertDescription>{form.error}</AlertDescription>
              </Alert>
            )}

            <TemplatePreview promptText={form.promptText} />
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end gap-2 px-6 py-4 border-t">
          <Button variant="outline" onClick={onClose}>
            {form.isDefault ? 'Close' : 'Cancel'}
          </Button>
          {!form.isDefault && (
            <Button onClick={form.handleSave} disabled={form.saving}>
              {form.saving ? 'Saving...' : 'Save'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
