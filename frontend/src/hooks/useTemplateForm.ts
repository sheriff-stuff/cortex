import { useState, useEffect, useCallback } from 'react';
import type { TemplateDetail } from '@/types';
import { api } from '@/api';
import { DEFAULT_PROMPT } from '@/constants';

interface Options {
  templateId: number | null;
  isNew: boolean;
  onSaved: () => void;
}

export function useTemplateForm({ templateId, isNew, onSaved }: Options) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [promptText, setPromptText] = useState('');
  const [isDefault, setIsDefault] = useState(false);
  const [loading, setLoading] = useState(!!templateId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

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

  return {
    name, setName,
    description, setDescription,
    promptText, setPromptText,
    isDefault,
    loading,
    saving,
    error,
    handleSave,
  };
}
