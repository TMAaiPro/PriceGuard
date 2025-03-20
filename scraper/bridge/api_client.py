import requests
import logging
import json
import os
import time
from typing import Dict, Optional, List, Any, Tuple
from urllib.parse import urlparse
from datetime import datetime

from django.conf import settings
from ..utils.retry import retry_with_exponential_backoff
from ..utils.screenshot import optimize_screenshot

logger = logging.getLogger(__name__)

class PuppeteerApiClient:
    """
    Client API pour communiquer avec un service Puppeteer externe
    """
    
    def __init__(self, api_url=None, api_key=None):
        self.api_url = api_url or settings.PUPPETEER_API_URL
        self.api_key = api_key or settings.PUPPETEER_API_KEY
        self.screenshots_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
        
        # Créer le répertoire de screenshots s'il n'existe pas
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Headers par défaut pour les requêtes
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=2)
    def get_page_content(self, url: str, wait_for: Optional[str] = None, 
                        wait_time: int = 5000) -> Tuple[str, str]:
        """
        Récupère le contenu HTML et JSON-LD d'une page via l'API Puppeteer
        
        Args:
            url: URL de la page à scraper
            wait_for: Sélecteur à attendre avant de considérer la page chargée
            wait_time: Temps d'attente maximal en ms
            
        Returns:
            Tuple contenant (html, json_ld)
        """
        endpoint = f"{self.api_url}/scrape"
        
        payload = {
            'url': url,
            'options': {
                'waitUntil': 'networkidle2',
                'timeout': wait_time
            }
        }
        
        if wait_for:
            payload['waitForSelector'] = wait_for
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get('html', ''), data.get('jsonLd', '[]')
            
        except requests.RequestException as e:
            logger.error(f"Erreur API lors du scraping de {url}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    @retry_with_exponential_backoff(max_retries=3, base_delay=2)
    def take_screenshot(self, url: str, selectors: Dict[str, str] = None) -> Dict[str, str]:
        """
        Prend des captures d'écran d'une page et de sélecteurs spécifiques via l'API
        
        Args:
            url: URL de la page
            selectors: Dictionnaire de sélecteurs à capturer {nom: sélecteur CSS}
            
        Returns:
            Dictionary de chemins d'images {nom: chemin}
        """
        endpoint = f"{self.api_url}/screenshot"
        
        payload = {
            'url': url,
            'options': {
                'waitUntil': 'networkidle2',
                'timeout': 30000
            }
        }
        
        if selectors:
            payload['selectors'] = selectors
        
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            screenshot_paths = {}
            
            # Générer un nom de base pour les fichiers
            domain = urlparse(url).netloc.replace('www.', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"{domain}_{timestamp}"
            
            # Sauvegarder et optimiser les images reçues
            for name, base64_image in data.get('screenshots', {}).items():
                if base64_image:
                    # Convertir base64 en fichier image
                    import base64
                    
                    image_data = base64.b64decode(base64_image.split(',')[1] if ',' in base64_image else base64_image)
                    
                    # Sauvegarder l'image
                    image_path = os.path.join(self.screenshots_dir, f"{base_filename}_{name}.png")
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                    
                    # Optimiser l'image
                    optimized_path = optimize_screenshot(image_path)
                    screenshot_paths[name] = optimized_path
            
            return screenshot_paths
            
        except requests.RequestException as e:
            logger.error(f"Erreur API lors de la capture d'écran de {url}: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response: {e.response.text}")
            raise
    
    def extract_product_data(self, url: str, extractor_class) -> Dict:
        """
        Extrait les données d'un produit en utilisant un extracteur spécifique
        
        Args:
            url: URL du produit
            extractor_class: Classe d'extracteur à utiliser
            
        Returns:
            Dictionnaire contenant les données du produit
        """
        html, json_ld = self.get_page_content(url)
        
        # Créer une instance d'extracteur
        extractor = extractor_class(html, json_ld)
        
        # Extraire les données de base du produit
        product_data = extractor.extract()
        
        # Prendre des captures d'écran si nécessaire
        if extractor.screenshot_selectors:
            try:
                screenshots = self.take_screenshot(url, extractor.screenshot_selectors)
                product_data['screenshots'] = screenshots
            except Exception as e:
                logger.error(f"Erreur lors de la prise de captures d'écran: {str(e)}")
                product_data['screenshots'] = {}
        
        return product_data
