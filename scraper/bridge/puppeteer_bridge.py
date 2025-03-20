import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union
import json
import os
from datetime import datetime
from urllib.parse import urlparse

from pyppeteer import launch
from pyppeteer.browser import Browser
from pyppeteer.page import Page
from pyppeteer.errors import TimeoutError, NetworkError, PageError

from django.conf import settings
from ..utils.retry import retry_async_with_exponential_backoff
from ..utils.screenshot import optimize_screenshot, crop_screenshot

logger = logging.getLogger(__name__)

class PuppeteerBridge:
    """
    Bridge pour interagir avec Puppeteer depuis Django
    en utilisant pyppeteer comme interface Python
    """
    
    def __init__(self, headless=True, proxy=None, user_agent=None):
        self.headless = headless
        self.proxy = proxy
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        self.browser: Optional[Browser] = None
        self.screenshots_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
        
        # Créer le répertoire de screenshots s'il n'existe pas
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    async def start_browser(self) -> Browser:
        """Démarre une instance de navigateur Puppeteer"""
        if self.browser is None or not self.browser.isConnected():
            args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1920,1080',
            ]
            
            if self.proxy:
                args.append(f'--proxy-server={self.proxy}')
            
            self.browser = await launch(
                headless=self.headless,
                args=args,
                ignoreHTTPSErrors=True,
                slowMo=20,  # ralentir légèrement pour éviter détection bot
            )
        
        return self.browser
    
    async def close_browser(self):
        """Ferme le navigateur s'il est ouvert"""
        if self.browser and self.browser.isConnected():
            await self.browser.close()
            self.browser = None
    
    @retry_async_with_exponential_backoff(max_retries=3, base_delay=2)
    async def get_page_content(self, url: str, wait_for: Optional[str] = None, 
                              wait_time: int = 5000) -> Tuple[str, str]:
        """
        Récupère le contenu HTML et JSON-LD d'une page
        
        Args:
            url: URL de la page à scraper
            wait_for: Sélecteur à attendre avant de considérer la page chargée
            wait_time: Temps d'attente maximal en ms
            
        Returns:
            Tuple contenant (html, json_ld)
        """
        browser = await self.start_browser()
        page: Page = await browser.newPage()
        
        try:
            # Configurer l'user-agent et la taille de la fenêtre
            await page.setUserAgent(self.user_agent)
            await page.setViewport({'width': 1920, 'height': 1080})
            
            # Intercepter les requêtes d'images et de police pour les bloquer
            await page.setRequestInterception(True)
            
            async def intercept_request(request):
                if request.resourceType in ['image', 'font', 'media']:
                    await request.abort()
                else:
                    await request.continue_()
            
            page.on('request', intercept_request)
            
            # Naviguer vers l'URL
            response = await page.goto(url, {
                'waitUntil': 'networkidle2',
                'timeout': wait_time
            })
            
            if not response.ok:
                logger.error(f"Erreur de chargement de la page {url}: {response.status}")
                raise PageError(f"Page error: {response.status}")
            
            # Attendre un sélecteur spécifique si fourni
            if wait_for:
                await page.waitForSelector(wait_for, {'timeout': wait_time})
            
            # Extraire le HTML complet
            html = await page.content()
            
            # Extraire les données JSON-LD
            json_ld = await page.evaluate('''() => {
                const jsonLdScripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                return jsonLdScripts.map(script => script.textContent);
            }''')
            
            return html, json.dumps(json_ld)
            
        except TimeoutError as e:
            logger.error(f"Timeout lors du chargement de {url}: {str(e)}")
            raise
        except NetworkError as e:
            logger.error(f"Erreur réseau pour {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors du scraping de {url}: {str(e)}")
            raise
        finally:
            await page.close()
    
    async def take_screenshot(self, url: str, selectors: Dict[str, str] = None) -> Dict[str, str]:
        """
        Prend des captures d'écran d'une page et de sélecteurs spécifiques
        
        Args:
            url: URL de la page
            selectors: Dictionnaire de sélecteurs à capturer {nom: sélecteur CSS}
            
        Returns:
            Dictionary de chemins d'images {nom: chemin}
        """
        browser = await self.start_browser()
        page = await browser.newPage()
        screenshot_paths = {}
        
        try:
            # Configurer la page
            await page.setUserAgent(self.user_agent)
            await page.setViewport({'width': 1920, 'height': 1080})
            
            # Naviguer vers l'URL
            await page.goto(url, {
                'waitUntil': 'networkidle2',
                'timeout': 30000
            })
            
            # Générer un nom de base pour les fichiers
            domain = urlparse(url).netloc.replace('www.', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            base_filename = f"{domain}_{timestamp}"
            
            # Capture d'écran de la page entière
            full_path = os.path.join(self.screenshots_dir, f"{base_filename}_full.png")
            await page.screenshot({'path': full_path, 'fullPage': True})
            
            # Optimiser l'image
            optimized_path = optimize_screenshot(full_path)
            screenshot_paths['full_page'] = optimized_path
            
            # Capturer des éléments spécifiques si fournis
            if selectors:
                for name, selector in selectors.items():
                    try:
                        # Attendre que le sélecteur soit disponible
                        await page.waitForSelector(selector, {'timeout': 5000})
                        
                        # Obtenir les dimensions de l'élément
                        rect = await page.evaluate(f"""() => {{
                            const element = document.querySelector('{selector}');
                            if (element) {{
                                const {{x, y, width, height}} = element.getBoundingClientRect();
                                return {{x, y, width, height}};
                            }}
                            return null;
                        }}""")
                        
                        if rect:
                            # Prendre une capture d'écran de l'élément
                            element_path = os.path.join(self.screenshots_dir, f"{base_filename}_{name}.png")
                            await page.screenshot({
                                'path': element_path,
                                'clip': {
                                    'x': rect['x'],
                                    'y': rect['y'],
                                    'width': rect['width'],
                                    'height': rect['height']
                                }
                            })
                            
                            # Optimiser l'image
                            optimized_element_path = optimize_screenshot(element_path)
                            screenshot_paths[name] = optimized_element_path
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la capture de l'élément '{name}': {str(e)}")
            
            return screenshot_paths
            
        except Exception as e:
            logger.error(f"Erreur lors de la prise de captures d'écran de {url}: {str(e)}")
            raise
        finally:
            await page.close()
    
    async def extract_product_data(self, url: str, extractor_class) -> Dict:
        """
        Extrait les données d'un produit en utilisant un extracteur spécifique
        
        Args:
            url: URL du produit
            extractor_class: Classe d'extracteur à utiliser
            
        Returns:
            Dictionnaire contenant les données du produit
        """
        html, json_ld = await self.get_page_content(url)
        
        # Créer une instance d'extracteur
        extractor = extractor_class(html, json_ld)
        
        # Extraire les données de base du produit
        product_data = extractor.extract()
        
        # Prendre des captures d'écran si nécessaire
        if extractor.screenshot_selectors:
            try:
                screenshots = await self.take_screenshot(url, extractor.screenshot_selectors)
                product_data['screenshots'] = screenshots
            except Exception as e:
                logger.error(f"Erreur lors de la prise de captures d'écran: {str(e)}")
                product_data['screenshots'] = {}
        
        return product_data
    
    def run_async(self, coroutine):
        """
        Exécute une coroutine asyncio dans un environnement synchrone
        Utile pour appeler des méthodes async depuis Django/Celery
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coroutine)
    
    def __del__(self):
        """Assure que le navigateur est fermé lors de la destruction de l'objet"""
        if self.browser:
            asyncio.get_event_loop().run_until_complete(self.close_browser())
