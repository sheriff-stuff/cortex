import type { ReactNode } from 'react';
import { Separator } from '@/components/ui/separator';

interface Props {
  title: string;
  children: ReactNode;
  showSeparator?: boolean;
}

export default function SummarySection({ title, children, showSeparator = true }: Props) {
  return (
    <>
      {showSeparator && <Separator />}
      <section>
        <h2 className="text-lg font-semibold mb-3">{title}</h2>
        {children}
      </section>
    </>
  );
}
