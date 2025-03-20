import time
import random
import logging
import functools
from typing import Callable, TypeVar, Any
import asyncio

from celery import Task

logger = logging.getLogger(__name__)

T = TypeVar('T')

def retry_with_exponential_backoff(max_retries: int = 3, base_delay: float = 1, 
                                  jitter: bool = True, exceptions=(Exception,)):
    """
    Décorateur pour réessayer une fonction avec un délai exponentiel entre les tentatives
    
    Args:
        max_retries: Nombre maximal de tentatives
        base_delay: Délai initial en secondes
        jitter: Ajouter un délai aléatoire pour éviter les effets de tempête
        exceptions: Tuple d'exceptions à intercepter
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            retries = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Échec après {max_retries} tentatives: {str(e)}")
                        raise
                    
                    # Calculer le délai avec backoff exponentiel
                    delay = base_delay * (2 ** (retries - 1))
                    
                    # Ajouter un jitter aléatoire si activé
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(f"Tentative {retries}/{max_retries} échouée: {str(e)}. Nouvelle tentative dans {delay:.2f}s")
                    time.sleep(delay)
        
        return wrapper
    
    return decorator

async def retry_async_with_exponential_backoff(max_retries: int = 3, base_delay: float = 1, 
                                             jitter: bool = True, exceptions=(Exception,)):
    """
    Décorateur pour réessayer une coroutine asyncio avec un délai exponentiel
    
    Args:
        max_retries: Nombre maximal de tentatives
        base_delay: Délai initial en secondes
        jitter: Ajouter un délai aléatoire pour éviter les effets de tempête
        exceptions: Tuple d'exceptions à intercepter
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            retries = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Échec async après {max_retries} tentatives: {str(e)}")
                        raise
                    
                    # Calculer le délai avec backoff exponentiel
                    delay = base_delay * (2 ** (retries - 1))
                    
                    # Ajouter un jitter aléatoire si activé
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    
                    logger.warning(f"Tentative async {retries}/{max_retries} échouée: {str(e)}. Nouvelle tentative dans {delay:.2f}s")
                    await asyncio.sleep(delay)
        
        return wrapper
    
    return decorator

def celery_retry_task(task: Task, exc, countdown=None, **kwargs):
    """
    Fonction helper pour gérer les retries dans les tâches Celery
    
    Args:
        task: Objet tâche Celery
        exc: Exception qui a déclenché le retry
        countdown: Délai avant la prochaine tentative (si None, utilise un backoff exponentiel)
    """
    try:
        task_id = task.request.id
        retries = task.request.retries
        max_retries = task.max_retries
        
        if countdown is None:
            # Backoff exponentiel avec jitter
            countdown = (2 ** retries) * 60 + random.uniform(0, 30)
        
        logger.warning(f"Tâche {task_id} échouée (tentative {retries}/{max_retries}): {str(exc)}. "
                     f"Nouvelle tentative dans {countdown:.2f}s")
        
        # Lever l'exception pour que Celery gère le retry
        raise task.retry(exc=exc, countdown=countdown, **kwargs)
        
    except task.MaxRetriesExceededError:
        logger.error(f"Tâche a atteint le nombre maximal de tentatives: {str(exc)}")
        raise
