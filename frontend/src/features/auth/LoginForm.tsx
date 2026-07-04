import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LogIn } from "lucide-react";
import axios from "axios";
import { z } from "zod";

import { homeRoute, useLogin } from "@/entities/session";
import { Field, Input, PasswordField } from "@/shared/ui";

/** Значения для подстановки из панели «Демо-доступ» (nonce — на повторный клик). */
export interface LoginPrefill {
  email: string;
  password: string;
  nonce: number;
}

const schema = z.object({
  email: z.string().min(1, "required").email("invalidEmail"),
  password: z.string().min(1, "required"),
});

export function LoginForm({ prefill }: { prefill?: LoginPrefill }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useLogin();
  const emailRef = useRef<HTMLInputElement>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<{ email?: string; password?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  // Клик по демо-аккаунту заполняет поля и ставит фокус в email (§3.5).
  useEffect(() => {
    if (!prefill) return;
    setEmail(prefill.email);
    setPassword(prefill.password);
    setFieldError({});
    setApiError(null);
    emailRef.current?.focus();
  }, [prefill]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (login.isPending) return;
    setApiError(null);

    const parsed = schema.safeParse({ email: email.trim(), password });
    if (!parsed.success) {
      const fe = parsed.error.flatten().fieldErrors;
      setFieldError({
        email: fe.email ? t(`login.errors.${fe.email[0]}`) : undefined,
        password: fe.password ? t(`login.errors.${fe.password[0]}`) : undefined,
      });
      emailRef.current?.focus();
      return;
    }
    setFieldError({});

    login.mutate(parsed.data, {
      onSuccess: (me) => navigate(homeRoute(me), { replace: true }),
      onError: (err) => {
        const isAuthFail = axios.isAxiosError(err) && err.response?.status === 401;
        setApiError(
          isAuthFail ? t("login.errors.invalidCredentials") : t("login.errors.network"),
        );
        emailRef.current?.focus();
      },
    });
  };

  return (
    <form onSubmit={submit} noValidate className="login-form">
      <Field label={t("login.email")} error={fieldError.email}>
        <Input
          ref={emailRef}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          disabled={login.isPending}
          autoFocus
        />
      </Field>
      <Field label={t("login.password")} error={fieldError.password}>
        <PasswordField
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          disabled={login.isPending}
          aria-label={t("login.password")}
        />
      </Field>

      {apiError && (
        <div className="login-form__error" role="alert">
          {apiError}
        </div>
      )}

      <button type="submit" className="login-form__submit" disabled={login.isPending}>
        {login.isPending ? (
          <>
            <span className="login-form__spinner" aria-hidden />
            {t("login.submitting")}
          </>
        ) : (
          <>
            <LogIn size={16} aria-hidden />
            {t("login.submit")}
          </>
        )}
      </button>
    </form>
  );
}
