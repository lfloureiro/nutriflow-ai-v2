import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

import "./ContextDrawer.css";

type ContextDrawerProps = {
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
  /** Return false to keep the drawer open (e.g. when a draft cannot be discarded). */
  onRequestClose: () => boolean | void;
  closeLabel?: string;
};

const FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

export default function ContextDrawer({
  title,
  children,
  footer,
  wide = false,
  onRequestClose,
  closeLabel = "Fechar",
}: ContextDrawerProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onRequestClose);
  onCloseRef.current = onRequestClose;

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    // The drawer is portaled outside #root, so the rest of the app is not interactive.
    const appRoot = document.getElementById("root");
    const wasInert = appRoot?.inert ?? false;
    if (appRoot) appRoot.inert = true;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const candidates = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE))
        .filter((element) => element.getClientRects().length > 0 && !element.closest("[inert]"));
      if (!candidates.length) {
        event.preventDefault();
        panelRef.current.focus();
        return;
      }
      const first = candidates[0]!;
      const last = candidates[candidates.length - 1]!;
      if (event.shiftKey && (document.activeElement === first || document.activeElement === panelRef.current || !panelRef.current.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !panelRef.current.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      if (appRoot) appRoot.inert = wasInert;
      previousFocus?.focus();
    };
  }, []);

  return createPortal(
    <div className="nf-context-overlay">
      <section
        ref={panelRef}
        className={`nf-context-drawer${wide ? " nf-context-drawer--wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <header className="nf-context-drawer__head">
          <h2 id={titleId}>{title}</h2>
          <button
            ref={closeRef}
            className="nf-context-drawer__close"
            type="button"
            aria-label={closeLabel}
            onClick={() => onCloseRef.current()}
          >
            ×
          </button>
        </header>
        <div className="nf-context-drawer__body">{children}</div>
        {footer ? <footer className="nf-context-drawer__foot">{footer}</footer> : null}
      </section>
    </div>,
    document.body,
  );
}
