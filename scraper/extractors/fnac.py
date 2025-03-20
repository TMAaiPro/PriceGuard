import re
import logging
import json
from typing import Dict, Any, Optional

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class FnacExtractor(BaseExtractor):
    """
    Extracteur spécifique pour les produits Fnac
    """
    
    def extract(self) -> Dict[str, Any]:
        """
        Extrait toutes les informations produit d'une page Fnac
        
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
            'retailer': 'fnac',
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
            '.f-productHeader-Title',
            '.f-productHeader__title',
            'h1.article-title'
        ]
        
        for selector in selectors:
            element = self.soup.select_one(selector)
            if element:
                return element.get_text().strip()
        
        return ""
    
    def extract_price(self) -> float:
        """Extrait le prix actuel du produit"""
        # Essayer d'abord le JSON-LD
        offers = self.extract_json_ld_property('offers')
        if offers:
            if isinstance(offers, dict) and 'price' in offers:
                return float(offers['price'])
            elif isinstance(offers, list) and offers and 'price' in offers[0]:
                return float(offers[0]['price'])
        
        # Essayer différents sélecteurs HTML
        selectors = [
            '.userPrice .finalPrice',
            '.article-price',
            '[data-automation-id="product-price"]'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                price_text = elements[0].get_text().strip()
                return self.clean_price(price_text)
        
        return 0.0
    
    def extract_currency(self) -> str:
        """Extrait la devise du prix"""
        # Essayer d'abord le JSON-LD
        offers = self.extract_json_ld_property('offers')
        if offers:
            if isinstance(offers, dict) and 'priceCurrency' in offers:
                return offers['priceCurrency']
            elif isinstance(offers, list) and offers and 'priceCurrency' in offers[0]:
                return offers[0]['priceCurrency']
        
        # Par défaut EUR pour la Fnac France
        return 'EUR'
    
    def extract_availability(self) -> bool:
        """Vérifie si le produit est disponible"""
        # Essayer d'abord le JSON-LD
        offers = self.extract_json_ld_property('offers')
        if offers:
            if isinstance(offers, dict) and 'availability' in offers:
                return 'InStock' in offers['availability']
            elif isinstance(offers, list) and offers and 'availability' in offers[0]:
                return 'InStock' in offers[0]['availability']
        
        # Vérifier le statut de disponibilité dans le HTML
        unavailable_selectors = [
            '.availabilityMessage.unavailable',
            '.f-buyBox-availabilityStatus--unavailable',
            '.f-productHeader-notAvailableAnymore'
        ]
        
        for selector in unavailable_selectors:
            if self.soup.select_one(selector):
                return False
        
        # Vérifier si un bouton d'achat est présent
        buy_button = self.soup.select_one('.f-buyBox-cta-buyNow, .f-buyBox-cta-book')
        if buy_button:
            return True
        
        # Vérifier les messages de disponibilité positifs
        available_selectors = [
            '.availabilityMessage.available',
            '.f-buyBox-availabilityStatus--available'
        ]
        
        for selector in available_selectors:
            if self.soup.select_one(selector):
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
            '.f-productVisuals-mainImage img',
            '.product-main-visual img',
            '.product-gallery-inner img'
        ]
        
        for selector in selectors:
            img = self.soup.select_one(selector)
            if img:
                # Essayer différents attributs d'image
                for attr in ['data-src', 'src', 'data-lazyload-src']:
                    if img.get(attr):
                        # Vérifier si l'URL est relative
                        src = img[attr]
                        if src.startswith('//'):
                            return f"https:{src}"
                        elif src.startswith('/'):
                            return f"https://www.fnac.com{src}"
                        return src
        
        return ""
    
    def extract_sku(self) -> Optional[str]:
        """Extrait l'identifiant unique du produit"""
        # Essayer d'abord le JSON-LD
        sku = self.extract_json_ld_property('sku')
        if sku:
            return sku
        
        # Chercher dans les attributs de données
        product_element = self.soup.select_one('[data-product-id]')
        if product_element and product_element.get('data-product-id'):
            return product_element['data-product-id']
        
        # Chercher dans l'URL
        sku_match = re.search(r'/([0-9a-zA-Z]+)(?:\.|$)', self.html)
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
            '.f-productOfferDescription',
            '.f-productDescription',
            '.editorial-content',
            '.product-features-list'
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
            '.userPrice .oldPrice',
            '.article-price-reduction',
            '.f-priceBox-priceInfo'
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
        feature_elements = self.soup.select('.f-productCharacteristics li, .full-feature-group li')
        for element in feature_elements:
            text = element.get_text().strip()
            if text:
                features.append(text)
        
        if features:
            metadata['features'] = features
        
        # Extraire les détails techniques
        tech_details = {}
        detail_rows = self.soup.select('.specifications-table tr, .f-productSpecifications-panel tr')
        for row in detail_rows:
            cells = row.select('td')
            if len(cells) >= 2:
                key = cells[0].get_text().strip().rstrip(':')
                val = cells[1].get_text().strip()
                if key and val:
                    tech_details[key] = val
        
        if tech_details:
            metadata['technical_details'] = tech_details
        
        # Extraire la note moyenne et nombre d'avis
        rating_element = self.soup.select_one('.f-reviewsRating-range .visuallyhidden, .f-productHeader-reviewsAverage')
        if rating_element:
            try:
                rating_text = rating_element.get_text().strip()
                rating_match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if rating_match:
                    metadata['rating'] = float(rating_match.group(1).replace(',', '.'))
            except:
                pass
        
        review_count_element = self.soup.select_one('.f-reviewsCount, .f-productHeader-reviewsCount')
        if review_count_element:
            try:
                text = review_count_element.get_text().strip()
                count_match = re.search(r'(\d+)', text)
                if count_match:
                    metadata['review_count'] = int(count_match.group(1))
            except:
                pass
        
        # Extraire le prix de référence/barré
        reference_price_element = self.soup.select_one('.userPrice .oldPrice, .article-old-price')
        if reference_price_element:
            try:
                reference_price_text = reference_price_element.get_text().strip()
                metadata['reference_price'] = self.clean_price(reference_price_text)
            except:
                pass
        
        return metadata
    
    def get_price_selector(self) -> str:
        """Retourne le sélecteur CSS pour l'élément de prix"""
        return '.userPrice .finalPrice, .article-price'
    
    def get_product_detail_selector(self) -> str:
        """Retourne le sélecteur CSS pour la section détail produit"""
        return '.f-productMain, .product-detail'
