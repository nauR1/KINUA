import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Biometria · Avaliação corporal",
  description: "Medição corporal e revisão profissional para fisioterapia.",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
