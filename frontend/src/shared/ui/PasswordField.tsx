import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { useTranslation } from "react-i18next";

type PasswordFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type">;

/** Поле пароля с кнопкой «показать/скрыть». */
export function PasswordField(props: PasswordFieldProps) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);
  const Icon = visible ? EyeOff : Eye;
  return (
    <div style={{ position: "relative", display: "flex" }}>
      <input
        className="input"
        type={visible ? "text" : "password"}
        style={{ flex: 1, paddingRight: 36 }}
        {...props}
      />
      <button
        type="button"
        className="icon-btn"
        style={{ position: "absolute", right: 5, top: "50%", transform: "translateY(-50%)" }}
        aria-label={visible ? t("login.hidePassword") : t("login.showPassword")}
        title={visible ? t("login.hidePassword") : t("login.showPassword")}
        onClick={() => setVisible((v) => !v)}
        tabIndex={-1}
      >
        <Icon size={16} aria-hidden />
      </button>
    </div>
  );
}
