import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { isAxiosError } from "axios";
import { Play } from "lucide-react";
import { z } from "zod";

import { useRunPayroll, type PayrollRun } from "@/entities/payroll";
import { apiErrorOf } from "@/shared/api";
import { Button, ErrorBanner, Field, Input, Modal, Select } from "@/shared/ui";

const schema = z.object({
  year: z.coerce.number().int().min(2000).max(2100),
  month: z.coerce.number().int().min(1).max(12),
});

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

/** Кнопка + модалка запуска расчёта зарплаты за период (год/месяц). */
export function RunPayrollButton({
  onCreated,
}: {
  onCreated?: (run: PayrollRun) => void;
}) {
  const { t } = useTranslation();
  const runPayroll = useRunPayroll();
  const now = new Date();
  const [open, setOpen] = useState(false);
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1));
  const [errors, setErrors] = useState<{ year?: string; month?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const close = () => {
    setOpen(false);
    setErrors({});
    setApiError(null);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = schema.safeParse({ year, month });
    if (!parsed.success) {
      const fieldErrors = parsed.error.flatten().fieldErrors;
      setErrors({
        year: fieldErrors.year ? t("common.required") : undefined,
        month: fieldErrors.month ? t("common.required") : undefined,
      });
      return;
    }
    setErrors({});
    runPayroll.mutate(parsed.data, {
      onSuccess: (run) => {
        close();
        onCreated?.(run);
      },
      onError: (err) => {
        setApiError(
          isAxiosError(err) && err.response?.status === 409
            ? t("payroll.alreadyFinalized")
            : apiErrorOf(err).message,
        );
      },
    });
  };

  return (
    <>
      <Button variant="primary" icon={Play} onClick={() => setOpen(true)}>
        {t("payroll.runPayroll")}
      </Button>
      <Modal title={t("payroll.runPayroll")} open={open} onClose={close}>
        <form onSubmit={submit} noValidate>
          <ErrorBanner error={apiError} />
          <Field label={t("payroll.year")} error={errors.year}>
            <Input
              type="number"
              min={2000}
              max={2100}
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </Field>
          <Field label={t("payroll.month")} error={errors.month}>
            <Select value={month} onChange={(e) => setMonth(e.target.value)}>
              {MONTHS.map((m) => (
                <option key={m} value={m}>
                  {String(m).padStart(2, "0")}
                </option>
              ))}
            </Select>
          </Field>
          <div className="modal__footer">
            <Button onClick={close}>{t("common.cancel")}</Button>
            <Button
              variant="primary"
              type="submit"
              icon={Play}
              disabled={runPayroll.isPending}
            >
              {t("common.create")}
            </Button>
          </div>
        </form>
      </Modal>
    </>
  );
}
