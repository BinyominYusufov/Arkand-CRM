import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowLeftRight, ArrowRight, Handshake } from "lucide-react";
import { z } from "zod";

import { useBusinesses } from "@/entities/business";
import { useDebtsRegistry, useNetDebts } from "@/entities/settlements";
import { CloseDebtModal, type CloseDebtTarget } from "@/features/close-debt";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  IconButton,
  Loading,
  Modal,
  Money,
  Select,
  StatusBadge,
} from "@/shared/ui";

const nettingSchema = z
  .object({
    business_a: z.coerce.number().int().positive(),
    business_b: z.coerce.number().int().positive(),
  })
  .refine((d) => d.business_a !== d.business_b, {
    path: ["business_b"],
    message: "same_business",
  });

/** Модалка неттинга: взаимозачёт встречных долгов между двумя бизнесами. */
function NettingModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const businesses = useBusinesses();
  const net = useNetDebts();
  const [businessA, setBusinessA] = useState("");
  const [businessB, setBusinessB] = useState("");
  const [errors, setErrors] = useState<{ business_a?: string; business_b?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = nettingSchema.safeParse({ business_a: businessA, business_b: businessB });
    if (!parsed.success) {
      const fe = parsed.error.flatten().fieldErrors;
      setErrors({
        business_a: fe.business_a ? t("common.required") : undefined,
        business_b: fe.business_b
          ? fe.business_b.includes("same_business")
            ? t("common.error")
            : t("common.required")
          : undefined,
      });
      return;
    }
    setErrors({});
    net.mutate(parsed.data, {
      onSuccess: onClose,
      onError: (err) => setApiError(apiErrorOf(err).message),
    });
  };

  return (
    <Modal title={t("settlements.netting")} open onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <Field label={t("settlements.debtor")} error={errors.business_a}>
          <Select value={businessA} onChange={(e) => setBusinessA(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("settlements.creditor")} error={errors.business_b}>
          <Select value={businessB} onChange={(e) => setBusinessB(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="primary"
            type="submit"
            icon={ArrowLeftRight}
            disabled={net.isPending}
          >
            {t("settlements.runNetting")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Реестр долгов: сводка «кто кому должен», таблица открытых долгов, неттинг. */
export function DebtRegistry() {
  const { t } = useTranslation();
  const registry = useDebtsRegistry();
  const [closing, setClosing] = useState<CloseDebtTarget | null>(null);
  const [nettingOpen, setNettingOpen] = useState(false);

  if (registry.isLoading) return <Loading />;
  if (registry.isError) return <ErrorBanner error={apiErrorOf(registry.error)} />;
  const data = registry.data;
  if (!data) return <EmptyState />;

  return (
    <section>
      <div className="filters-bar">
        <Button icon={ArrowLeftRight} onClick={() => setNettingOpen(true)}>
          {t("settlements.runNetting")}
        </Button>
      </div>

      <div className="kpi-grid">
        <Card title={t("settlements.openDebtsTotal")}>
          <div className="kpi-value">
            <Money value={data.total_open} direction="out" withSign />
          </div>
        </Card>
      </div>

      <Card title={t("settlements.whoOwes")}>
        {data.pairs.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="tbl-wrap" style={{ border: "none" }}>
            <table className="tbl">
              <thead>
                <tr>
                  <th>{t("settlements.debtor")}</th>
                  <th aria-hidden />
                  <th>{t("settlements.creditor")}</th>
                  <th className="num">{t("settlements.remaining")}</th>
                  <th className="num">{t("settlements.debts")}</th>
                </tr>
              </thead>
              <tbody>
                {data.pairs.map((p) => (
                  <tr key={`${p.debtor_id}-${p.creditor_id}`}>
                    <td>{p.debtor_name}</td>
                    <td>
                      <ArrowRight size={16} aria-hidden color="var(--text-muted)" />
                    </td>
                    <td>{p.creditor_name}</td>
                    <td className="num">
                      <Money value={p.total_remaining} direction="out" withSign />
                    </td>
                    <td className="num">{p.debts_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <h2 className="section-title">{t("settlements.debts")}</h2>
      {data.debts.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("settlements.debtor")}</th>
                <th>{t("settlements.creditor")}</th>
                <th className="num">{t("common.amount")}</th>
                <th className="num">{t("settlements.remaining")}</th>
                <th>{t("common.date")}</th>
                <th>{t("common.status")}</th>
                <th className="num">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {data.debts.map((d) => (
                <tr key={d.id}>
                  <td>{d.debtor_name}</td>
                  <td>{d.creditor_name}</td>
                  <td className="num">{formatMoney(d.amount)}</td>
                  <td className="num">
                    <Money value={d.remaining} direction="out" withSign />
                  </td>
                  <td>{new Date(d.created_at).toLocaleDateString("ru-RU")}</td>
                  <td>{d.is_overdue && <StatusBadge status="overdue" />}</td>
                  <td>
                    <span className="row-actions">
                      <IconButton
                        icon={Handshake}
                        label={t("settlements.closeDebt")}
                        onClick={() =>
                          setClosing({
                            id: d.id,
                            debtor_name: d.debtor_name,
                            creditor_name: d.creditor_name,
                            remaining: d.remaining,
                          })
                        }
                      />
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {closing && <CloseDebtModal debt={closing} onClose={() => setClosing(null)} />}
      {nettingOpen && <NettingModal onClose={() => setNettingOpen(false)} />}
    </section>
  );
}
