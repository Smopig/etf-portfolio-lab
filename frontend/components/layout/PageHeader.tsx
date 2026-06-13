export interface PageHeaderProps {
  title: string;
  subtitle: string;
  actions?: React.ReactNode;
}

export default function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="mb-space-8 flex flex-wrap items-start justify-between gap-space-4">
      <div>
        <h1 className="text-display text-text-primary">{title}</h1>
        <p className="mt-space-1 text-body text-text-secondary">{subtitle}</p>
      </div>
      {actions && <div className="flex items-center gap-space-2">{actions}</div>}
    </div>
  );
}
