import type { Metadata } from "next";
import "./globals.css";
import "./brand.css";
import "./protocols.css";
import localFont from "next/font/local";
const manrope = localFont({
  src: "../public/brand/fonts/Manrope-Variable.ttf",
  variable: "--font-manrope",
  display: "swap",
  weight: "200 800",
});
export const metadata: Metadata = {
  title: "KINUA · Análise corporal inteligente",
  description: "Plataforma inteligente de análise corporal e movimento humano.",
  icons: { icon: "/favicon.svg", apple: "/brand/kinua-icon-180.png" },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={manrope.variable}>
      <body>{children}</body>
    </html>
  );
}
