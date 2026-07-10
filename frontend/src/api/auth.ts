export type AuthUser = {
  id: number;
  name: string;
  email: string;
  administrator: boolean;
  readonly: boolean;
  device_readonly: boolean;
};
