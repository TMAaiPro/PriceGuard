import json
import logging
import re
from typing import Dict, List, Any, Optional, Union
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def extract_json_from_html(html: str, pattern: str = r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>') -> List[Dict]:
    """
    Extrait les données JSON-LD d'une page HTML
    
    Args:
        html: Contenu HTML de la page
        pattern: Expression régulière pour trouver les balises script JSON-LD
        
    Returns:
        Liste de dictionnaires contenant les données JSON-LD
    """
    results = []
    
    # Trouver tous les blocs JSON-LD
    json_matches = re.finditer(pattern, html, re.DOTALL)
    
    for match in json_matches:
        json_str = match.group(1).strip()
        try:
            data = json.loads(json_str)
            if isinstance(data, dict):
                results.append(data)
            elif isinstance(data, list):
                results.extend(data)
        except json.JSONDecodeError as e:
            logger.warning(f"Erreur de décodage JSON-LD: {str(e)}")
    
    return results

def extract_structured_data(html: str) -> Dict[str, Any]:
    """
    Extrait toutes les données structurées d'une page HTML
    
    Args:
        html: Contenu HTML de la page
        
    Returns:
        Dictionnaire contenant les données structurées par type
    """
    result = {
        'json_ld': extract_json_from_html(html),
        'meta_tags': {}
    }
    
    # Parser la page avec BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extraire les meta tags
    meta_tags = soup.select('meta[property], meta[name]')
    for tag in meta_tags:
        key = tag.get('property', tag.get('name', ''))
        value = tag.get('content', '')
        
        if key and value:
            # Organiser par préfixe (og:, twitter:, etc.)
            prefix = key.split(':')[0] if ':' in key else 'other'
            
            if prefix not in result['meta_tags']:
                result['meta_tags'][prefix] = {}
            
            result['meta_tags'][prefix][key] = value
    
    return result

def extract_price_from_text(text: str) -> Optional[float]:
    """
    Extrait un prix d'une chaîne de texte
    
    Args:
        text: Texte contenant potentiellement un prix
        
    Returns:
        Prix extrait sous forme de float ou None si non trouvé
    """
    if not text:
        return None
    
    # Différents patterns de prix
    patterns = [
        r'(\d+[,.]\d+)\s*€',  # 19,99 €
        r'(\d+[,.]\d+)\s*EUR',  # 19,99 EUR
        r'€\s*(\d+[,.]\d+)',  # € 19,99
        r'EUR\s*(\d+[,.]\d+)',  # EUR 19,99
        r'(\d+[,.]\d+)',  # 19,99 (fallback)
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            price_str = match.group(1).replace(',', '.')
            try:
                return float(price_str)
            except ValueError:
                pass
    
    return None

def clean_html_content(html_content: str) -> str:
    """
    Nettoie le contenu HTML en supprimant les scripts, styles, etc.
    
    Args:
        html_content: Contenu HTML à nettoyer
        
    Returns:
        Contenu HTML nettoyé
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Supprimer les éléments non désirés
    for element in soup(['script', 'style', 'iframe', 'noscript']):
        element.decompose()
    
    return str(soup)
