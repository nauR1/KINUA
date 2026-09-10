import type { PoseProvider, PoseResult } from "./types";
export class MediaPipePoseProvider implements PoseProvider {
  private worker: Worker;
  private sequence = 0;
  private pending = new Map<
    number,
    {
      resolve: (r: PoseResult) => void;
      reject: (e: Error) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >();
  constructor() {
    this.worker = new Worker("/pose-worker.js");
    this.worker.onmessage = ({ data }) => {
      const pending = this.pending.get(data.id);
      if (!pending) return;
      clearTimeout(pending.timer);
      this.pending.delete(data.id);
      if (data.error) pending.reject(new Error(data.error));
      else pending.resolve(data.result);
    };
    this.worker.onerror = () =>
      this.fail(
        "Não foi possível carregar o detector corporal. Verifique os arquivos do modelo.",
      );
  }
  private fail(message: string) {
    for (const p of this.pending.values()) {
      clearTimeout(p.timer);
      p.reject(new Error(message));
    }
    this.pending.clear();
  }
  detect(bitmap: ImageBitmap): Promise<PoseResult> {
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(
          new Error("O detector excedeu o tempo limite. Reinicie a câmera."),
        );
      }, 45000);
      this.pending.set(id, { resolve, reject, timer });
      this.worker.postMessage({ id, bitmap }, [bitmap]);
    });
  }
  close() {
    this.worker.terminate();
    this.fail("Detector encerrado.");
  }
}
