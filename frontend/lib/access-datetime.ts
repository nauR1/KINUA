export function toUtcIso(
  value: FormDataEntryValue | string | null,
): string | null {
  const raw = value === null ? "" : String(value).trim();
  if (!raw) return null;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) throw new Error("Data inválida.");
  return parsed.toISOString();
}

export function toDatetimeLocal(value: string | null): string {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
