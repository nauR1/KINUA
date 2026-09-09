# Componentes de terceiros

Dependências são instaladas a partir de PyPI/npm e preservam suas licenças. Consulte os metadados de cada distribuição antes de redistribuir comercialmente. O código não contém dados reais de pacientes.

O provider inicial usa Google MediaPipe Tasks Vision. Fonte e documentação:
- https://github.com/google-ai-edge/mediapipe
- https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/web_js
- https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

O manifesto em `frontend/vision/model-manifest.json` registra URL, modelo e SHA-256. O download é feito na preparação; binários do modelo/WASM não são commitados. O script recusa alterações do hash, inclusive quando um arquivo local for substituído.

Na validação de integração foi usada a imagem pública de exemplo `https://storage.googleapis.com/mediapipe-assets/pose.jpg`, apenas no diretório de trabalho local. Ela e o vídeo de câmera derivado não integram o código-fonte nem o pacote ZIP. A imagem serve para testar inferência, não como caso clínico.
