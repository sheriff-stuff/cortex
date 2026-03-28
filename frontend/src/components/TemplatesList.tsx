import { useState, useEffect, useCallback } from 'react';
import type { TemplateSummary } from '@/types';
import { api } from '@/api';
import { Card, CardHeader, CardTitle, CardDescription, CardAction } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Copy, Trash2, Plus } from 'lucide-react';
import TemplateEditor from './TemplateEditor';

export default function TemplatesList() {
  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [isNew, setIsNew] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const list = await api.listTemplates();
      setTemplates(list);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const openEditor = (id: number) => {
    setEditingId(id);
    setIsNew(false);
    setEditorOpen(true);
  };

  const openNew = () => {
    setEditingId(null);
    setIsNew(true);
    setEditorOpen(true);
  };

  const handleDuplicate = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    await api.duplicateTemplate(id);
    refresh();
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    await api.deleteTemplate(id);
    refresh();
  };

  const handleEditorClose = () => {
    setEditorOpen(false);
    setEditingId(null);
    setIsNew(false);
  };

  const handleEditorSaved = () => {
    handleEditorClose();
    refresh();
  };

  if (loading) {
    return <p className="text-center py-16 text-muted-foreground">Loading templates...</p>;
  }

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Prompt Templates</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Customize how meetings are summarized by the LLM
          </p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {templates.map((tmpl) => (
          <Card
            key={tmpl.id}
            className="cursor-pointer hover:border-primary/50 transition-colors"
            onClick={() => openEditor(tmpl.id)}
          >
            <CardHeader>
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <CardTitle className="flex items-center gap-2">
                    <span className="truncate">{tmpl.name}</span>
                    {tmpl.is_default ? <Badge variant="secondary">Default</Badge> : null}
                  </CardTitle>
                  {tmpl.description && (
                    <CardDescription className="line-clamp-2 mt-1">
                      {tmpl.description}
                    </CardDescription>
                  )}
                </div>
                <CardAction>
                  <div className="flex gap-1">
                    <Button
                      variant="ghost"
                      size="icon-xs"
                      onClick={(e) => handleDuplicate(e, tmpl.id)}
                      title="Duplicate"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                    {!tmpl.is_default && (
                      <Button
                        variant="ghost"
                        size="icon-xs"
                        onClick={(e) => handleDelete(e, tmpl.id)}
                        title="Delete"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </CardAction>
              </div>
            </CardHeader>
          </Card>
        ))}

        {/* Create new template card */}
        <Card
          className="cursor-pointer border-dashed hover:border-primary/50 transition-colors"
          onClick={openNew}
        >
          <CardHeader>
            <div className="flex flex-col items-center justify-center py-4 text-muted-foreground">
              <Plus className="h-8 w-8 mb-2" />
              <CardTitle className="text-base">Create Template</CardTitle>
            </div>
          </CardHeader>
        </Card>
      </div>

      {editorOpen && (
        <TemplateEditor
          templateId={editingId}
          isNew={isNew}
          onClose={handleEditorClose}
          onSaved={handleEditorSaved}
        />
      )}
    </>
  );
}
