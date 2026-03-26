import type { ReactNode } from 'react';
import ThemeToggle from './ThemeToggle';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="bg-card border-b shadow-sm px-6 py-4">
        <div className="max-w-[960px] mx-auto flex items-center gap-3">
          <span className="text-xl">&#128221;</span>
          <span className="text-xl font-semibold">Meeting Notes</span>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </header>
      <main className="max-w-[960px] mx-auto mt-8 px-6">{children}</main>
    </>
  );
}
