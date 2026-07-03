import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AlertTriangle, Check, Plus, X } from "lucide-react";
import { z } from "zod";

import { useBusinesses } from "@/entities/business";
import { hasPerm, useMe } from "@/entities/session";
import {
  useApproveTransfer,
  useCreateTransfer,
  useRejectTransfer,
  useTransfers,
} from "@/entities/settlements";
import { apiErrorOf } from "@/shared/api";
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

const transferSchema = z
  .object({
    from_business: z.coerce.number().int().positive(),
    to_business: z.coerce.number().int().positive(),
    amount: z.coerce.number().positive(),
    note: z.string(),
  })
  .refine((d) => d.from_business !== d.to_business, {
    path: ["to_business"],
    message: "same_business",
  });

function CreateTransferModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const businesses = useBusinesses();
  const create = useCreateTransfer();
  const [fromBusiness, setFromBusiness] = useState("");
  const [toBusiness, setToBusiness] = useState("");
  const [amount, setAmount] = useState("");
  const [note, setNote] = useState("");
  const [errors, setErrors] = useState<{
    from_business?: string;
    to_business?: string;
    amount?: string;
  }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = transferSchema.safeParse({
      from_business: fromBusiness,
      to_business: toBusiness,
      amount,
      note,
    });
    if (!parsed.success) {
      const fe = parsed.error.flatten().fieldErrors;
      setErrors({
        from_business: fe.from_business ? t("common.required") : undefined,
        to_business: fe.to_business
          ? fe.to_business.includes("same_business")
            ? t("common.error")
            : t("common.required")
          : undefined,
        amount: fe.amount ? t("common.positiveAmount") : undefined,
      });
      return;
    }
    setErrors({});
    create.mutate(
      {
        from_business: parsed.data.from_business,
        to_business: parsed.data.to_business,
        amount: parsed.data.amount.toFixed(2),
        note: parsed.data.note,
      },
      {
        onSuccess: onClose,
        onError: (err) => setApiError(apiErrorOf(err).message),
      },
    );
  };

  return (
    <Modal title={t("settlements.addTransfer")} open onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <ErrorBanner error={apiError} />
        <Field label={t("settlements.fromBusiness")} error={errors.from_business}>
          <Select value={fromBusiness} onChange={(e) => setFromBusiness(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("settlements.toBusiness")} error={errors.to_business}>
          <Select value={toBusiness} onChange={(e) => setToBusiness(e.target.value)}>
            <option value="" />
            {(businesses.data ?? []).map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t("common.amount")} error={errors.amount}>
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
          <Button variant="primary" type="submit" icon={Plus} disabled={create.isPending}>
            {t("common.create")}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** Таблица передач между бизнесами: одобрение/отклонение (RBAC), создание передачи. */
export function TransfersSection() {
  const { t } = useTranslation();
  const me = useMe().data;
  const transfers = useTransfers();
  const approve = useApproveTransfer();
  const reject = useRejectTransfer();
  const [createOpen, setCreateOpen] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const canApprove = hasPerm(me, "settlements.approve");
  const canManage = hasPerm(me, "settlements.manage");

  const onActionError = (err: unknown) => {
    const parsed = apiErrorOf(err);
    setActionError(
      parsed.code === "owner_approval_required"
        ? t("settlements.ownerApprovalRequired")
        : parsed.message,
    );
  };

  if (transfers.isLoading) return <Loading />;
  if (transfers.isError) return <ErrorBanner error={apiErrorOf(transfers.error)} />;
  const rows = transfers.data?.results ?? [];

  return (
    <section>
      <div className="filters-bar">
        {canManage && (
          <Button variant="primary" icon={Plus} onClick={() => setCreateOpen(true)}>
            {t("settlements.addTransfer")}
          </Button>
        )}
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
                <th className="num">{t("common.amount")}</th>
                <th>{t("common.status")}</th>
                <th>{t("common.note")}</th>
                <th>{t("common.date")}</th>
                <th className="num">{t("common.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((tr) => (
                <tr key={tr.id}>
                  <td>{tr.from_business_name}</td>
                  <td>{tr.to_business_name}</td>
                  <td className="num">
                    <Money value={tr.amount} />
                  </td>
                  <td>
                    <span style={{ display: "inline-flex", gap: 6, flexWrap: "wrap" }}>
                      <StatusBadge status={tr.status} />
                      {tr.requires_owner_approval && (
                        <span className="badge badge--warning">
                          <AlertTriangle size={13} aria-hidden />
                          {t("settlements.requiresOwner")}
                        </span>
                      )}
                    </span>
                  </td>
                  <td>{tr.note}</td>
                  <td>{new Date(tr.created_at).toLocaleDateString("ru-RU")}</td>
                  <td>
                    <span className="row-actions">
                      {tr.status === "pending" && canApprove && (
                        <>
                          <IconButton
                            icon={Check}
                            tone="success"
                            label={t("settlements.approveTransfer")}
                            disabled={approve.isPending || reject.isPending}
                            onClick={() => {
                              setActionError(null);
                              approve.mutate(tr.id, { onError: onActionError });
                            }}
                          />
                          <IconButton
                            icon={X}
                            tone="danger"
                            label={t("settlements.rejectTransfer")}
                            disabled={approve.isPending || reject.isPending}
                            onClick={() => {
                              setActionError(null);
                              reject.mutate(tr.id, { onError: onActionError });
                            }}
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
      {createOpen && <CreateTransferModal onClose={() => setCreateOpen(false)} />}
    </section>
  );
}
