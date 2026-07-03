import { useState } from "react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { hasPerm, useMe } from "@/entities/session";
import { useBusinesses } from "@/entities/business";
import { useCategories, useCreateTransaction } from "@/entities/transaction";
import { apiErrorOf } from "@/shared/api";
import {
  Button,
  ErrorBanner,
  Field,
  Input,
  Modal,
  Select,
  Tabs,
} from "@/shared/ui";

type Kind = "income" | "expense";

const schema = z
  .object({
    kind: z.enum(["income", "expense"]),
    business: z.string().min(1, "required"),
    category: z.string(),
    amount: z.string().refine((v) => {
      const n = Number(v.replace(",", "."));
      return v.trim() !== "" && !Number.isNaN(n) && n > 0;
    }, "positiveAmount"),
    method: z.enum(["cash", "transfer"]),
    note: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.kind === "expense" && data.category === "") {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["category"],
        message: "categoryRequired",
      });
    }
  });

type FieldErrors = Partial<Record<"business" | "category" | "amount", string>>;

function AddTransactionModal({
  initialKind,
  onClose,
}: {
  initialKind: Kind;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const businesses = useBusinesses();
  const categories = useCategories();
  const create = useCreateTransaction();

  const [kind, setKind] = useState<Kind>(initialKind);
  const [business, setBusiness] = useState("");
  const [category, setCategory] = useState("");
  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<"cash" | "transfer">("cash");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<FieldErrors>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = schema.safeParse({ kind, business, category, amount, method, note });
    if (!parsed.success) {
      const fe = parsed.error.flatten().fieldErrors;
      setErrors({
        business: fe.business ? t("common.required") : undefined,
        amount: fe.amount ? t("common.positiveAmount") : undefined,
        category: fe.category ? t("finance.categoryRequired") : undefined,
      });
      return;
    }
    setErrors({});
    create.mutate(
      {
        business: Number(parsed.data.business),
        kind: parsed.data.kind,
        category: parsed.data.kind === "expense" ? Number(parsed.data.category) : null,
        amount: parsed.data.amount.replace(",", "."),
        method: parsed.data.method,
        note: parsed.data.note.trim() || undefined,
      },
      {
        onSuccess: onClose,
        onError: (err) => setApiError(apiErrorOf(err).message),
      },
    );
  };

  return (
    <Modal
      open
      onClose={onClose}
      title={t(kind === "income" ? "finance.addIncome" : "finance.addExpense")}
    >
      <Tabs
        tabs={[
          { key: "income", label: t("finance.income") },
          { key: "expense", label: t("finance.expense") },
        ]}
        active={kind}
        onChange={(key) => setKind(key as Kind)}
      />
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <Field label={t("common.business")} error={errors.business}>
          <Select value={business} onChange={(e) => setBusiness(e.target.value)}>
            <option value="">—</option>
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        {kind === "expense" && (
          <Field label={t("common.category")} error={errors.category}>
            <Select value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">—</option>
              {(categories.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
        )}
        <Field label={t("common.amount")} error={errors.amount}>
          <Input
            type="text"
            inputMode="decimal"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            autoFocus
          />
        </Field>
        <Field label={t("common.method")}>
          <Select
            value={method}
            onChange={(e) => setMethod(e.target.value as "cash" | "transfer")}
          >
            <option value="cash">{t("method.cash")}</option>
            <option value="transfer">{t("method.transfer")}</option>
          </Select>
        </Field>
        <Field label={t("common.note")}>
          <Input type="text" value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
        <div className="modal__footer">
          <Button variant="ghost" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" disabled={create.isPending}>
            {t("common.save")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Кнопки «Добавить приход/расход» + модалка. Скрыты без finance.manage
 *  (владелец в финансах read-only). */
export function AddTransactionControls() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const [openKind, setOpenKind] = useState<Kind | null>(null);

  if (!hasPerm(me, "finance.manage")) return null;

  return (
    <>
      <Button variant="primary" icon={ArrowUpRight} onClick={() => setOpenKind("income")}>
        {t("finance.addIncome")}
      </Button>
      <Button variant="secondary" icon={ArrowDownRight} onClick={() => setOpenKind("expense")}>
        {t("finance.addExpense")}
      </Button>
      {openKind && (
        <AddTransactionModal initialKind={openKind} onClose={() => setOpenKind(null)} />
      )}
    </>
  );
}
