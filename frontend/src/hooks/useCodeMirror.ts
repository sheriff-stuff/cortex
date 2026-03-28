import { useEffect, useRef } from 'react';
import { EditorView, keymap } from '@codemirror/view';
import { EditorState } from '@codemirror/state';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';
import { defaultKeymap } from '@codemirror/commands';

interface UseCodeMirrorOptions {
  initialDoc: string;
  readOnly?: boolean;
  onChange?: (value: string) => void;
}

/**
 * Mounts a CodeMirror editor into a container ref. Returns the ref to
 * attach to a div. Handles dark mode detection, read-only state, and cleanup.
 */
export function useCodeMirror({ initialDoc, readOnly = false, onChange }: UseCodeMirrorOptions) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const docRef = useRef(initialDoc);
  docRef.current = initialDoc;

  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = document.documentElement.classList.contains('dark');

    const extensions = [
      keymap.of(defaultKeymap),
      markdown(),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChange?.(update.state.doc.toString());
        }
      }),
    ];
    if (isDark) extensions.push(oneDark);
    if (readOnly) {
      extensions.push(EditorState.readOnly.of(true));
      extensions.push(EditorView.editable.of(false));
    }

    const view = new EditorView({
      state: EditorState.create({ doc: docRef.current, extensions }),
      parent: containerRef.current,
    });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [readOnly, onChange]);

  return containerRef;
}
