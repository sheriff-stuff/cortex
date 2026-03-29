import { Fragment } from 'react';
import type { Topic, Decision, ActionItem, Question } from '@/types';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import {
  CheckCircle,
  Square,
  HelpCircle,
  MessageCircle,
  AlertCircle,
  ChevronRight,
} from 'lucide-react';
import SummarySection from './SummarySection';

interface Props {
  overview?: string;
  keywords?: string[];
  topics: Topic[];
  decisions: Decision[];
  actionItems: ActionItem[];
  questions: Question[];
  apply: (text: string) => string;
}

export default function SummaryTab({ overview, keywords, topics, decisions, actionItems, questions, apply }: Props) {
  const overviewText = overview
    ? apply(overview)
    : topics.length > 0
      ? topics.slice(0, 3).map((t) => apply(t.description)).join(' ')
      : null;

  return (
    <div className="space-y-6 pt-4">
      {/* Overview */}
      {overviewText && (
        <section>
          <h2 className="text-lg font-semibold mb-2">Overview</h2>
          <p className="text-sm text-muted-foreground leading-relaxed">{overviewText}</p>
        </section>
      )}

      {/* Outline */}
      {topics.length > 0 && (
        <SummarySection title="Outline" showSeparator={!!overviewText}>
          <div>
            {topics.map((topic, i) => {
              const points = topic.key_points && topic.key_points.length > 0
                ? topic.key_points
                : topic.description ? [topic.description] : [];
              return (
                <Collapsible key={i} defaultOpen>
                  <CollapsibleTrigger className="flex items-center gap-2 w-full py-2 text-left cursor-pointer hover:bg-muted/50 rounded-md px-1 -mx-1 transition-colors group">
                    <ChevronRight className="h-4 w-4 shrink-0 transition-transform group-data-[panel-open]:rotate-90" />
                    <span className="font-medium text-sm">{topic.title}</span>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <ul className="list-disc ml-8 mb-2 space-y-1">
                      {points.map((point, j) => (
                        <li key={j} className="text-sm text-muted-foreground leading-relaxed">
                          {apply(point)}
                        </li>
                      ))}
                    </ul>
                  </CollapsibleContent>
                </Collapsible>
              );
            })}
          </div>
        </SummarySection>
      )}

      {/* Action Items */}
      {actionItems.length > 0 && (
        <SummarySection title="Action Items">
          <ul className="space-y-2">
            {actionItems.map((a, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <Square className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm">{a.task}</div>
                  {a.detail && (
                    <div className="text-sm text-muted-foreground mt-0.5">{apply(a.detail)}</div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </SummarySection>
      )}

      {/* Decisions */}
      {decisions.length > 0 && (
        <SummarySection title="Decisions">
          <ul className="space-y-2">
            {decisions.map((d, i) => (
              <li key={i} className="flex items-start gap-2.5">
                <CheckCircle className="h-4 w-4 text-success mt-0.5 shrink-0" />
                <div>
                  <div className="text-sm">{d.decision}</div>
                  {d.detail && (
                    <div className="text-sm text-muted-foreground mt-0.5">{apply(d.detail)}</div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </SummarySection>
      )}

      {/* Questions & Answers */}
      {questions.length > 0 && (
        <SummarySection title="Questions & Answers">
          <div className="space-y-4">
            {questions.map((q, i) => (
              <Fragment key={i}>
                {i > 0 && <Separator />}
                <div className="space-y-2">
                  <div className="flex items-start gap-2">
                    <HelpCircle className="h-4 w-4 text-warning mt-0.5 shrink-0" />
                    <div>
                      <div className="text-sm font-medium">{q.question}</div>
                      {q.attribution && (
                        <div className="text-xs text-muted-foreground mt-0.5">{apply(q.attribution)}</div>
                      )}
                    </div>
                  </div>
                  {q.answer ? (
                    <div className="flex items-start gap-2 ml-6">
                      <MessageCircle className="h-3.5 w-3.5 text-green-500 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-sm">{apply(q.answer)}</div>
                        {q.answer_attribution && (
                          <div className="text-xs text-muted-foreground mt-0.5">{apply(q.answer_attribution)}</div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 ml-6">
                      <AlertCircle className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <span className="text-sm text-muted-foreground italic">Unanswered</span>
                    </div>
                  )}
                </div>
              </Fragment>
            ))}
          </div>
        </SummarySection>
      )}

      {/* Keywords */}
      {keywords && keywords.length > 0 && (
        <SummarySection title="Keywords">
          <div className="flex flex-wrap gap-1.5">
            {keywords.map((kw, i) => (
              <span
                key={i}
                className="inline-block rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                {kw}
              </span>
            ))}
          </div>
        </SummarySection>
      )}
    </div>
  );
}
