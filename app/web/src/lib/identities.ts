export const DEMO_IDENTITIES = {
  customer: "demo-customer",
  restaurant: "demo-rest-seu-manoel",
  courier: "demo-courier",
  operations: "demo-operations",
} as const;

export type DemoIdentity = (typeof DEMO_IDENTITIES)[keyof typeof DEMO_IDENTITIES];
