# Liturgia Diária — PWA

App de Liturgia Diária para a Arquidiocese de Florianópolis (Regional Sul 4 da CNBB).

## Como instalar no iPhone via Safari

1. Abra o Safari no iPhone
2. Acesse o endereço onde o app está hospedado (ex: `https://seu-dominio.com`)
3. Toque no botão de compartilhamento (ícone de quadrado com seta para cima)
4. Role para baixo e toque em **"Adicionar à Tela de Início"**
5. Confirme o nome "Liturgia" e toque em **"Adicionar"**
6. O app aparecerá na tela inicial como um app nativo

## Como rodar localmente

Você precisa de um servidor HTTP local. Opções:

### Com Python (já instalado no macOS):
```bash
cd liturgia
python3 -m http.server 8080
```
Acesse: `http://localhost:8080`

### Com Node.js:
```bash
npx serve liturgia
```

### Com VS Code:
Instale a extensão "Live Server" e abra o `index.html`.

## Gerar ícones PNG

1. Abra `generate-icons.html` no navegador
2. Clique nos botões para baixar `icon-192.png` e `icon-512.png`
3. Salve os arquivos na pasta `icons/`

## Estrutura de arquivos

```
liturgia/
  index.html          - App completo (HTML + CSS + JS)
  manifest.json       - Manifesto PWA
  service-worker.js   - Cache offline
  generate-icons.html - Gerador de ícones
  icons/
    icon.svg          - Ícone vetorial
    icon-192.png      - Ícone 192x192 (gerar via generate-icons.html)
    icon-512.png      - Ícone 512x512 (gerar via generate-icons.html)
```

## API utilizada

- Endpoint: `https://liturgia.up.railway.app/DD-MM-YYYY`
- Projeto: Dancrf (scraping CNBB)
- Fallback: Estrutura fixa da Santa Missa quando offline

## Funcionalidades

- 7 abas: Entrada, Leituras, Salmo, Evangelho, Orações, Eucaristia, Comunhão
- Cor litúrgica automática (verde, roxo, branco, vermelho, rosa)
- Detecção de Quaresma (oculta Glória, substitui Aleluia)
- 2ª Leitura exibida automaticamente aos domingos/festas
- Navegação entre dias (anterior/seguinte)
- 3 tamanhos de fonte (normal, grande, muito grande)
- Cache offline via Service Worker + localStorage
- Design inspirado no folheto "Deus Conosco"
