import { useState, useRef, useCallback, useEffect } from 'react';
import type { TemplateSummary } from '@/types';
import { cn } from '@/lib/utils';
import { api } from '@/api';
import { ACCEPTED_EXTENSIONS, formatFileSize, isValidFile } from '@/utils';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { X, Upload } from 'lucide-react';

interface Props {
  onUpload: (file: File, templateId?: number) => void;
  uploading: boolean;
}

export default function UploadPage({ onUpload, uploading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const [templates, setTemplates] = useState<TemplateSummary[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | undefined>();

  useEffect(() => {
    api.listTemplates().then((list) => {
      setTemplates(list);
      const def = list.find((t) => t.is_default);
      if (def) setSelectedTemplateId(def.id);
    });
  }, []);

  const handleFile = useCallback((f: File) => {
    if (!isValidFile(f)) {
      setError(`Unsupported format. Accepted: ${ACCEPTED_EXTENSIONS.join(', ')}`);
      setFile(null);
      return;
    }
    setError('');
    setFile(f);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const onDragLeave = useCallback(() => setDragOver(false), []);

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  return (
    <div className="flex flex-col items-center gap-6 py-8">
      <div className="text-center">
        <h1 className="text-2xl font-semibold mb-2">Process a Recording</h1>
        <p className="text-muted-foreground">Upload an audio or video file to generate structured notes</p>
      </div>

      <div
        className={cn(
          "w-full max-w-[560px] border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors bg-card",
          dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
        )}
        role="button"
        tabIndex={0}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputRef.current?.click(); } }}
      >
        <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
        <p className="text-base">
          Drag & drop your file here, or <strong>browse</strong>
        </p>
        <p className="text-sm text-muted-foreground mt-2">MP3, WAV, M4A, AAC, MP4, MKV, AVI, MOV</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(',')}
          onChange={onInputChange}
          className="hidden"
        />
      </div>

      {error && (
        <Alert variant="destructive" className="max-w-[560px]">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {file && (
        <div className="flex items-center gap-3 bg-card border rounded-lg px-4 py-2.5 max-w-[560px] w-full">
          <span className="font-medium truncate flex-1">{file.name}</span>
          <span className="text-sm text-muted-foreground whitespace-nowrap">{formatFileSize(file.size)}</span>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => setFile(null)}
            aria-label="Remove file"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Template selector */}
      {templates.length > 0 && (
        <div className="w-full max-w-[560px]">
          <label className="text-sm font-medium block mb-1">Extraction Template</label>
          <select
            value={selectedTemplateId ?? ''}
            onChange={(e) => setSelectedTemplateId(Number(e.target.value))}
            className="w-full px-3 py-2 rounded-md border bg-background text-sm"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}{t.is_default ? ' (Default)' : ''}
              </option>
            ))}
          </select>
        </div>
      )}

      <Button
        size="lg"
        disabled={!file || uploading}
        onClick={() => file && onUpload(file, selectedTemplateId)}
        className="min-w-[160px]"
      >
        {uploading ? 'Uploading...' : 'Process'}
      </Button>
    </div>
  );
}
