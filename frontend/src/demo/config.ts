/** True when the static demo build is served without a backend. */
export const isDemoMode = import.meta.env.VITE_DEMO_MODE === "true";

export const DEMO_USER = {
  id: 1,
  name: "Demo Fleet Manager",
  email: "demo@example.com",
  administrator: true,
  readonly: false,
  device_readonly: false,
} as const;
