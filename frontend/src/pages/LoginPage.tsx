import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { resolveLoginSubtitle } from "../branding";
import LoginLayout from "../components/LoginLayout";
import { useLocale, useStrings } from "../hooks/useLocale";
import { LOCALE_DEFINITIONS, LOCALES, type Locale } from "../i18n";

type LoginPageProps = {
  onSuccess: () => void;
};

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const strings = useStrings();
  const { locale, setLocale } = useLocale();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const login = useMutation({
    mutationFn: () => api.login(email, password),
    onSuccess: () => onSuccess(),
  });

  return (
    <LoginLayout>
      <Stack spacing={2}>
        <FormControl size="small" sx={{ alignSelf: "flex-end", minWidth: 140 }}>
          <InputLabel id="login-locale-label">{strings.locale.language}</InputLabel>
          <Select
            labelId="login-locale-label"
            label={strings.locale.language}
            value={locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
          >
            {LOCALES.map((code) => (
              <MenuItem key={code} value={code}>
                {LOCALE_DEFINITIONS[code].label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="h5">{strings.auth.title}</Typography>
        <Typography variant="body2" color="text.secondary">
          {resolveLoginSubtitle(strings.auth.subtitle)}
        </Typography>
        {login.isError && (
          <Alert severity="error">
            {login.error instanceof Error ? login.error.message : strings.auth.loginFailed}
          </Alert>
        )}
        <Box
          component="form"
          onSubmit={(event) => {
            event.preventDefault();
            login.mutate();
          }}
        >
          <Stack spacing={2}>
            <TextField
              label={strings.auth.email}
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="username"
              required
              fullWidth
              size="small"
            />
            <TextField
              label={strings.auth.password}
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
              fullWidth
              size="small"
            />
            <Button
              type="submit"
              variant="contained"
              disabled={login.isPending}
              fullWidth
            >
              {login.isPending ? <CircularProgress size={24} color="inherit" /> : strings.auth.signIn}
            </Button>
          </Stack>
        </Box>
      </Stack>
    </LoginLayout>
  );
}
