import type {ReactNode} from "react";
export function Panel({children, className = "", label}: {children: ReactNode; className?: string; label?: string}) {
  return <section className={`nf-panel ${className}`} aria-label={label}>{children}</section>;
}
export function EmptyState({title, description, children}: {title: string; description: string; children?: ReactNode}) {
  return <div className="nf-empty"><strong>{title}</strong><p>{description}</p>{children}</div>;
}
