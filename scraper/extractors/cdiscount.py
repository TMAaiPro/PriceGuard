import re
import logging
from typing import Dict, Any, Optional

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class CdiscountExtractor(BaseExtractor):
    """
    Extracteur spécifique pour les produits Cdiscount
    """
    
    def extract(self) -> Dict[str, Any]:
        """
        Extrait toutes les informations produit d'une page Cdiscount
        
        Returns:
            Dictionnaire avec toutes les données produit
        """
        return {
            'title': self.extract_title(),
            'price': self.extract_price(),
            'currency': self.extract_currency(),
            'in_stock': self.extract_availability(),
            'image_url': self.extract_image_url(),
            'sku': self.extract_sku(),
            'description': self.extract_description(),
            'retailer': 'cdiscount',
            'is_deal': self.is_deal(),
            'metadata': self.extract_metadata()
        }
    
    def extract_title(self) -> str:
        """Extrait le titre du produit"""
        # Essayer d'abord le JSON-LD
        title = self.extract_json_ld_property('name')
        if title:
            return title
        
        # Essayer différents sélecteurs HTML
        selectors = [
            'h1[itemprop="name"]',
            '.fpDesCol h1',
            '.prdtBTit'
        ]
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_price(self) -> float:
        """Extrait le prix actuel du produit"""
        # Essayer d'abord le JSON-LD
        price = self.extract_json_ld_property('price')
        if price and isinstance(price, (int, float)):
            return float(price)
        
        # Essayer d'extraire du JSON-LD comme chaîne
        price_str = self.extract_json_ld_property('price')
        if price_str and isinstance(price_str, str):
            return self.clean_price(price_str)
        
        # Essayer différents sélecteurs HTML
        selectors = [
            '.fpPrice',
            '[itemprop="price"]',
            '.prdtPrice',
            '.price .current'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                for element in elements:
                    price_text = element.get_text().strip()
                    if price_text:
                        return self.clean_price(price_text)
        
        return 0.0
    
    def extract_currency(self) -> str:
        """Extrait la devise du prix"""
        # Essayer d'abord le JSON-LD
        currency = self.extract_json_ld_property('priceCurrency')
        if currency:
            return currency
        
        # Par défaut pour Cdiscount France
        return 'EUR'
    
    def extract_availability(self) -> bool:
        """Vérifie si le produit est disponible"""
        # Essayer d'abord le JSON-LD
        availability = self.extract_json_ld_property('availability')
        if availability:
            return 'InStock' in availability
        
        # Vérifier le statut de disponibilité dans le HTML
        unavailable_selectors = [
            '.fpHD-Availability .red',
            '.prdtBOff',
            '.prdtBUn',
            '[data-availability="0"]'
        ]
        
        for selector in unavailable_selectors:
            if self.soup.select_one(selector):
                return False
        
        # Vérifier si un bouton d'achat est présent
        buy_button = self.soup.select_one('#fpAddToCart, .btGreen, .prdtBAdd')
        if buy_button:
            return True
        
        # Par défaut, supposer disponible
        return True
    
    def extract_image_url(self) -> str:
        """Extrait l'URL de l'image principale du produit"""
        # Essayer d'abord le JSON-LD
        image = self.extract_json_ld_property('image')
        if image:
            if isinstance(image, str):
                return image
            elif isinstance(image, list) and image:
                return image[0]
        
        # Essayer différents sélecteurs pour les images
        selectors = [
            '[itemprop="image"]',
            '.jsPrdtBImgS',
            '.prdtBloc img',
            '.prdtVisual img'
        ]
        
        for selector in selectors:
            img = self.soup.select_one(selector)
            if img and img.get('src'):
                return img['src']
            elif img and img.get('data-src'):
                return img['data-src']
        
        return ""
    
    def extract_sku(self) -> Optional[str]:
        """Extrait l'identifiant unique du produit"""
        # Essayer d'abord le JSON-LD
        sku = self.extract_json_ld_property('sku')
        if sku:
            return sku
        
        # Chercher dans les attributs de données
        product_element = self.soup.select_one('[data-sku], [data-productid]')
        if product_element:
            if product_element.get('data-sku'):
                return product_element['data-sku']
            elif product_element.get('data-productid'):
                return product_element['data-productid']
        
        # Chercher dans l'URL
        sku_match = re.search(r'[/-]([a-zA-Z0-9]{5,})[/-]', self.html)
        if sku_match:
            return sku_match.group(1)
        
        return None
    
    def extract_description(self) -> str:
        """Extrait la description du produit"""
        # Essayer d'abord le JSON-LD
        description = self.extract_json_ld_property('description')
        if description:
            return description
        
        # Essayer différents sélecteurs pour la description
        selectors = [
            '[itemprop="description"]',
            '.fpDesc',
            '.prdtDesc',
            '#fpContent'
        ]
        
        descriptions = []
        for selector in selectors:
            elements = self.soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                if text:
                    descriptions.append(text)
        
        return ' '.join(descriptions)
    
    def is_deal(self) -> bool:
        """Vérifie si le produit est en promotion"""
        deal_selectors = [
            '.fpOldP',
            '.prdtPrSt',
            '.prdtStrike',
            '.discountSticker'
        ]
        
        for selector in deal_selectors:
            if self.soup.select_one(selector):
                return True
        
        return False
    
    def extract_metadata(self) -> Dict[str, Any]:
        """Extrait les métadonnées supplémentaires"""
        metadata = {}
        
        # Extraire les caractéristiques produit
        features = []
        feature_elements = self.soup.select('.fpTech li, .fpDesc li, .prdtBInfoList li')
        for element in feature_elements:
            text = element.get_text().strip()
            if text:
                features.append(text)
        
        if features:
            metadata['features'] = features
        
        # Extraire la note moyenne et nombre d'avis
        rating_element = self.soup.select_one('.fpAbt-review, .prdtBIRANotes')
        if rating_element:
            try:
                rating_text = rating_element.get_text().strip()
                rating_match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if rating_match:
                    metadata['rating'] = float(rating_match.group(1).replace(',', '.'))
            except:
                pass
        
        review_count_element = self.soup.select_one('.fpAbt-review-count, .prdtBIRACounts')
        if review_count_element:
            try:
                text = review_count_element.get_text().strip()
                count_match = re.search(r'(\d+)', text)
                if count_match:
                    metadata['review_count'] = int(count_match.group(1))
            except:
                pass
        
        # Extraire le prix de référence/barré
        reference_price_element = self.soup.select_one('.fpOldP, .prdtPrSt')
        if reference_price_element:
            try:
                reference_price_text = reference_price_element.get_text().strip()
                metadata['reference_price'] = self.clean_price(reference_price_text)
            except:
                pass
        
        return metadata
    
    def get_price_selector(self) -> str:
        """Retourne le sélecteur CSS pour l'élément de prix"""
        return '.fpPrice, .prdtPrice'
    
    def get_product_detail_selector(self) -> str:
        """Retourne le sélecteur CSS pour la section détail produit"""
        return '.fpBlk, .prdtBILDetails'
