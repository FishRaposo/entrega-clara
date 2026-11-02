"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const roles = [
  { href: "/customer", label: "Cliente", accessibleLabel: "Cliente (Customer)" },
  { href: "/restaurant", label: "Restaurante", accessibleLabel: "Restaurante (Restaurant)" },
  { href: "/courier", label: "Entregador", accessibleLabel: "Entregador (Courier)" },
  { href: "/admin", label: "Administrador", accessibleLabel: "Administrador (Admin)" },
] as const;

type RoleSwitcherProps = {
  variant?: "default" | "header";
};

export function RoleSwitcher({ variant = "default" }: RoleSwitcherProps) {
  const pathname = usePathname();
  const links = roles.map((role) => (
    <Link
      aria-current={pathname === role.href ? "page" : undefined}
      aria-label={role.accessibleLabel}
      href={role.href}
      key={role.href}
    >
      {role.label}
    </Link>
  ));

  if (variant === "header") {
    return (
      <nav aria-label="Papéis da demonstração" className="role-switcher header-role-switcher">
        <span className="eyebrow">Papéis</span>
        <div className="role-links">{links}</div>
      </nav>
    );
  }

  return (
    <nav aria-label="Navegação de papéis da demonstração" className="role-switcher">
      <span className="eyebrow">Prévia de papéis da demonstração</span>
      <div className="role-links">{links}</div>
      <p className="role-note">Os links servem apenas para navegar na demonstração; ninguém faz login.</p>
    </nav>
  );
}
