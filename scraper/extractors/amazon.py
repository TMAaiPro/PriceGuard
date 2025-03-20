import re
import logging
from typing import Dict, Any, Optional
import json

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class AmazonExtractor(BaseExtractor):
    """
    Extracteur spécifique pour les produits Amazon
    """
    
    def extract(self) -> Dict[str, Any]:
        """
        Extrait toutes les informations produit d'une page Amazon
        
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
            'retailer': 'amazon',
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
            '#productTitle',
            '#title',
            '.product-title-word-break'
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
            '.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '.a-color-price',
            '#price_inside_buybox'
        ]
        
        for selector in selectors:
            elements = self.soup.select(selector)
            if elements:
                # Prendre le premier élément de prix non vide
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
        
        # Rechercher dans les éléments de prix
        price_elements = self.soup.select('.a-price .a-price-symbol')
        if price_elements:
            symbol = price_elements[0].get_text().strip()
            # Mapper les symboles aux codes de devise
            symbol_map = {
                '€': 'EUR',
                '$': 'USD',
                '£': 'GBP',
                '¥': 'JPY'
            }
            return symbol_map.get(symbol, 'EUR')
        
        # Par défaut, supposer EUR pour le marché français
        return 'EUR'
    
    def extract_availability(self) -> bool:
        """Vérifie si le produit est disponible"""
        # Essayer d'abord le JSON-LD
        availability = self.extract_json_ld_property('availability')
        if availability:
            return 'InStock' in availability
        
        # Vérifier le statut de disponibilité dans le HTML
        selectors_available = [
            '#availability .a-color-success',
            '#availability:contains("En stock")',
            '#availability:contains("in stock")'
        ]
        
        for selector in selectors_available:
            if self.soup.select_one(selector):
                return True
        
        # Vérifier les indicateurs de rupture de stock
        selectors_unavailable = [
            '#availability .a-color-price',
            '#availability:contains("indisponible")',
            '#availability:contains("out of stock")',
            '#outOfStock'
        ]
        
        for selector in selectors_unavailable:
            if self.soup.select_one(selector):
                return False
        
        # Vérifier si un bouton d'achat est présent
        buy_button = self.soup.select_one('#add-to-cart-button')
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
            '#landingImage',
            '#imgBlkFront',
            '#main-image',
            '.a-dynamic-image'
        ]
        
        for selector in selectors:
            img = self.soup.select_one(selector)
            if img and img.get('src'):
                return img['src']
            elif img and img.get('data-a-dynamic-image'):
                # Amazon stocke parfois les URLs d'image dans un attribut JSON
                try:
                    images = json.loads(img['data-a-dynamic-image'])
                    if images:
                        # Prendre la première URL
                        return list(images.keys())[0]
                except:
                    pass
        
        return ""
    
    def extract_sku(self) -> Optional[str]:
        """Extrait l'identifiant unique du produit (ASIN pour Amazon)"""
        # Essayer d'abord le JSON-LD
        sku = self.extract_json_ld_property('sku')
        if sku:
            return sku
        
        # Chercher l'ASIN dans les métadonnées
        asin_element = self.soup.select_one('input#ASIN')
        if asin_element and asin_element.get('value'):
            return asin_element['value']
        
        # Chercher l'ASIN dans l'URL
        asin_match = re.search(r'/dp/([A-Z0-9]{10})(?:/|$)', self.html)
        if asin_match:
            return asin_match.group(1)
        
        # Chercher dans le tableau de détails
        detail_elements = self.soup.select('#productDetailsTable .content li')
        for element in detail_elements:
            text = element.get_text().strip()
            if 'ASIN' in text:
                asin_match = re.search(r'ASIN:\s*([A-Z0-9]{10})', text)
                if asin_match:
                    return asin_match.group(1)
        
        return None
    
    def extract_description(self) -> str:
        """Extrait la description du produit"""
        # Essayer d'abord le JSON-LD
        description = self.extract_json_ld_property('description')
        if description:
            return description
        
        # Essayer différents sélecteurs pour la description
        selectors = [
            '#productDescription',
            '#feature-bullets',
            '#aplus',
            '.a-expander-content'
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
            '.savingsPercentage',
            '#dealprice_savings',
            '.priceBlockSavingsString',
            '.deal-badge'
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
        feature_bullets = self.soup.select('#feature-bullets li')
        for bullet in feature_bullets:
            text = bullet.get_text().strip()
            if text:
                features.append(text)
        
        if features:
            metadata['features'] = features
        
        # Extraire les détails techniques
        tech_details = {}
        detail_rows = self.soup.select('.prodDetTable tr')
        for row in detail_rows:
            label = row.select_one('th')
            value = row.select_one('td')
            if label and value:
                key = label.get_text().strip().rstrip(':')
                val = value.get_text().strip()
                if key and val:
                    tech_details[key] = val
        
        if tech_details:
            metadata['technical_details'] = tech_details
        
        # Extraire la note moyenne et nombre d'avis
        rating_element = self.soup.select_one('#acrPopover')
        if rating_element and rating_element.get('title'):
            try:
                rating_text = rating_element['title']
                rating_match = re.search(r'(\d+[.,]?\d*)', rating_text)
                if rating_match:
                    metadata['rating'] = float(rating_match.group(1).replace(',', '.'))
            except:
                pass
        
        review_count_element = self.soup.select_one('#acrCustomerReviewText')
        if review_count_element:
            try:
                text = review_count_element.get_text().strip()
                count_match = re.search(r'(\d+[\s.,]?\d*)', text)
                if count_match:
                    count_str = count_match.group(1).replace(' ', '').replace(',', '').replace('.', '')
                    metadata['review_count'] = int(count_str)
            except:
                pass
        
        # Extraire le prix de référence/barré
        reference_price_elements = self.soup.select('.a-text-strike')
        if reference_price_elements:
            try:
                reference_price_text = reference_price_elements[0].get_text().strip()
                metadata['reference_price'] = self.clean_price(reference_price_text)
            except:
                pass
        
        return metadata
    
    def get_price_selector(self) -> str:
        """Retourne le sélecteur CSS pour l'élément de prix"""
        return '.a-price, #priceblock_ourprice, #priceblock_dealprice'
    
    def get_product_detail_selector(self) -> str:
        """Retourne le sélecteur CSS pour la section détail produit"""
        return '#centerCol, #ppd'
