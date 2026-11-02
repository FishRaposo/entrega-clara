import type { Metadata, Viewport } from "next";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "Entrega Clara · Demonstração de delivery",
    template: "%s · Entrega Clara",
  },
  description: "Uma demonstração de portfólio de delivery com o Brasil como mercado inicial.",
  applicationName: "Entrega Clara",
};

export const viewport: Viewport = {
  themeColor: "#fffdf8",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
