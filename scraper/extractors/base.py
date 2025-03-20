from abc import ABC, abstractmethod
import logging
from typing import Dict, Optional, List, Any
import json
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """
    Classe de base pour tous les extracteurs de sites e-commerce
    """
    
    def __init__(self, html: str, json_ld: str = None):
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        
        # Parsing des données JSON-LD
        self.json_ld_data = []
        if json_ld:
            try:
                # json_ld peut être une string contenant une liste de strings JSON
                json_strings = json.loads(json_ld)
                for js in json_strings:
                    try:
                        self.json_ld_data.append(json.loads(js))
                    except:
                        logger.warning(f"Impossible de parser un JSON-LD: {js[:100]}...")
            except:
                logger.warning(f"Format JSON-LD invalide: {json_ld[:100]}...")
        
        # Les sélecteurs pour les captures d'écran - à redéfinir dans les sous-classes
        self.screenshot_selectors = {
            'price_element': self.get_price_selector(),
            'product_detail': self.get_product_detail_selector()
        }
    
    @abstractmethod
    def extract(self) -> Dict[str, Any]:
        """
        Extrait toutes les informations produit du HTML et JSON-LD
        
        Returns:
            Dictionnaire avec toutes les données produit
        """
        pass
    
    @abstractmethod
    def extract_title(self) -> str:
        """Extrait le titre du produit"""
        pass
    
    @abstractmethod
    def extract_price(self) -> float:
        """Extrait le prix actuel du produit"""
        pass
    
    @abstractmethod
    def extract_currency(self) -> str:
        """Extrait la devise du prix"""
        pass
    
    @abstractmethod
    def extract_availability(self) -> bool:
        """Vérifie si le produit est disponible"""
        pass
    
    @abstractmethod
    def extract_image_url(self) -> str:
        """Extrait l'URL de l'image principale du produit"""
        pass
    
    @abstractmethod
    def extract_sku(self) -> Optional[str]:
        """Extrait l'identifiant unique du produit (SKU)"""
        pass
    
    @abstractmethod
    def extract_description(self) -> str:
        """Extrait la description du produit"""
        pass
    
    @abstractmethod
    def extract_metadata(self) -> Dict[str, Any]:
        """Extrait les métadonnées supplémentaires"""
        pass
    
    @abstractmethod
    def get_price_selector(self) -> str:
        """Retourne le sélecteur CSS pour l'élément de prix"""
        pass
    
    @abstractmethod
    def get_product_detail_selector(self) -> str:
        """Retourne le sélecteur CSS pour la section détail produit"""
        pass
    
    def extract_json_ld_property(self, property_name: str) -> Any:
        """
        Extrait une propriété des données JSON-LD
        
        Args:
            property_name: Nom de la propriété à extraire
            
        Returns:
            Valeur de la propriété ou None si non trouvée
        """
        for item in self.json_ld_data:
            # Check pour un objet Product
            if item.get('@type') == 'Product' and property_name in item:
                return item[property_name]
            
            # Check pour un ProductOffer imbriqué
            if item.get('@type') == 'Product' and 'offers' in item:
                offers = item['offers']
                if isinstance(offers, dict) and property_name in offers:
                    return offers[property_name]
                elif isinstance(offers, list):
                    for offer in offers:
                        if property_name in offer:
                            return offer[property_name]
        
        return None
    
    def clean_price(self, price_str: str) -> float:
        """
        Nettoie et convertit une chaîne de prix en nombre flottant
        
        Args:
            price_str: Chaîne de caractères représentant un prix
            
        Returns:
            Prix sous forme de nombre flottant
        """
        if not price_str:
            return 0.0
        
        # Supprimer tous les caractères non numériques sauf le point et la virgule
        import re
        cleaned = re.sub(r'[^\d.,]', '', price_str.strip())
        
        # Remplacer la virgule par un point si nécessaire
        cleaned = cleaned.replace(',', '.')
        
        # Gérer le cas des multiples points (ex: 1.234.56)
        if cleaned.count('.') > 1:
            parts = cleaned.split('.')
            if len(parts[-1]) == 2:  # Format avec séparateur des milliers
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
        
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Impossible de convertir le prix: {price_str}")
            return 0.0
