# KINUA — identidade no produto

Identidade implementada a partir da referência visual fornecida: inteligência em movimento humano, com uma linguagem clínica, humana e precisa. O símbolo foi redesenhado em curvas vetoriais; a imagem do painel de referência não integra o aplicativo.

## Paleta e tipografia

| Token da marca | Cor | Aplicação |
| --- | --- | --- |
| Azul profundo | `#0B2D5B` | Navegação, títulos, símbolo |
| Turquesa | `#14B8A6` | Movimento, curvas, skeleton |
| Branco | `#FFFFFF` | Superfícies e versão negativa |
| Cinza suave | `#E5EAF0` | Divisórias e bordas |
| Verde menta | `#A7F3D0` | Articulações e elementos de apoio |
| Coral suave | `#FF7F7F` | Sinalização de erro; nunca classifica uma medida sozinho |

Manrope variável é servida localmente com `next/font/local`, sem chamadas ao Google Fonts durante o uso. O PDF incorpora versões estáticas de pesos 400 e 600. Arquivos de fonte obtidos do repositório oficial `google/fonts/ofl/manrope`, com licença SIL OFL incluída junto a cada distribuição.

O turquesa original permanece no símbolo e nas ilustrações. Botões com texto branco usam a variação semântica `#087F75` para contraste. No tema escuro, texto e superfícies usam tokens próprios. O tema e o recolhimento da navegação persistem apenas como preferências locais, sem dados de pacientes.

## Organização

- `frontend/app/tokens.css`: paleta, cores semânticas, espaçamento, raios, sombras e transições.
- `frontend/app/globals.css`: estrutura dos fluxos existentes, com cores referenciadas por token.
- `frontend/app/brand.css`: linguagem visual KINUA, responsividade e apresentação da marca.
- `frontend/components/brand/KinuaLogo.tsx`: variantes `horizontal`, `compact`, `symbol`; propriedades `size`, `showTagline`, `theme`.
- `frontend/components/brand/geometry.json`: curvas originais e letras convertidas em contornos, sem dependência de fontes externas para o logotipo.
- `frontend/components/brand/MovementArt.tsx`: ilustração SVG decorativa. Não representa dados nem achados.
- `frontend/components/ui`: estados vazios e cartões de indicadores compartilhados, ligados aos registros reais.
- `frontend/public/brand`: SVGs horizontal, símbolo, branco, azul, preto, wordmark e ícone; PNGs de ícone derivados do SVG em 180, 192 e 512 pixels.
- `backend/app/report_brand.py`: identidade vetorial e tipografia dos relatórios. As curvas correspondentes ficam em `backend/app/assets/kinua-geometry.json`.

Exemplo:

```tsx
<KinuaLogo variant="horizontal" size={180} theme="dark" showTagline />
```

Ícones de favicon SVG/ICO e Apple Touch estão incluídos. O manifesto prepara a identificação em dispositivos; não há cache offline de prontuários nem promessa de funcionamento offline.

## Fluxos preservados

Login, pacientes, câmera, processamento, revisão, histórico, evolução e PDF continuam usando o backend existente. O painel não inclui percentuais de melhora nem gráficos inventados. Relatórios na navegação levam ao histórico por paciente, onde cada avaliação permite gerar seu PDF. Análise abre o fluxo real de nova avaliação.

A navegação recolhe no desktop; no celular aparece na parte inferior, com controles de tema e saída ainda acessíveis. Há link para pular a navegação, nomes acessíveis para ícones, foco visível e respeito à preferência por movimento reduzido.

Nomes internos de banco, diretórios, cookie e cabeçalho CSRF `Biometria` foram preservados para compatibilidade. Eles não são a marca visível e não exigem migração de pacientes. Relatórios anteriormente gerados permanecem como foram emitidos; novas gerações usam KINUA.

## Verificação da entrega

Build de produção, verificação TypeScript, revisão de formatação e testes de contrato. Backend: 51 testes. Playwright: foto com inferência MediaPipe real, câmera com fixture local, vídeo com processamento real no servidor, revisão, histórico e PDF. Dados de QA foram mantidos em banco e armazenamento separados da clínica.

Revisão visual de login, painel, captura, resultados e PDF; navegação e ausência de transbordamento horizontal em 390 e 768 pixels, além do desktop de 1440 pixels. Tema escuro e preferências persistentes também conferidos.

Esta entrega altera a identidade e a apresentação. O estado da validação clínica e de exposição pela internet continua documentado em `clinical-readiness.md`.
