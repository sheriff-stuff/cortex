import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Upload } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

type Page = 'notes' | 'templates';

interface Props {
  children: ReactNode;
  activePage: Page;
  onNavigate: (page: Page) => void;
  onUpload: () => void;
}

export default function Layout({ children, activePage, onNavigate, onUpload }: Props) {
  return (
    <>
      <header className="bg-card border-b shadow-sm px-6 py-4">
        <div className="max-w-[960px] mx-auto flex items-center gap-3">
          <button onClick={() => onNavigate('notes')} className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <svg width="24" height="24" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
              <line x1="24" y1="8" x2="12" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="24" y1="8" x2="36" y2="20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="12" y1="20" x2="24" y2="28" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="36" y1="20" x2="24" y2="28" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="12" y1="20" x2="8" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="36" y1="20" x2="40" y2="34" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="24" y1="28" x2="16" y2="40" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="24" y1="28" x2="32" y2="40" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="8" y1="34" x2="16" y2="40" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <line x1="40" y1="34" x2="32" y2="40" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.6"/>
              <circle cx="24" cy="8" r="4" fill="#7c3aed"/>
              <circle cx="12" cy="20" r="3.5" fill="#8b5cf6"/>
              <circle cx="36" cy="20" r="3.5" fill="#8b5cf6"/>
              <circle cx="24" cy="28" r="4.5" fill="#6d28d9"/>
              <circle cx="8" cy="34" r="3" fill="#a78bfa"/>
              <circle cx="40" cy="34" r="3" fill="#a78bfa"/>
              <circle cx="16" cy="40" r="3" fill="#8b5cf6"/>
              <circle cx="32" cy="40" r="3" fill="#8b5cf6"/>
              <circle cx="24" cy="28" r="2" fill="#c4b5fd" opacity="0.8"/>
            </svg>
            <span className="text-xl font-semibold">Cortex</span>
          </button>
          <nav className="ml-8 flex gap-1">
            {(['notes', 'templates'] as const).map((page) => (
              <button
                key={page}
                onClick={() => onNavigate(page)}
                className={cn(
                  'px-3 py-1.5 text-sm font-medium rounded-md transition-colors',
                  activePage === page
                    ? 'bg-primary/10 text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted',
                )}
              >
                {page === 'notes' ? 'Meetings' : 'Templates'}
              </button>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Button size="sm" onClick={onUpload}>
              <Upload className="h-4 w-4 mr-1.5" />
              Upload
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="max-w-[960px] mx-auto mt-8 px-6">{children}</main>
    </>
  );
}
