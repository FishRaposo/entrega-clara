import type { Metadata } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: "Entrega Clara · Demonstração de delivery",
  description: "Uma demonstração de portfólio de delivery com o Brasil como mercado inicial.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
