import base64
import hashlib
import json
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.utils.crypto import constant_time_compare, salted_hmac

# Clé secrète pour la signature des tokens, à définir dans settings.py
TOKEN_SECRET_KEY = getattr(settings, 'NOTIFICATION_TOKEN_SECRET_KEY', settings.SECRET_KEY)

def generate_unsubscribe_token(user):
    """
    Génère un token sécurisé pour le désabonnement aux notifications
    
    Args:
        user: Utilisateur pour lequel générer le token
        
    Returns:
        str: Token encodé en base64
    """
    # Données à inclure dans le token
    payload = {
        'user_id': str(user.id),
        'email': user.email,
        'exp': int((datetime.now() + timedelta(days=30)).timestamp()),  # Expire après 30 jours
        'iat': int(datetime.now().timestamp()),
    }
    
    # Sérialiser les données
    payload_json = json.dumps(payload).encode('utf-8')
    
    # Encoder en base64
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode('utf-8').rstrip('=')
    
    # Générer la signature
    signature = salted_hmac(
        "unsubscribe_token",
        payload_b64,
        secret=TOKEN_SECRET_KEY,
        algorithm="sha256"
    ).hexdigest()
    
    # Renvoyer le token (payload + signature)
    return f"{payload_b64}.{signature}"

def verify_unsubscribe_token(token):
    """
    Vérifie et décode un token de désabonnement
    
    Args:
        token: Token à vérifier
        
    Returns:
        dict: Données du token si valide, None sinon
    """
    try:
        # Séparer le payload et la signature
        parts = token.split('.')
        if len(parts) != 2:
            return None
            
        payload_b64, signature = parts
        
        # Vérifier la signature
        expected_signature = salted_hmac(
            "unsubscribe_token",
            payload_b64,
            secret=TOKEN_SECRET_KEY,
            algorithm="sha256"
        ).hexdigest()
        
        if not constant_time_compare(signature, expected_signature):
            return None
        
        # Décoder le payload
        payload_json = base64.urlsafe_b64decode(payload_b64 + '=' * (4 - len(payload_b64) % 4))
        payload = json.loads(payload_json.decode('utf-8'))
        
        # Vérifier l'expiration
        if 'exp' in payload and payload['exp'] < time.time():
            return None
            
        return payload
        
    except Exception:
        return None
