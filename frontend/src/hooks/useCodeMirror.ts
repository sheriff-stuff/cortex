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
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  // Create the editor once (or when readOnly changes)
  useEffect(() => {
    if (!containerRef.current) return;

    const isDark = document.documentElement.classList.contains('dark');

    const extensions = [
      keymap.of(defaultKeymap),
      markdown(),
      EditorView.lineWrapping,
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChangeRef.current?.(update.state.doc.toString());
        }
      }),
    ];
    if (isDark) extensions.push(oneDark);
    if (readOnly) {
      extensions.push(EditorState.readOnly.of(true));
      extensions.push(EditorView.editable.of(false));
    }

    const view = new EditorView({
      state: EditorState.create({ doc: initialDoc, extensions }),
      parent: containerRef.current,
    });
    viewRef.current = view;

    return () => {
      view.destroy();
      viewRef.current = null;
    };
  }, [readOnly]); // eslint-disable-line react-hooks/exhaustive-deps -- initialDoc handled by separate effect

  // Update document content without rebuilding the editor
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const currentDoc = view.state.doc.toString();
    if (currentDoc !== initialDoc) {
      view.dispatch({
        changes: { from: 0, to: currentDoc.length, insert: initialDoc },
      });
    }
  }, [initialDoc]);

  return containerRef;
}
