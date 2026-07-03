import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ArrowRight, Handshake } from "lucide-react";
import { z } from "zod";

import { useSettleDebt } from "@/entities/settlements";
import { apiErrorOf } from "@/shared/api";
import { Button, ErrorBanner, Field, Input, Modal, Money, Select } from "@/shared/ui";

/** Минимум данных о долге для модалки (совместим с Debt и DebtsRegistry.debts). */
export interface CloseDebtTarget {
  id: number;
  debtor_name: string;
  creditor_name: string;
  remaining: string;
}

const schema = z.object({
  method: z.enum(["offset", "return"]),
  amount: z
    .string()
    .refine((v) => v === "" || Number.parseFloat(v) > 0, { message: "positive" }),
  note: z.string(),
});

/** Модалка погашения долга: метод offset/return, частичная сумма (пусто — весь остаток). */
export function CloseDebtModal({
  debt,
  onClose,
}: {
  debt: CloseDebtTarget;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const settle = useSettleDebt();
  const [method, setMethod] = useState<"offset" | "return">("offset");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<{ amount?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = schema.safeParse({ method, amount, note });
    if (!parsed.success) {
      setErrors({ amount: t("common.positiveAmount") });
      return;
    }
    setErrors({});
    settle.mutate(
      {
        id: debt.id,
        method: parsed.data.method,
        amount: parsed.data.amount || undefined,
        note: parsed.data.note,
      },
      {
        onSuccess: onClose,
        onError: (err) => setApiError(apiErrorOf(err).message),
      },
    );
  };

  return (
    <Modal title={t("settlements.closeDebt")} open onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 12,
            fontSize: 13,
          }}
        >
          <span>{debt.debtor_name}</span>
          <ArrowRight size={16} aria-hidden color="var(--text-muted)" />
          <span>{debt.creditor_name}</span>
          <span style={{ marginLeft: "auto" }}>
            <Money value={debt.remaining} direction="out" withSign />
          </span>
        </div>
        <Field label={t("settlements.settleMethod")}>
          <Select
            value={method}
            onChange={(e) => setMethod(e.target.value as "offset" | "return")}
          >
            <option value="offset">{t("settlements.offset")}</option>
            <option value="return">{t("settlements.return")}</option>
          </Select>
        </Field>
        <Field label={t("settlements.partialAmount")} error={errors.amount}>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </Field>
        <Field label={t("common.note")}>
          <Input value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="primary"
            type="submit"
            icon={Handshake}
            disabled={settle.isPending}
          >
            {t("settlements.closeDebt")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
