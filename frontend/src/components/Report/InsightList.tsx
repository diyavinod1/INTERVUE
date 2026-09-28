interface InsightListProps {
  title: string;
  items: string[];
  tone: "positive" | "negative" | "neutral";
}
const TONE_STYLES: Record<InsightListProps["tone"], string> = {
  positive: "bg-signal-green",
  negative: "bg-signal-rose",
  neutral: "bg-accent",
};

export function InsightList({ title, items, tone }: InsightListProps) {
  if (items.length === 0) return null;
  return (
    <div className="surface rounded-2xl p-6">
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-4 flex flex-col gap-3">
        {items.map((item, i) => (
          <li key={i} className="flex gap-3 text-sm leading-6 text-ink/75 dark:text-paper/70">
            <span className={`mt-[9px] h-1.5 w-1.5 flex-shrink-0 rounded-full ${TONE_STYLES[tone]}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
