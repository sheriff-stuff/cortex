import { useState, useRef, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { X, Upload } from 'lucide-react';

const ACCEPTED = ['.mp3', '.wav', '.m4a', '.aac', '.mp4', '.mkv', '.avi', '.mov'];

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isValidFile(file: File): boolean {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  return ACCEPTED.includes(ext);
}

interface Props {
  onUpload: (file: File) => void;
  uploading: boolean;
}

export default function UploadPage({ onUpload, uploading }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    if (!isValidFile(f)) {
      setError(`Unsupported format. Accepted: ${ACCEPTED.join(', ')}`);
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
        <h1 className="text-2xl font-semibold mb-2">Process a Meeting Recording</h1>
        <p className="text-muted-foreground">Upload an audio or video file to generate structured meeting notes</p>
      </div>

      <div
        className={cn(
          "w-full max-w-[560px] border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors bg-card",
          dragOver ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
        )}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => inputRef.current?.click()}
      >
        <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
        <p className="text-base">
          Drag & drop your file here, or <strong>browse</strong>
        </p>
        <p className="text-sm text-muted-foreground mt-2">MP3, WAV, M4A, AAC, MP4, MKV, AVI, MOV</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          onChange={onInputChange}
          style={{ display: 'none' }}
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
          <span className="text-sm text-muted-foreground whitespace-nowrap">{formatSize(file.size)}</span>
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

      <Button
        size="lg"
        disabled={!file || uploading}
        onClick={() => file && onUpload(file)}
        className="min-w-[160px]"
      >
        {uploading ? 'Uploading...' : 'Process'}
      </Button>
    </div>
  );
}
