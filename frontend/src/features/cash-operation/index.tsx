import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { z } from "zod";

import {
  useCreateCashOperation,
  type CashRegister,
} from "@/entities/cash-register";
import { apiErrorOf } from "@/shared/api";
import { moneyColor } from "@/shared/lib/money";
import { Button, ErrorBanner, Field, Input, Modal, Select } from "@/shared/ui";

const schema = z.object({
  register: z.number().int().positive(),
  direction: z.enum(["in", "out"]),
  method: z.enum(["cash", "transfer"]),
  amount: z.number().positive(),
  note: z.string(),
});

type Direction = "in" | "out";
type Method = "cash" | "transfer";

interface CashOperationModalProps {
  open: boolean;
  onClose: () => void;
  /** Доступные пользователю кассы (бэкенд уже изолирует по членству). */
  registers: CashRegister[];
}

/** Модалка «Добавить операцию» по кассе: направление, способ, сумма, примечание. */
export function CashOperationModal({
  open,
  onClose,
  registers,
}: CashOperationModalProps) {
  const { t } = useTranslation();
  const createOp = useCreateCashOperation();
  const [register, setRegister] = useState("");
  const [direction, setDirection] = useState<Direction>("in");
  const [method, setMethod] = useState<Method>("cash");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<{ register?: string; amount?: string }>(
    {},
  );
  const [apiError, setApiError] = useState<string | null>(null);

  const reset = () => {
    setRegister("");
    setDirection("in");
    setMethod("cash");
    setAmount("");
    setNote("");
    setErrors({});
    setApiError(null);
  };

  const close = () => {
    reset();
    onClose();
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = schema.safeParse({
      register: register === "" ? 0 : Number(register),
      direction,
      method,
      amount: amount === "" ? 0 : Number(amount),
      note,
    });
    if (!parsed.success) {
      const fieldErrors = parsed.error.flatten().fieldErrors;
      setErrors({
        register: fieldErrors.register ? t("common.required") : undefined,
        amount: fieldErrors.amount ? t("common.positiveAmount") : undefined,
      });
      return;
    }
    setErrors({});
    createOp.mutate(
      {
        register: parsed.data.register,
        direction: parsed.data.direction,
        method: parsed.data.method,
        amount: String(parsed.data.amount),
        note: parsed.data.note || undefined,
      },
      {
        onSuccess: close,
        onError: (err) => {
          const apiErr = apiErrorOf(err);
          const base =
            apiErr.code === "cash_limit_exceeded"
              ? t("cash.limitError")
              : apiErr.code === "insufficient_funds"
                ? t("cash.insufficientFunds")
                : apiErr.message;
          const details = apiErr.details
            ? Object.entries(apiErr.details)
                .map(([key, value]) => `${key}: ${String(value)}`)
                .join(", ")
            : "";
          setApiError(details ? `${base} (${details})` : base);
        },
      },
    );
  };

  const directionOptions: { value: Direction; label: string }[] = [
    { value: "in", label: t("cash.in") },
    { value: "out", label: t("cash.out") },
  ];

  return (
    <Modal title={t("cash.addOperation")} open={open} onClose={close}>
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <Field label={t("cash.register")} error={errors.register}>
          <Select
            value={register}
            onChange={(e) => setRegister(e.target.value)}
          >
            <option value="">—</option>
            {registers.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} · {r.business_name}
              </option>
            ))}
          </Select>
        </Field>
        <div className="field">
          <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-muted)" }}>
            {t("cash.direction")}
          </span>
          <div
            role="radiogroup"
            aria-label={t("cash.direction")}
            style={{ display: "flex", gap: 16 }}
          >
            {directionOptions.map((opt) => {
              const Icon = opt.value === "in" ? ArrowUpRight : ArrowDownRight;
              return (
                <label
                  key={opt.value}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 13,
                    color: "var(--text)",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="direction"
                    value={opt.value}
                    checked={direction === opt.value}
                    onChange={() => setDirection(opt.value)}
                  />
                  <Icon
                    size={16}
                    aria-hidden
                    style={{ color: moneyColor(opt.value) }}
                  />
                  {opt.label}
                </label>
              );
            })}
          </div>
        </div>
        <Field label={t("common.method")}>
          <Select
            value={method}
            onChange={(e) => setMethod(e.target.value as Method)}
          >
            <option value="cash">{t("method.cash")}</option>
            <option value="transfer">{t("method.transfer")}</option>
          </Select>
        </Field>
        <Field label={t("common.amount")} error={errors.amount}>
          <Input
            type="number"
            inputMode="decimal"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
        </Field>
        <Field label={t("common.note")}>
          <Input value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <div className="modal__footer">
          <Button variant="ghost" onClick={close} disabled={createOp.isPending}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" disabled={createOp.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
