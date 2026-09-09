import KinuaLogo from "@/components/brand/KinuaLogo";
import type { ReactNode } from "react";
export default function EmptyState({
  title = "Seu primeiro movimento começa aqui.",
  description,
  children,
}: {
  title?: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-emblem">
        <KinuaLogo variant="symbol" size={38} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {children}
    </div>
  );
}
