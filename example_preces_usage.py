#!/usr/bin/env python3
"""
Exemplo de Uso: Ferramenta de Extração de Preces
=================================================
Demonstra como usar a classe PrecesExtractor de forma programática.
"""

from preces_extractor import PrecesExtractor
import os

def example_basic():
    """Exemplo básico: extrair de imagens e salvar"""
    print("=" * 60)
    print("EXEMPLO 1: Extração Básica")
    print("=" * 60)
    
    # Inicializar extrator
    extractor = PrecesExtractor()
    
    # Simular imagens (você substituiria por imagens reais)
    image_paths = [
        "./folheto_pagina1.jpg",
        "./folheto_pagina2.jpg",
    ]
    
    date = "2026-02-22"
    
    # Extrair dados
    data = extractor.extract_from_images(image_paths, date)
    
    # Salvar em JSON
    filepath = extractor.save_to_json(data, date)
    print(f"✅ Arquivo salvo: {filepath}\n")


def example_with_metadata():
    """Exemplo com metadados adicionais"""
    print("=" * 60)
    print("EXEMPLO 2: Extração com Metadados")
    print("=" * 60)
    
    extractor = PrecesExtractor()
    
    image_paths = ["./folheto.jpg"]
    date = "2026-02-22"
    
    # Extrair dados
    data = extractor.extract_from_images(image_paths, date)
    
    # Adicionar informações extras
    additional = {
        "domingo": "1º Domingo da Quaresma",
        "ano_liturgico": "B",
        "ciclo": "quaresma",
        "cor": "roxo",
    }
    
    # Salvar com metadados
    filepath = extractor.save_to_json(data, date, additional_fields=additional)
    print(f"✅ Arquivo salvo com metadados: {filepath}\n")


def example_from_directory():
    """Exemplo: processar todas as imagens de um diretório"""
    print("=" * 60)
    print("EXEMPLO 3: Processar Diretório")
    print("=" * 60)
    
    import glob
    
    extractor = PrecesExtractor()
    
    # Buscar todas as imagens JPG em um diretório
    folhetos_dir = "./folhetos"
    image_paths = glob.glob(f"{folhetos_dir}/*.jpg")
    
    if image_paths:
        date = "2026-02-22"
        data = extractor.extract_from_images(image_paths, date)
        filepath = extractor.save_to_json(data, date)
        print(f"✅ {len(image_paths)} imagens processadas")
        print(f"   Arquivo: {filepath}\n")
    else:
        print(f"⚠️  Nenhuma imagem encontrada em {folhetos_dir}\n")


def example_error_handling():
    """Exemplo: tratamento de erros"""
    print("=" * 60)
    print("EXEMPLO 4: Tratamento de Erros")
    print("=" * 60)
    
    extractor = PrecesExtractor()
    
    try:
        # Imagens inválidas
        data = extractor.extract_from_images(["arquivo_inexistente.jpg"], "2026-02-22")
    except FileNotFoundError as e:
        print(f"❌ Arquivo não encontrado: {e}\n")
    except ValueError as e:
        print(f"❌ Erro de validação: {e}\n")
    
    try:
        # Data inválida
        extractor.save_to_json({"resposta": "Test"}, "22-02-2026")
    except ValueError as e:
        print(f"❌ Formato de data inválido: {e}\n")


def show_cli_commands():
    """Mostra exemplos de linhas de comando"""
    print("=" * 60)
    print("USO VIA LINHA DE COMANDO")
    print("=" * 60)
    print("""
# Básico: extrair de uma ou mais imagens
python3 preces_extractor.py --date 2026-02-22 --images foto1.jpg foto2.jpg

# Usar wildcards
python3 preces_extractor.py --date 2026-02-22 --images ./folhetos/*.jpg

# Com metadados adicionais
python3 preces_extractor.py \\
  --date 2026-02-22 \\
  --images foto1.jpg foto2.jpg \\
  --domingo "1º Domingo da Quaresma" \\
  --ano-liturgico B

# Salvar em local customizado
python3 preces_extractor.py \\
  --date 2026-02-22 \\
  --images foto1.jpg \\
  --output ./dados_customizados/preces.json

# Com chave API específica
python3 preces_extractor.py \\
  --date 2026-02-22 \\
  --images foto.jpg \\
  --api-key sua_chave_aqui
    """)


def show_output_format():
    """Mostra formato do arquivo JSON de saída"""
    print("=" * 60)
    print("FORMATO DE SAÍDA JSON")
    print("=" * 60)
    print("""
{
  "data": "2026-02-22",
  "resposta": "Assisti, ó Senhor...",
  "intencoes": [
    {
      "numero": 1,
      "tema": "Pela Igreja",
      "texto": "Pela Igreja: para que, neste tempo de Quaresma..."
    },
    {
      "numero": 2,
      "tema": "Pelos governantes",
      "texto": "Pelos governantes: para que se empenhem..."
    },
    {
      "numero": 3,
      "tema": "Pelas famílias",
      "texto": "Pelas famílias: para que sejam espaços..."
    },
    {
      "numero": 4,
      "tema": "Pelo sacrifício",
      "texto": "Pelo todo sacrifício seja aceito por Deus..."
    },
    {
      "numero": 5,
      "tema": "Por nós aqui reunidos",
      "texto": "Por nós aqui reunidos: para que a vivência..."
    }
  ],
  "oracao_eucaristica": "III",
  "fonte": "Arquidiocese de Brasília - O Povo de Deus",
  "atualizado_em": "2026-02-24T14:32:00Z"
}
    """)


if __name__ == "__main__":
    print("\n🙏 SantaLitu - Exemplos de Uso\n")
    
    # Mostrar informações gerais
    show_cli_commands()
    show_output_format()
    
    print("\n" + "=" * 60)
    print("COMO USAR NA SUA APLICAÇÃO")
    print("=" * 60)
    print("""
from preces_extractor import PrecesExtractor

# Criar instância
extractor = PrecesExtractor()

# Extrair de imagens
data = extractor.extract_from_images(
    image_paths=["foto1.jpg", "foto2.jpg"],
    data_date="2026-02-22"
)

# Salvar em JSON
filepath = extractor.save_to_json(data, "2026-02-22")

# Ou com campos adicionais
filepath = extractor.save_to_json(
    data,
    "2026-02-22",
    additional_fields={
        "domingo": "1º Domingo da Quaresma",
        "ano_liturgico": "B"
    }
)
    """)
    
    print("\n✅ Exemplos concluídos!")
    print("   Para mais detalhes, veja o código-fonte de preces_extractor.py\n")
