import { useState, useCallback, useEffect } from 'react';
import type { AppState, MeetingNotes } from '@/types';
import { api } from '@/api';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import Layout from '@/components/Layout';
import NotesList from '@/components/NotesList';
import UploadPage from '@/components/UploadPage';
import NotesView from '@/components/NotesView';
import TemplatesList from '@/components/TemplatesList';

/** Parse current URL path into page + optional note filename. */
function parseLocation(): { page: 'notes' | 'templates'; filename?: string } {
  const path = window.location.pathname;
  if (path === '/templates') return { page: 'templates' };
  if (path.startsWith('/notes/')) {
    const filename = decodeURIComponent(path.slice('/notes/'.length));
    if (filename) return { page: 'notes', filename };
  }
  return { page: 'notes' };
}

export default function App() {
  const [page, setPage] = useState<'notes' | 'templates'>('notes');
  const [state, setState] = useState<AppState>('home');
  const [notes, setNotes] = useState<MeetingNotes | null>(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  // Bump to force NotesList re-mount after upload
  const [listKey, setListKey] = useState(0);

  const goHome = useCallback((pushHistory = true) => {
    setState('home');
    setNotes(null);
    setError('');
    setUploading(false);
    setListKey((k) => k + 1);
    if (pushHistory) {
      window.history.pushState(null, '', '/');
    }
  }, []);

  // Load initial state from URL + handle browser back/forward
  useEffect(() => {
    const loadFromUrl = async () => {
      const loc = parseLocation();
      setPage(loc.page);
      if (loc.filename) {
        try {
          const n = await api.getSavedNotes(loc.filename);
          setNotes(n);
          setState('viewing');
        } catch {
          setState('home');
        }
      }
    };
    loadFromUrl();

    const onPopState = () => {
      const loc = parseLocation();
      setPage(loc.page);
      if (loc.filename) {
        api.getSavedNotes(loc.filename).then((n) => {
          setNotes(n);
          setState('viewing');
        }).catch(() => {
          goHome(false);
        });
      } else if (loc.page === 'templates') {
        setState('home');
      } else {
        setState('home');
        setNotes(null);
      }
    };
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [goHome]);

  const handleUpload = useCallback(async (file: File, templateId?: number) => {
    setUploading(true);
    setError('');
    try {
      await api.upload(file, templateId);
      setUploading(false);
      // Go straight to home — NotesList shows job progress inline
      goHome();
    } catch (err) {
      setUploading(false);
      setError(err instanceof Error ? err.message : 'Upload failed');
      setState('error');
    }
  }, [goHome]);

  const handleSelectNote = useCallback(async (filename: string) => {
    try {
      const n = await api.getSavedNotes(filename);
      setNotes(n);
      setState('viewing');
      window.history.pushState(null, '', `/notes/${encodeURIComponent(filename)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load notes');
      setState('error');
    }
  }, []);

  const handleNavigate = useCallback((p: 'notes' | 'templates') => {
    setPage(p);
    if (p === 'notes') {
      goHome();
    } else {
      window.history.pushState(null, '', '/templates');
    }
  }, [goHome]);

  return (
    <Layout activePage={page} onNavigate={handleNavigate} onUpload={() => { setPage('notes'); setState('uploading'); }}>
      {page === 'templates' && <TemplatesList />}

      {page === 'notes' && (
        <>
          {state === 'home' && (
            <NotesList
              key={listKey}
              onSelect={handleSelectNote}
              onUpload={() => setState('uploading')}
            />
          )}

          {state === 'uploading' && (
            <UploadPage onUpload={handleUpload} uploading={uploading} />
          )}

          {state === 'viewing' && notes && (
            <NotesView notes={notes} onReset={goHome} onNotesUpdated={setNotes} />
          )}

          {state === 'error' && (
            <div className="text-center py-16">
              <Alert variant="destructive" className="max-w-md mx-auto mb-4">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
              <Button onClick={() => goHome()}>Back to Home</Button>
            </div>
          )}
        </>
      )}
    </Layout>
  );
}
