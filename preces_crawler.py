"""
SantaLitu - Crawler de Preces da Assembleia (Oração dos Fiéis)
==============================================================
Extrai as Preces semanais dos folhetos litúrgicos da CNBB publicados
por dioceses brasileiras em PDF.

Fontes:
  1. Arquidiocese de Brasília - "O Povo de Deus"
  2. Diocese da Campanha - "O Dia do Senhor"
  3. Arquidiocese de São Paulo - "Povo de Deus em São Paulo"

Uso:
  python preces_crawler.py                # busca próximo domingo
  python preces_crawler.py 2026-02-22     # busca data específica
"""

import os
import re
import sys
import json
import datetime
import urllib.request
import urllib.error
import ssl
import tempfile
import glob
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Tentar importar pdfplumber, senão usar fallback
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

# Diretório para salvar JSONs
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "preces_data")
PDF_CACHE_DIR = os.path.join(SCRIPT_DIR, "pdf_cache")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_CACHE_DIR, exist_ok=True)

# ===== HELPERS =====
def get_next_sunday(from_date=None):
    """Retorna a data do próximo domingo."""
    d = from_date or datetime.date.today()
    days_until = (6 - d.weekday()) % 7
    if days_until == 0 and from_date is None:
        days_until = 7  # se hoje é domingo, pega o próximo
    return d + datetime.timedelta(days=days_until)

def fmt_date_br(d):
    """Formata data para dd/mm/yyyy."""
    return d.strftime("%d/%m/%Y")

def fmt_date_iso(d):
    """Formata data para yyyy-mm-dd."""
    return d.strftime("%Y-%m-%d")

def fmt_date_file(d):
    """Formata para nome de arquivo: dd-mm-yyyy."""
    return d.strftime("%d-%m-%Y")

def download_file(url, dest_path, timeout=30):
    """Baixa um arquivo de URL para dest_path."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            data = resp.read()
            with open(dest_path, 'wb') as f:
                f.write(data)
            return True
    except Exception as e:
        print(f"  [ERRO] Download falhou: {url} -> {e}")
        return False

def download_page(url, timeout=20):
    """Baixa conteúdo HTML de uma página."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f"  [ERRO] Página não acessível: {url} -> {e}")
        return None

# ===== PDF TEXT EXTRACTION =====
def extract_text_pdfplumber(pdf_path):
    """Extrai texto usando pdfplumber com suporte a duas colunas."""
    if not HAS_PDFPLUMBER:
        return None
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                w = page.width
                # Extrair coluna esquerda, depois direita
                left = page.crop((0, 0, w/2, page.height))
                right = page.crop((w/2, 0, w, page.height))
                tl = left.extract_text() or ''
                tr = right.extract_text() or ''
                text += tl + "\n" + tr + "\n"
        return text if text.strip() else None
    except Exception as e:
        print(f"  [ERRO] pdfplumber: {e}")
        return None

def extract_text_pymupdf(pdf_path):
    """Extrai texto usando PyMuPDF (fitz)."""
    if not HAS_PYMUPDF:
        return None
    try:
        text = ""
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text() + "\n"
        doc.close()
        return text if text.strip() else None
    except Exception as e:
        print(f"  [ERRO] PyMuPDF: {e}")
        return None

def extract_text(pdf_path):
    """Extrai texto do PDF usando a melhor lib disponível."""
    text = extract_text_pdfplumber(pdf_path)
    if text:
        return text
    text = extract_text_pymupdf(pdf_path)
    if text:
        return text
    print("  [ERRO] Nenhuma biblioteca PDF disponível. Instale: pip install pdfplumber")
    return None

# ===== PRECES PARSER =====
def parse_preces(text, target_date=None):
    """
    Analisa o texto extraído do PDF e encontra as Preces da Assembleia.
    Retorna dict com resposta e intenções.
    
    Formato real do folheto Diocese da Campanha:
    - Seção: "Oração da Assembleia" ou "Preces da Assembleia"
    - Resposta após "Ass.:" logo depois do convite do presidente
    - Intenções numeradas (1., 2., 3.) terminando com "nós vos pedimos:"
    - Oração conclusiva do presidente após as intenções
    """
    if not text:
        return None

    # Normalizar texto
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Encontrar seção de Preces - vários nomes possíveis
    preces_patterns = [
        r'Ora[çc][aã]o\s+da\s+Assembl[eé]ia',
        r'Preces\s+da\s+Assembl[eé]ia',
        r'Ora[çc][aã]o\s+dos\s+Fi[eé]is',
        r'Ora[çc][aã]o\s+Universal',
        r'PRECES\s+DA\s+ASSEMBL[EÉ]IA',
        r'ORA[ÇC][AÃ]O\s+DA\s+ASSEMBL[EÉ]IA',
        r'ORA[ÇC][AÃ]O\s+DOS\s+FI[EÉ]IS',
    ]

    preces_start = -1
    for pat in preces_patterns:
        match = re.search(pat, text, re.IGNORECASE)
        if match:
            preces_start = match.start()
            print(f"  Secao encontrada: '{match.group()}' na posicao {preces_start}")
            break

    if preces_start == -1:
        print("  [AVISO] Secao de Preces nao encontrada no PDF")
        return None

    # Extrair texto das preces até a próxima seção
    end_patterns = [
        r'\n(?:LiTURGiA|LITURGIA)\s+EUCAR[IÍí]STICA',
        r'\n(?:Apresenta[çc][aã]o|APRESENTA[ÇC])',
        r'\nConvite\s+[àa]\s+Ora[çc][aã]o',
        r'\nOra[çc][aã]o\s+sobre\s+as\s+Oferendas',
        r'\nORA[ÇC][AÃ]O\s+EUCAR[IÍ]STICA',
        r'\nPrefácio',
        r'\nPREFÁCIO',
    ]

    preces_end = min(preces_start + 3000, len(text))  # máx 3000 chars
    for pat in end_patterns:
        match = re.search(pat, text[preces_start + 20:preces_end], re.IGNORECASE)
        if match:
            preces_end = preces_start + 20 + match.start()
            break

    preces_text = text[preces_start:preces_end]
    print(f"  Texto da secao ({len(preces_text)} chars)")

    # === Extrair RESPOSTA ===
    resposta = None
    
    # Padrão 1: "Ass.:" seguido do texto da resposta (formato Diocese da Campanha)
    resp_match = re.search(r'Ass\.?\s*:\s*(.+?)(?:\n|$)', preces_text)
    if resp_match:
        candidate = resp_match.group(1).strip().rstrip('.')
        if len(candidate) > 5 and len(candidate) < 80:
            resposta = candidate + ('.' if not candidate.endswith('!') else '')

    # Padrão 2: "R." ou "♦" 
    if not resposta:
        resp_match = re.search(r'[R♦]\.\s*[:–-]?\s*(.+?)(?:\n|$)', preces_text)
        if resp_match:
            candidate = resp_match.group(1).strip()
            if len(candidate) > 10:
                resposta = candidate

    # Padrão 3: "Resposta:" ou "RESPOSTA:"
    if not resposta:
        resp_match = re.search(r'(?:Resposta|RESPOSTA)\s*[:–-]?\s*(.+?)(?:\n|$)', preces_text)
        if resp_match:
            candidate = resp_match.group(1).strip()
            if len(candidate) > 10:
                resposta = candidate

    print(f"  Resposta encontrada: {resposta}")

    # === Extrair INTENÇÕES ===
    intencoes = []

    # Padrão principal: numeradas (1., 2., 3., 4.)
    # Elas podem ser interleaved com texto de outras colunas no PDF
    # Vamos usar uma abordagem robusta
    int_pattern = re.compile(r'(\d+)\.\s+(.+?)(?=\n\d+\.\s|\n\(Outras\s+preces|\nPres\.:\s|\Z)', re.DOTALL)
    int_matches = int_pattern.findall(preces_text)
    
    if int_matches:
        for num_str, texto_raw in int_matches:
            num = int(num_str)
            # Limpar texto: remover quebras de linha e espaços extras
            texto_clean = re.sub(r'\s+', ' ', texto_raw).strip()
            
            # Ignorar textos muito curtos ou que são versículos do salmo/canto
            if len(texto_clean) < 20:
                continue
            
            # Verificar se parece uma intenção (contém "pedimos", "rezemos", "Senhor", etc.)
            looks_like_intention = any(w in texto_clean.lower() for w in 
                ['pedimos', 'rezemos', 'senhor', 'concedei', 'inspirai', 'ajudai', 'dai-'])
            
            if not looks_like_intention and num > 1:
                continue

            # Tentar extrair tema
            tema = f"Intencao {num}"
            tema_patterns = [
                (r'^(?:Pel[oa]s?\s+.+?)(?:,|\s+nós)', 'match'),
                (r'^(?:Por\s+.+?)(?:,|\s+nós)', 'match'),
                (r'^(?:Senhor.+?)(?:,|\s+aju)', 'match'),
                (r'^(?:Inspirai.+?)(?:\s+medidas)', 'match'),
                (r'^(?:Concedei.+?)(?:\s+que)', 'match'),
                (r'^(?:Afastai.+?)(?:\s+das)', 'match'),
            ]
            for tp, _ in tema_patterns:
                tm = re.match(tp, texto_clean, re.IGNORECASE)
                if tm:
                    tema = tm.group(0).strip().rstrip(',')
                    if len(tema) > 50:
                        tema = tema[:50] + "..."
                    break

            intencoes.append({
                "numero": num,
                "tema": tema,
                "texto": texto_clean
            })

    # Se não encontrou intenções numeradas, tentar por blocos separados por resposta
    if not intencoes:
        # Dividir por "nós vos pedimos:" ou "Rezemos" ou pela resposta repetida
        if resposta:
            blocks = re.split(re.escape(resposta), preces_text)
        else:
            blocks = re.split(r'(?:nós\s+vos\s+pedimos\s*:|[Rr]ezemos.*?\.)', preces_text)
        
        num = 0
        for block in blocks:
            block = re.sub(r'\s+', ' ', block).strip()
            if len(block) < 30:
                continue
            if re.search(r'^(?:Pres\.|Ass\.|Ora[çc]|PRECES|LITURGIA)', block, re.IGNORECASE):
                continue
            num += 1
            intencoes.append({
                "numero": num,
                "tema": f"Intencao {num}",
                "texto": block
            })

    if not intencoes:
        print("  [AVISO] Nenhuma intencao extraida das preces")
        return None

    print(f"  Intencoes encontradas: {len(intencoes)}")
    for i in intencoes:
        print(f"    {i['numero']}. {i['texto'][:60]}...")

    return {
        "resposta": resposta or "Senhor, escutai a nossa prece.",
        "intencoes": intencoes
    }

# ===== ORAÇÃO EUCARÍSTICA DETECTION =====
def extract_oracao_eucaristica(text):
    """Detecta qual Oração Eucarística é usada no folheto."""
    if not text:
        return None
    # Buscar padrão: ORAÇÃO EUCARÍSTICA III, Oração Eucarística II, etc.
    match = re.search(r'ORA[ÇC][AÃ]O\s+EUCAR[IÍ]STICA\s+(I{1,3}V?|\d+)', text, re.IGNORECASE)
    if match:
        oe = match.group(1).upper().strip()
        print(f"  Oracao Eucaristica detectada: {oe}")
        return oe
    return None

# ===== LITURGICAL HELPERS =====
def get_liturgical_info(date_obj):
    """Determina informações litúrgicas básicas para a data."""
    # API check
    api_url = f"https://liturgia.up.railway.app/{date_obj.strftime('%d-%m-%Y')}"
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(api_url, headers={
            'User-Agent': 'SantaLitu/1.0'
        })
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            liturgia = data.get('liturgia', '')
            cor = data.get('cor', 'verde')
            ciclo = 'quaresma' if 'quaresma' in liturgia.lower() else \
                    'advento' if 'advento' in liturgia.lower() else \
                    'pascoa' if 'páscoa' in liturgia.lower() or 'pascoa' in liturgia.lower() else \
                    'tempo_comum'
            # Ano litúrgico
            year = date_obj.year
            ano = chr(ord('A') + (year % 3))  # A=2026, B=2024, C=2025
            return {
                'domingo': liturgia,
                'ano_liturgico': ano,
                'ciclo': ciclo,
                'cor': cor
            }
    except Exception as e:
        print(f"  [AVISO] API liturgia indisponível: {e}")
        return {
            'domingo': 'Domingo',
            'ano_liturgico': chr(ord('A') + (date_obj.year % 3)),
            'ciclo': 'desconhecido',
            'cor': 'verde'
        }

# ===== PDF FINDERS =====
def find_pdf_arqbrasilia(target_date):
    """Tenta encontrar PDF no site da Arquidiocese de Brasília."""
    print(f"  Buscando PDF em arqbrasilia.com.br...")

    # Padrão de URL observado
    year = target_date.year
    month = target_date.month
    month_names = ['', 'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho',
                   'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    # Tentar vários padrões de URL comuns em sites WordPress
    date_str = target_date.strftime("%d-%m-%Y")
    date_str2 = target_date.strftime("%d-%m-%y")
    date_str3 = target_date.strftime("%Y%m%d")
    month_str = f"{year}/{str(month).zfill(2)}"

    base_urls = [
        f"https://arqbrasilia.com.br/wp-content/uploads/{month_str}/",
    ]

    # Primeiro tentar acessar a página do folheto
    page_url = "https://arqbrasilia.com.br/o-povo-de-deus/"
    html = download_page(page_url)
    if html:
        # Procurar links PDF na página que contenham a data
        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
        pdf_links = re.findall(pdf_pattern, html, re.IGNORECASE)
        for link in pdf_links:
            link_lower = link.lower()
            # Check se o link contém a data ou referência ao domingo
            if (date_str.replace('-', '') in link_lower or
                date_str in link_lower or
                'quaresma' in link_lower or
                target_date.strftime('%d_%m') in link_lower):
                full_url = link if link.startswith('http') else f"https://arqbrasilia.com.br{link}"
                pdf_path = os.path.join(PDF_CACHE_DIR, f"arqbrasilia_{date_str}.pdf")
                if download_file(full_url, pdf_path):
                    return pdf_path

        # Tentar todos os PDFs da página e ver qual tem a data certa
        for link in pdf_links:
            if 'povo' in link.lower() or 'folheto' in link.lower() or 'liturgi' in link.lower():
                full_url = link if link.startswith('http') else f"https://arqbrasilia.com.br{link}"
                pdf_path = os.path.join(PDF_CACHE_DIR, f"arqbrasilia_{date_str}.pdf")
                if download_file(full_url, pdf_path):
                    return pdf_path

    return None

def find_pdf_diocesecampanha(target_date):
    """Tenta encontrar PDF no site da Diocese da Campanha."""
    print(f"  Buscando PDF em diocesedacampanha.org.br...")

    date_str = target_date.strftime("%d-%m-%Y")
    year = target_date.year
    month = target_date.month
    month_str = f"{year}/{str(month).zfill(2)}"

    # Tentar página principal de folhetos
    pages_to_try = [
        "https://diocesedacampanha.org.br/downloads/o-dia-do-senhor-e-partituras/",
    ]

    for page_url in pages_to_try:
        html = download_page(page_url)
        if not html:
            continue

        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
        pdf_links = re.findall(pdf_pattern, html, re.IGNORECASE)

        for link in pdf_links:
            link_lower = link.lower()
            if ('folheto' in link_lower and
                (date_str in link_lower or
                 date_str.replace('-', '') in link_lower)):
                full_url = link if link.startswith('http') else f"https://diocesedacampanha.org.br{link}"
                pdf_path = os.path.join(PDF_CACHE_DIR, f"campanha_{date_str}.pdf")
                if download_file(full_url, pdf_path):
                    return pdf_path

    return None

def find_pdf_arquisp(target_date):
    """Tenta encontrar PDF na Arquidiocese de São Paulo."""
    print(f"  Buscando PDF em arquisp.org.br...")

    date_str = target_date.strftime("%d-%m-%Y")

    page_url = "https://arquisp.org.br/povo-de-deus"
    html = download_page(page_url)
    if html:
        pdf_pattern = r'href=["\']([^"\']*\.pdf)["\']'
        pdf_links = re.findall(pdf_pattern, html, re.IGNORECASE)
        for link in pdf_links:
            link_lower = link.lower()
            if ('povo' in link_lower or 'folheto' in link_lower or 'liturgi' in link_lower):
                full_url = link if link.startswith('http') else f"https://arquisp.org.br{link}"
                pdf_path = os.path.join(PDF_CACHE_DIR, f"arquisp_{date_str}.pdf")
                if download_file(full_url, pdf_path):
                    return pdf_path

    return None

# ===== MAIN CRAWL =====
def crawl_preces(target_date):
    """
    Busca e extrai as Preces da Assembleia para a data alvo.
    Retorna o JSON completo ou None.
    """
    date_str = fmt_date_iso(target_date)
    json_path = os.path.join(DATA_DIR, f"preces_{date_str}.json")

    # Verificar cache
    if os.path.exists(json_path):
        print(f"  [CACHE] Preces já existe: {json_path}")
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    print(f"\n{'='*60}")
    print(f"  BUSCANDO PRECES PARA: {fmt_date_br(target_date)}")
    print(f"{'='*60}")

    # Tentar fontes em ordem de prioridade
    pdf_path = None
    fonte = None

    finders = [
        ("Arquidiocese de Brasília", find_pdf_arqbrasilia),
        ("Diocese da Campanha", find_pdf_diocesecampanha),
        ("Arquidiocese de São Paulo", find_pdf_arquisp),
    ]

    for nome, finder in finders:
        print(f"\n  Tentando: {nome}...")
        pdf_path = finder(target_date)
        if pdf_path:
            fonte = nome
            print(f"  [OK] PDF encontrado: {os.path.basename(pdf_path)}")
            break

    if not pdf_path:
        print("\n  [X] Nenhum PDF encontrado em nenhuma fonte.")
        print("    Gerando preces padrão baseadas na estação litúrgica...")
        return generate_fallback_preces(target_date, json_path)

    # Extrair texto
    print(f"\n  Extraindo texto do PDF...")
    text = extract_text(pdf_path)
    if not text:
        print("  [X] Nao foi possivel extrair texto do PDF")
        return generate_fallback_preces(target_date, json_path)

    # Parsear preces
    print(f"  Parseando Preces da Assembleia...")
    preces = parse_preces(text, target_date)
    if not preces:
        print("  [X] Nao foi possivel encontrar/parsear as preces no PDF")
        return generate_fallback_preces(target_date, json_path)

    # Detectar Oração Eucarística
    oe = extract_oracao_eucaristica(text)

    # Obter info litúrgica
    lit_info = get_liturgical_info(target_date)

    # Montar resultado
    result = {
        "data": date_str,
        "domingo": lit_info['domingo'],
        "ano_liturgico": lit_info['ano_liturgico'],
        "ciclo": lit_info['ciclo'],
        "cor": lit_info['cor'],
        "fonte": fonte,
        "oracao_eucaristica": oe or "III",
        "resposta": preces['resposta'],
        "intencoes": preces['intencoes'],
        "atualizado_em": datetime.datetime.now().isoformat()
    }

    # Salvar JSON
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n  [OK] Preces salvas: {json_path}")
    print(f"    Resposta: {result['resposta']}")
    print(f"    Intenções: {len(result['intencoes'])}")

    return result

def generate_fallback_preces(target_date, json_path):
    """Gera preces padrão baseadas na estação litúrgica quando o PDF não está disponível."""
    lit_info = get_liturgical_info(target_date)
    ciclo = lit_info.get('ciclo', 'tempo_comum')

    # Preces padrão por estação
    if ciclo == 'quaresma':
        result = {
            "data": fmt_date_iso(target_date),
            "domingo": lit_info['domingo'],
            "ano_liturgico": lit_info['ano_liturgico'],
            "ciclo": ciclo,
            "cor": lit_info.get('cor', 'roxo'),
            "fonte": "gerado_automatico",
            "resposta": "Senhor, escutai a nossa prece.",
            "intencoes": [
                {"numero": 1, "tema": "Pela Igreja", "texto": "Pelo Papa, pelos bispos e por todo o clero: para que sejam sustentados pela Palavra de Deus e conduzam o povo com fidelidade neste tempo de conversão. Rezemos ao Senhor."},
                {"numero": 2, "tema": "Pelos governantes", "texto": "Pelos governantes e por todos os que exercem autoridade: para que promovam a justiça, a paz e o bem comum, especialmente para os mais pobres e necessitados. Rezemos ao Senhor."},
                {"numero": 3, "tema": "Pelos catecúmenos", "texto": "Pelos catecúmenos e por todos os que se preparam para celebrar a Páscoa: para que sejam conduzidos pela Palavra e pelo Espírito e recebam a graça de vencer as tentações. Rezemos ao Senhor."},
                {"numero": 4, "tema": "Pela comunidade", "texto": "Pela nossa comunidade e por todas as famílias: para que a vivência da Campanha da Fraternidade nos leve a superar a indiferença e a abrir o coração aos irmãos mais necessitados. Rezemos ao Senhor."},
                {"numero": 5, "tema": "Por nós", "texto": "Por todos nós aqui reunidos: para que, seguindo o exemplo de Cristo no deserto, saibamos resistir às tentações pela oração, pelo jejum e pela caridade. Rezemos ao Senhor."}
            ],
            "atualizado_em": datetime.datetime.now().isoformat()
        }
    else:
        result = {
            "data": fmt_date_iso(target_date),
            "domingo": lit_info['domingo'],
            "ano_liturgico": lit_info['ano_liturgico'],
            "ciclo": ciclo,
            "cor": lit_info.get('cor', 'verde'),
            "fonte": "gerado_automatico",
            "resposta": "Senhor, escutai a nossa prece.",
            "intencoes": [
                {"numero": 1, "tema": "Pela Igreja", "texto": "Pela Santa Igreja de Deus, pelo Papa e por todos os pastores: para que, guiados pelo Espírito Santo, sejam sempre fiéis à missão de anunciar o Evangelho. Rezemos ao Senhor."},
                {"numero": 2, "tema": "Pelos governantes", "texto": "Pelos governantes e por todos os que exercem autoridade: para que promovam a justiça, a paz e o bem comum. Rezemos ao Senhor."},
                {"numero": 3, "tema": "Pelos que sofrem", "texto": "Pelos que sofrem, pelos doentes, pelos que perderam entes queridos e por todos os necessitados: para que encontrem no Senhor consolo e esperança. Rezemos ao Senhor."},
                {"numero": 4, "tema": "Pela comunidade", "texto": "Por nossa comunidade: para que vivamos na fé, na caridade e na comunhão fraterna. Rezemos ao Senhor."},
                {"numero": 5, "tema": "Por nós", "texto": "Por todos nós aqui reunidos: para que esta celebração eucarística nos fortaleça no caminho da santidade e do serviço ao próximo. Rezemos ao Senhor."}
            ],
            "atualizado_em": datetime.datetime.now().isoformat()
        }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Preces fallback salvas: {json_path}")
    return result

# ===== CLI =====
if __name__ == '__main__':
    if len(sys.argv) > 1:
        try:
            target = datetime.date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"Data inválida: {sys.argv[1]}. Use formato YYYY-MM-DD")
            sys.exit(1)
    else:
        target = get_next_sunday()

    print(f"SantaLitu - Crawler de Preces")
    print(f"Data alvo: {fmt_date_br(target)} ({fmt_date_iso(target)})")
    print(f"Libs disponíveis: pdfplumber={'SIM' if HAS_PDFPLUMBER else 'NÃO'}, PyMuPDF={'SIM' if HAS_PYMUPDF else 'NÃO'}")

    result = crawl_preces(target)
    if result:
        print(f"\n{'='*60}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("\nFalha ao obter preces.")
        sys.exit(1)
