import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LogIn } from "lucide-react";
import { z } from "zod";

import { homeRoute, useLogin } from "@/entities/session";
import { apiErrorOf } from "@/shared/api";
import { Button, ErrorBanner, Field, Input } from "@/shared/ui";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

export function LoginForm() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [apiError, setApiError] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    setApiError(null);
    const parsed = schema.safeParse({ email, password });
    if (!parsed.success) {
      const fieldErrors = parsed.error.flatten().fieldErrors;
      setErrors({
        email: fieldErrors.email ? t("common.required") : undefined,
        password: fieldErrors.password ? t("common.required") : undefined,
      });
      return;
    }
    setErrors({});
    login.mutate(parsed.data, {
      onSuccess: (me) => navigate(homeRoute(me), { replace: true }),
      onError: (err) => {
        const parsedErr = apiErrorOf(err);
        setApiError(
          parsedErr.code === "not_authenticated" || parsedErr.code === "error"
            ? t("auth.invalidCredentials")
            : parsedErr.message,
        );
      },
    });
  };

  return (
    <form onSubmit={submit} noValidate>
      <ErrorBanner error={apiError} />
      <Field label={t("auth.email")} error={errors.email}>
        <Input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          autoComplete="username"
          autoFocus
        />
      </Field>
      <Field label={t("auth.password")} error={errors.password}>
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
      </Field>
      <Button
        variant="primary"
        type="submit"
        icon={LogIn}
        disabled={login.isPending}
        style={{ width: "100%", justifyContent: "center" }}
      >
        {t("auth.submit")}
      </Button>
    </form>
  );
}
