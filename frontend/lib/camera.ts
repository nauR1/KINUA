export function cameraError(error: unknown): string {
  const name = error instanceof Error ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Acesso à câmera não autorizado. Permita a câmera no navegador ou envie um arquivo.";
  if (name === "NotFoundError" || name === "DevicesNotFoundError")
    return "Nenhuma câmera encontrada. Conecte uma câmera ou envie um arquivo.";
  if (name === "NotReadableError" || name === "TrackStartError")
    return "A câmera está ocupada ou foi desconectada. Confira o dispositivo e tente novamente.";
  if (name === "OverconstrainedError")
    return "A câmera não suporta a configuração solicitada. Use outro dispositivo ou envie um arquivo.";
  return error instanceof Error
    ? error.message
    : "Não foi possível iniciar a câmera.";
}
