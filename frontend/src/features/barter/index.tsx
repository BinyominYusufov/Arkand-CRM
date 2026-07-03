import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Check, Handshake, Plus, X } from "lucide-react";
import { z } from "zod";

import { useBusinesses } from "@/entities/business";
import { useMe } from "@/entities/session";
import {
  useBarterAction,
  useBarters,
  useCreateBarter,
  useDebts,
  type Barter,
} from "@/entities/settlements";
import { apiErrorOf } from "@/shared/api";
import { formatMoney } from "@/shared/lib/money";
import {
  Button,
  EmptyState,
  ErrorBanner,
  Field,
  IconButton,
  Input,
  Loading,
  Modal,
  Money,
  Select,
  StatusBadge,
} from "@/shared/ui";

const barterSchema = z
  .object({
    business_a: z.coerce.number().int().positive(),
    business_b: z.coerce.number().int().positive(),
    description: z.string().min(1),
    value: z.coerce.number().positive(),
  })
  .refine((d) => d.business_a !== d.business_b, {
    path: ["business_b"],
    message: "same_business",
  });

function CreateBarterModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const me = useMe().data;
  const businesses = useBusinesses();
  const create = useCreateBarter();
  const [businessA, setBusinessA] = useState("");
  const [businessB, setBusinessB] = useState("");
  const [description, setDescription] = useState("");
  const [value, setValue] = useState("");
  const [errors, setErrors] = useState<{
    business_a?: string;
    business_b?: string;
    description?: string;
    value?: string;
  }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = barterSchema.safeParse({
      business_a: businessA,
      business_b: businessB,
      description,
      value,
    });
    if (!parsed.success) {
      const fe = parsed.error.flatten().fieldErrors;
      setErrors({
        business_a: fe.business_a ? t("common.required") : undefined,
        business_b: fe.business_b
          ? fe.business_b.includes("same_business")
            ? t("common.error")
            : t("common.required")
          : undefined,
        description: fe.description ? t("common.required") : undefined,
        value: fe.value ? t("common.positiveAmount") : undefined,
      });
      return;
    }
    if (!me) return;
    setErrors({});
    create.mutate(
      {
        business_a: parsed.data.business_a,
        business_b: parsed.data.business_b,
        description: parsed.data.description,
        value: parsed.data.value.toFixed(2),
        // Контролирующий бухгалтер — текущий пользователь (поле скрыто).
        controlled_by: me.id,
      },
      {
        onSuccess: onClose,
        onError: (err) => setApiError(apiErrorOf(err).message),
      },
    );
  };

  return (
    <Modal title={t("settlements.addBarter")} open onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <Field label={t("settlements.fromBusiness")} error={errors.business_a}>
          <Select value={businessA} onChange={(e) => setBusinessA(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("settlements.toBusiness")} error={errors.business_b}>
          <Select value={businessB} onChange={(e) => setBusinessB(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("settlements.description")} error={errors.description}>
          <Input value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
        <Field label={t("settlements.value")} error={errors.value}>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </Field>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="primary"
            type="submit"
            icon={Plus}
            disabled={create.isPending || !me}
          >
            {t("common.create")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Закрытие долга бартером: выбор открытого долга между теми же двумя бизнесами. */
function CloseDebtWithBarterModal({
  barter,
  onClose,
}: {
  barter: Barter;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const debts = useDebts({ status: "open" });
  const action = useBarterAction();
  const [debtId, setDebtId] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [apiError, setApiError] = useState<string | null>(null);

  const samePair = (debts.data?.results ?? []).filter(
    (d) =>
      (d.debtor === barter.business_a && d.creditor === barter.business_b) ||
      (d.debtor === barter.business_b && d.creditor === barter.business_a),
  );

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    if (!debtId) {
      setError(t("common.required"));
      return;
    }
    setError(undefined);
    action.mutate(
      { id: barter.id, action: "close-debt", debt: Number(debtId) },
      {
        onSuccess: onClose,
        onError: (err) => setApiError(apiErrorOf(err).message),
      },
    );
  };

  return (
    <Modal title={t("settlements.closeDebtWithBarter")} open onClose={onClose}>
      {debts.isLoading ? (
        <Loading />
      ) : samePair.length === 0 ? (
        <EmptyState />
      ) : (
        <form onSubmit={submit} noValidate>
          <ErrorBanner error={apiError} />
          <Field label={t("settlements.debt")} error={error}>
            <Select value={debtId} onChange={(e) => setDebtId(e.target.value)}>
              <option value="" />
              {samePair.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.debtor_name} — {d.creditor_name} · {formatMoney(d.remaining)}
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
              icon={Handshake}
              disabled={action.isPending}
            >
              {t("settlements.closeDebt")}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  );
}

/** Бартерные сделки: таблица, создание, завершение/отмена, закрытие долга бартером. */
export function BarterSection() {
  const { t } = useTranslation();
  const barters = useBarters();
  const action = useBarterAction();
  const [createOpen, setCreateOpen] = useState(false);
  const [closingFor, setClosingFor] = useState<Barter | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const run = (id: number, kind: "complete" | "cancel") => {
    setActionError(null);
    action.mutate(
      { id, action: kind },
      { onError: (err) => setActionError(apiErrorOf(err).message) },
    );
  };

  if (barters.isLoading) return <Loading />;
  if (barters.isError) return <ErrorBanner error={apiErrorOf(barters.error)} />;
  const rows = barters.data?.results ?? [];

  return (
    <section>
      <div className="filters-bar">
        <Button variant="primary" icon={Plus} onClick={() => setCreateOpen(true)}>
          {t("settlements.addBarter")}
        </Button>
      </div>
      <ErrorBanner error={actionError} />
      {rows.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="tbl-wrap">
          <table className="tbl">
            <thead>
              <tr>
                <th>{t("settlements.fromBusiness")}</th>
                <th>{t("settlements.toBusiness")}</th>
                <th>{t("settlements.description")}</th>
                <th className="num">{t("settlements.value")}</th>
                <th>{t("settlements.controlledBy")}</th>
                <th>{t("common.status")}</th>
                <th className="num">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((b) => (
                <tr key={b.id}>
                  <td>{b.business_a_name}</td>
                  <td>{b.business_b_name}</td>
                  <td>{b.description}</td>
                  <td className="num">
                    <Money value={b.value} />
                  </td>
                  <td>{b.controlled_by_name}</td>
                  <td>
                    <StatusBadge status={b.status} />
                  </td>
                  <td>
                    <span className="row-actions">
                      {b.status === "active" && (
                        <>
                          <IconButton
                            icon={Check}
                            tone="success"
                            label={t("settlements.completeBarter")}
                            disabled={action.isPending}
                            onClick={() => run(b.id, "complete")}
                          />
                          <IconButton
                            icon={X}
                            tone="danger"
                            label={t("settlements.cancelBarter")}
                            disabled={action.isPending}
                            onClick={() => run(b.id, "cancel")}
                          />
                          <IconButton
                            icon={Handshake}
                            label={t("settlements.closeDebtWithBarter")}
                            onClick={() => setClosingFor(b)}
                          />
                        </>
                      )}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {createOpen && <CreateBarterModal onClose={() => setCreateOpen(false)} />}
      {closingFor && (
        <CloseDebtWithBarterModal barter={closingFor} onClose={() => setClosingFor(null)} />
      )}
    </section>
  );
}
