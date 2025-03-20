import os
import logging
from typing import Optional
from PIL import Image
import io
import base64
from django.conf import settings

logger = logging.getLogger(__name__)

def optimize_screenshot(image_path: str, quality: int = 85, max_width: int = 1200) -> str:
    """
    Optimise une capture d'écran pour réduire sa taille
    
    Args:
        image_path: Chemin vers l'image à optimiser
        quality: Qualité de compression JPEG (0-100)
        max_width: Largeur maximale de l'image
        
    Returns:
        Chemin vers l'image optimisée
    """
    try:
        # Ouvrir l'image
        with Image.open(image_path) as img:
            # Redimensionner si nécessaire
            width, height = img.size
            if width > max_width:
                ratio = height / width
                new_width = max_width
                new_height = int(max_width * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Créer un chemin pour l'image optimisée
            filename, ext = os.path.splitext(image_path)
            optimized_path = f"{filename}_optimized.jpg"
            
            # Convertir en RGB si nécessaire (pour les images avec transparence)
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  # 3 is the alpha channel
                img = background
            
            # Sauvegarder en JPEG optimisé
            img.save(optimized_path, 'JPEG', quality=quality, optimize=True)
            
            # Vérifier si la taille a été réduite
            original_size = os.path.getsize(image_path)
            optimized_size = os.path.getsize(optimized_path)
            
            if optimized_size < original_size:
                logger.info(f"Image optimisée: {original_size/1024:.1f}KB -> {optimized_size/1024:.1f}KB ({100*optimized_size/original_size:.1f}%)")
                return optimized_path
            else:
                logger.info("L'optimisation n'a pas réduit la taille, utilisation de l'image originale")
                os.remove(optimized_path)
                return image_path
                
    except Exception as e:
        logger.error(f"Erreur lors de l'optimisation de l'image {image_path}: {str(e)}")
        return image_path

def crop_screenshot(image_path: str, x: int, y: int, width: int, height: int) -> Optional[str]:
    """
    Découpe une capture d'écran selon les coordonnées spécifiées
    
    Args:
        image_path: Chemin vers l'image à découper
        x, y: Coordonnées du coin supérieur gauche
        width, height: Largeur et hauteur de la zone à découper
        
    Returns:
        Chemin vers l'image découpée ou None en cas d'erreur
    """
    try:
        # Ouvrir l'image
        with Image.open(image_path) as img:
            # Découper l'image
            cropped = img.crop((x, y, x + width, y + height))
            
            # Créer un chemin pour l'image découpée
            filename, ext = os.path.splitext(image_path)
            cropped_path = f"{filename}_cropped{ext}"
            
            # Sauvegarder l'image découpée
            cropped.save(cropped_path)
            
            return cropped_path
            
    except Exception as e:
        logger.error(f"Erreur lors du découpage de l'image {image_path}: {str(e)}")
        return None

def base64_to_image(base64_str: str, image_name: str) -> Optional[str]:
    """
    Convertit une image base64 en fichier
    
    Args:
        base64_str: Chaîne base64 de l'image
        image_name: Nom du fichier image à créer
        
    Returns:
        Chemin vers l'image sauvegardée ou None en cas d'erreur
    """
    try:
        # Nettoyer la chaîne base64 si nécessaire
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        # Décoder le base64
        image_data = base64.b64decode(base64_str)
        
        # Créer le chemin de l'image
        screenshots_dir = os.path.join(settings.MEDIA_ROOT, 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        
        image_path = os.path.join(screenshots_dir, image_name)
        
        # Sauvegarder l'image
        with open(image_path, 'wb') as f:
            f.write(image_data)
        
        return image_path
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion base64 en image: {str(e)}")
        return None

def create_thumbnail(image_path: str, width: int = 300) -> Optional[str]:
    """
    Crée une miniature de l'image
    
    Args:
        image_path: Chemin vers l'image originale
        width: Largeur de la miniature
        
    Returns:
        Chemin vers la miniature ou None en cas d'erreur
    """
    try:
        # Ouvrir l'image
        with Image.open(image_path) as img:
            # Calculer les nouvelles dimensions en conservant le ratio
            w, h = img.size
            ratio = h / w
            new_width = width
            new_height = int(width * ratio)
            
            # Redimensionner l'image
            thumbnail = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Créer un chemin pour la miniature
            filename, ext = os.path.splitext(image_path)
            thumb_path = f"{filename}_thumb{ext}"
            
            # Sauvegarder la miniature
            thumbnail.save(thumb_path)
            
            return thumb_path
            
    except Exception as e:
        logger.error(f"Erreur lors de la création de la miniature pour {image_path}: {str(e)}")
        return None
