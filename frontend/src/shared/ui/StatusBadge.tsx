import { AlertTriangle, CheckCircle2, Clock, XCircle } from "lucide-react";
import { useTranslation } from "react-i18next";

/** Статусы различаются иконкой + цветом + текстом (не только иконкой). */
const STATUS_META: Record<string, { icon: typeof Clock; tone: string }> = {
  pending: { icon: Clock, tone: "warning" },
  draft: { icon: Clock, tone: "warning" },
  open: { icon: Clock, tone: "info" },
  active: { icon: Clock, tone: "info" },
  confirmed: { icon: CheckCircle2, tone: "success" },
  approved: { icon: CheckCircle2, tone: "success" },
  closed: { icon: CheckCircle2, tone: "success" },
  finalized: { icon: CheckCircle2, tone: "success" },
  completed: { icon: CheckCircle2, tone: "success" },
  void: { icon: XCircle, tone: "muted" },
  rejected: { icon: XCircle, tone: "error" },
  cancelled: { icon: XCircle, tone: "muted" },
  overdue: { icon: AlertTriangle, tone: "error" },
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const meta = STATUS_META[status] ?? { icon: Clock, tone: "muted" };
  const Icon = meta.icon;
  return (
    <span className={`badge badge--${meta.tone}`} data-status={status}>
      <Icon size={13} aria-hidden />
      {t(`status.${status}`, status)}
    </span>
  );
}
