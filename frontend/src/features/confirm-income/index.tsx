import { CheckCircle2 } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useConfirmIncome } from "@/entities/transaction";
import { apiErrorOf } from "@/shared/api";
import { IconButton } from "@/shared/ui";

interface ConfirmIncomeButtonProps {
  transactionId: number;
  /** Ошибки API (в т.ч. 409 «уже подтверждено/аннулировано») поднимаются
   *  наверх — владелец кнопки показывает ErrorBanner. null — сброс. */
  onApiError: (message: string | null) => void;
}

/** Строчное действие «Подтвердить приход» (ФНС-02). */
export function ConfirmIncomeButton({
  transactionId,
  onApiError,
}: ConfirmIncomeButtonProps) {
  const { t } = useTranslation();
  const confirm = useConfirmIncome();

  return (
    <IconButton
      icon={CheckCircle2}
      label={t("finance.confirmIncome")}
      tone="success"
      disabled={confirm.isPending}
      onClick={() => {
        onApiError(null);
        confirm.mutate(transactionId, {
          onError: (err) => onApiError(apiErrorOf(err).message),
        });
      }}
    />
  );
}
