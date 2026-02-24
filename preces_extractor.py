#!/usr/bin/env python3
"""
SantaLitu - Ferramenta de Extração Automática de Preces
========================================================
Extrai preces de imagens de folhetos litúrgicos usando visão computacional.

Uso:
  python3 preces_extractor.py --date 2026-02-22 --images foto1.jpg foto2.jpg
  python3 preces_extractor.py --date 2026-02-22 --images ./folhetos/*

Requisitos:
  - Acesso à API de visão (via OpenClaw)
  - Imagens em formato JPG ou PNG

Formato de saída:
  {
    "data": "2026-02-22",
    "resposta": "Assisti, ó Senhor...",
    "intencoes": [
      {"numero": 1, "tema": "...", "texto": "..."},
      ...
    ],
    "atualizado_em": "ISO 8601 timestamp"
  }
"""

import os
import sys
import json
import glob
import argparse
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Try to import anthropic for vision API
try:
    from anthropic import Anthropic, APIError
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False
    print("⚠️  Anthropic SDK not found. Install: pip install anthropic")

# Script directory setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "preces_data")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


class PrecesExtractor:
    """Extrator de Preces de Imagens de Folhetos Litúrgicos"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o extrator.
        
        Args:
            api_key: Chave API do Anthropic (usa ANTHROPIC_API_KEY se não fornecido)
        """
        if not HAS_ANTHROPIC:
            raise ImportError("Anthropic SDK não encontrado. Instale com: pip install anthropic")
        
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key não encontrada. Defina ANTHROPIC_API_KEY ou passe via api_key="
            )
        
        self.client = Anthropic(api_key=self.api_key)

    def extract_from_images(
        self, 
        image_paths: List[str], 
        data_date: str
    ) -> Dict[str, Any]:
        """
        Extrai preces de uma lista de imagens.
        
        Args:
            image_paths: Lista de caminhos para imagens (jpg/png)
            data_date: Data no formato YYYY-MM-DD
        
        Returns:
            Dict com chaves:
              - "response": Resposta das preces (ex: "Assisti, ó Senhor...")
              - "intentions": Array com até 5 intenções
              - "eucharistic_prayer": Número da oração eucarística (1-4)
              - "source": Fonte do folheto (se identificada)
        """
        
        if not image_paths:
            raise ValueError("Nenhuma imagem fornecida")
        
        # Preparar conteúdo das imagens para envio
        image_content = []
        
        for idx, img_path in enumerate(image_paths, 1):
            if not os.path.exists(img_path):
                print(f"⚠️  Imagem {idx} não encontrada: {img_path}")
                continue
            
            # Ler arquivo em base64
            with open(img_path, "rb") as f:
                import base64
                img_data = base64.standard_b64encode(f.read()).decode("utf-8")
            
            # Detectar tipo MIME
            ext = Path(img_path).suffix.lower()
            media_type = "image/jpeg" if ext in [".jpg", ".jpeg"] else "image/png"
            
            image_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": img_data,
                },
            })
        
        if not image_content:
            raise ValueError("Nenhuma imagem válida fornecida")
        
        # Preparar prompt para extração
        prompt = """Você é um especialista em liturgia católica. Analise a(s) imagem(ns) de folheto(s) litúrgico(s) e extraia as seguintes informações:

1. **RESPOSTA DA ASSEMBLY** (ex: "Assisti, ó Senhor..." ou "Vinde, Senhor..."):
   - Procure pela resposta que o povo deve falar durante as preces

2. **INTENÇÕES DAS PRECES** (até 5):
   - Cada intenção contém: tema (ex: "Pela Igreja") e texto completo
   - Formate cada uma como: "TEMA: [tema] | TEXTO: [texto completo]"

3. **ORAÇÃO EUCARÍSTICA**:
   - Identifique qual oração eucarística está indicada (I, II, III, IV)
   - Se houver variações ou alternativas, mencione

4. **FONTE** (se disponível):
   - Diocese/Arquidiocese ou publicação

Retorne NO FORMATO JSON, similar a este:
{
  "resposta": "Assisti, ó Senhor...",
  "intencoes": [
    {"numero": 1, "tema": "Pela Igreja", "texto": "texto completo da intenção 1"},
    {"numero": 2, "tema": "...", "texto": "..."},
    ...
  ],
  "oracao_eucaristica": "III",
  "fonte": "Nome da fonte se identificada"
}

IMPORTANTE:
- Se não conseguir extrair informações completas, inclua o que conseguir
- Mantenha exatamente a estrutura JSON acima
- Não adicione campos extras
- Garanta que os textos das intenções estejam completos e legíveis"""
        
        # Adicionar prompt ao final do conteúdo
        image_content.append({
            "type": "text",
            "text": prompt
        })
        
        print(f"📸 Analisando {len([i for i in image_content if i['type'] == 'image'])} imagem(ns)...")
        
        try:
            # Chamar API de visão do Claude
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Melhor modelo para visão
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": image_content,
                    }
                ],
            )
            
            response_text = response.content[0].text
            
            # Tentar parsear JSON da resposta
            try:
                # Procurar bloco JSON na resposta
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    extracted = json.loads(json_str)
                else:
                    raise ValueError("Nenhum JSON encontrado na resposta")
                
                # Validar estrutura mínima
                if "resposta" not in extracted:
                    extracted["resposta"] = "Resposta não extraída"
                
                if "intencoes" not in extracted:
                    extracted["intencoes"] = []
                
                # Garantir que temos até 5 intenções
                extracted["intencoes"] = extracted["intencoes"][:5]
                
                # Garantir que cada intenção tem número
                for idx, intent in enumerate(extracted["intencoes"], 1):
                    if "numero" not in intent:
                        intent["numero"] = idx
                
                return extracted
            
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️  Erro ao fazer parse do JSON: {e}")
                print(f"📝 Resposta bruta: {response_text[:500]}...")
                
                # Retornar resposta parcial
                return {
                    "resposta": "Análise incompleta",
                    "intencoes": [],
                    "raw_response": response_text[:500],
                    "error": str(e)
                }
        
        except APIError as e:
            print(f"❌ Erro na API: {e}")
            raise

    def save_to_json(
        self, 
        data: Dict[str, Any], 
        date: str,
        additional_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Salva dados de preces em arquivo JSON.
        
        Args:
            data: Dados extraídos (com 'resposta' e 'intencoes')
            date: Data no formato YYYY-MM-DD
            additional_fields: Campos adicionais para adicionar (ex: domingo, ano_liturgico, etc)
        
        Returns:
            Caminho do arquivo salvo
        """
        
        # Validar formato de data
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Data inválida. Use YYYY-MM-DD: {date}")
        
        # Montar estrutura final
        output = {
            "data": date,
            "resposta": data.get("resposta", ""),
            "intencoes": data.get("intencoes", []),
            "atualizado_em": datetime.datetime.utcnow().isoformat() + "Z",
        }
        
        # Adicionar campos opcionais
        if "oracao_eucaristica" in data:
            output["oracao_eucaristica"] = data["oracao_eucaristica"]
        
        if "fonte" in data:
            output["fonte"] = data["fonte"]
        
        # Adicionar campos adicionais se fornecidos
        if additional_fields:
            output.update(additional_fields)
        
        # Definir caminho do arquivo
        filename = f"preces_{date}.json"
        filepath = os.path.join(DATA_DIR, filename)
        
        # Salvar arquivo
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Arquivo salvo: {filepath}")
        return filepath


def main():
    """CLI principal"""
    
    parser = argparse.ArgumentParser(
        description="Extrai preces de imagens de folhetos litúrgicos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python3 preces_extractor.py --date 2026-02-22 --images foto1.jpg foto2.jpg
  python3 preces_extractor.py --date 2026-02-22 --images ./folhetos/*.jpg
  python3 preces_extractor.py --date 2026-02-22 --images scan.jpg --domingo "1º Domingo da Quaresma"
        """
    )
    
    parser.add_argument(
        "--date",
        required=True,
        help="Data no formato YYYY-MM-DD (ex: 2026-02-22)"
    )
    
    parser.add_argument(
        "--images",
        nargs="+",
        required=True,
        help="Caminho(s) da(s) imagem(ns) (jpg/png). Suporta wildcards: *.jpg"
    )
    
    parser.add_argument(
        "--domingo",
        help="Nome do domingo (ex: '1º Domingo da Quaresma')"
    )
    
    parser.add_argument(
        "--ano-liturgico",
        help="Ano litúrgico (A, B ou C)"
    )
    
    parser.add_argument(
        "--api-key",
        help="Chave da API Anthropic (default: variável ANTHROPIC_API_KEY)"
    )
    
    parser.add_argument(
        "--output",
        help="Caminho para salvar (default: preces_data/preces_DATA.json)"
    )
    
    args = parser.parse_args()
    
    # Resolver wildcards em image paths
    image_paths = []
    for pattern in args.images:
        matched = glob.glob(pattern)
        if matched:
            image_paths.extend(matched)
        else:
            # Se não for glob, assumir que é um arquivo direto
            if os.path.exists(pattern):
                image_paths.append(pattern)
    
    if not image_paths:
        print(f"❌ Nenhuma imagem encontrada: {args.images}")
        sys.exit(1)
    
    print(f"📁 Imagens encontradas: {len(image_paths)}")
    for img in image_paths:
        print(f"   - {img}")
    
    try:
        # Inicializar extrator
        extractor = PrecesExtractor(api_key=args.api_key)
        
        # Extrair de imagens
        print(f"\n🔄 Extraindo preces de {len(image_paths)} imagem(ns)...")
        extracted_data = extractor.extract_from_images(image_paths, args.date)
        
        print(f"\n✨ Dados extraídos:")
        print(f"   Resposta: {extracted_data.get('resposta', 'N/A')[:60]}...")
        print(f"   Intenções: {len(extracted_data.get('intencoes', []))} encontradas")
        
        # Preparar campos adicionais
        additional = {}
        if args.domingo:
            additional["domingo"] = args.domingo
        if args.ano_liturgico:
            additional["ano_liturgico"] = args.ano_liturgico
        
        # Salvar em JSON
        output_path = args.output or os.path.join(DATA_DIR, f"preces_{args.date}.json")
        
        # Criar diretório se necessário
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        filepath = extractor.save_to_json(extracted_data, args.date, additional)
        
        print(f"\n✅ Conclusão!")
        print(f"   Arquivo: {filepath}")
        print(f"   Data: {args.date}")
        
        sys.exit(0)
    
    except KeyboardInterrupt:
        print("\n⏹️  Interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
