import type { MetadataRoute } from "next";
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "KINUA — Inteligência em movimento humano",
    short_name: "KINUA",
    description:
      "Plataforma inteligente de análise corporal e movimento humano.",
    lang: "pt-BR",
    start_url: "/",
    display: "standalone",
    background_color: "#FFFFFF",
    theme_color: "#0B2D5B",
    icons: [
      {
        src: "/brand/kinua-app-icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
      { src: "/brand/kinua-icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/brand/kinua-icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
