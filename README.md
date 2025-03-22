# PriceGuard Frontend

PriceGuard est une application de suivi de prix pour e-commerce permettant aux utilisateurs de suivre les variations de prix de leurs produits préférés et de recevoir des alertes lors des baisses de prix.

## Technologies utilisées

- **React 18** - Bibliothèque frontend
- **TypeScript** - Superset JavaScript typé
- **Material-UI** - Bibliothèque de composants UI
- **Redux Toolkit** - Gestion d'état
- **RTK Query** - Gestion des requêtes API
- **Recharts** - Visualisations de données
- **Framer Motion** - Animations

## Structure actuelle du projet 

```
/src
  /assets            # Images, icônes et ressources statiques (dossier créé mais pas encore rempli)
  
  /components        # Composants partagés et réutilisables
    /ui              # Composants d'interface utilisateur génériques
      PriceCard.tsx  # Affichage des informations de prix
      ProductCard.tsx # Carte de produit avec actions
      AlertCard.tsx  # Affichage des alertes
    
    /layout          # Composants de mise en page
      MainLayout.tsx # Layout principal avec navigation
      AuthLayout.tsx # Layout pour pages d'authentification
      PageHeader.tsx # En-tête des pages avec titre et actions
      EmptyState.tsx # État vide pour les listes
      LoadingScreen.tsx # Écran de chargement
    
    /charts          # Composants de visualisation
      PriceHistoryChart.tsx  # Graphique d'historique de prix
      PricePredictionChart.tsx # Graphique de prédiction de prix
      PriceTrendsChart.tsx   # Graphique de tendances de prix
      DashboardSummaryChart.tsx # Graphique résumé pour tableau de bord
  
  /features          # Architecture basée sur les fonctionnalités (feature-based)
    /auth            # Authentification
      /api
        authApi.ts   # API endpoints d'authentification
      authSlice.ts   # Slice Redux pour l'authentification
      types.ts       # Types TypeScript pour l'authentification
    
    /products        # Fonctionnalité produits
      /api
        productsApi.ts # API endpoints des produits
      productsSlice.ts # Slice Redux pour les produits
      types.ts        # Types TypeScript pour les produits
    
    /alerts          # Fonctionnalité alertes
      /api
        alertsApi.ts  # API endpoints des alertes
      alertsSlice.ts  # Slice Redux pour les alertes
      types.ts        # Types TypeScript pour les alertes
    
    /analytics       # Fonctionnalité analyse
      /api
        analyticsApi.ts # API endpoints d'analyse
      analyticsSlice.ts # Slice Redux pour l'analyse
      types.ts         # Types TypeScript pour l'analyse
    
    /profile         # Fonctionnalité profil utilisateur
      /api
        profileApi.ts  # API endpoints du profil
      profileSlice.ts  # Slice Redux pour le profil
      types.ts         # Types TypeScript pour le profil
    
    /ui              # Fonctionnalité UI globale
      uiSlice.ts     # Slice Redux pour l'UI (drawer, thème, notifications)
  
  /hooks             # Hooks personnalisés
    useAppDispatch.ts # Hook pour le dispatch Redux
    useAppSelector.ts # Hook pour le selector Redux
    useAuth.ts        # Hook pour l'authentification
    useAlerts.ts      # Hook pour les alertes
    useProducts.ts    # Hook pour les produits
    useAnalytics.ts   # Hook pour l'analyse
    useNotifications.ts # Hook pour les notifications
    index.ts          # Export de tous les hooks
  
  /services          # Services partagés
    /api             # Configuration de base de l'API
      apiService.ts  # Service API configuré avec RTK Query
  
  /store             # Configuration Redux
    store.ts         # Configuration du store Redux
    rootReducer.ts   # Combinaison des reducers
  
  /theme             # Configuration du thème Material-UI
    theme.ts         # Thème principal
    palette.ts       # Palette de couleurs
    typography.ts    # Configuration de la typographie
    components.ts    # Style des composants Material-UI
  
  /pages             # Pages principales de l'application
    /login
      LoginPage.tsx  # Page de connexion
    /register
      RegisterPage.tsx # Page d'inscription
    /forgot-password
      ForgotPasswordPage.tsx # Page de récupération de mot de passe
    /dashboard
      DashboardPage.tsx # Page tableau de bord
    /products
      ProductsPage.tsx  # Page de gestion des produits
      ProductDetailPage.tsx # Page de détail d'un produit
```

## Ce qui est actuellement implémenté :

1. **Structure du projet** complète avec architecture feature-based
2. **Configuration du thème** Material-UI personnalisé pour PriceGuard
3. **Configuration Redux** avec Redux Toolkit et middleware API RTK Query
4. **Slices Redux** pour toutes les principales fonctionnalités
5. **Services API** avec RTK Query pour tous les endpoints
6. **Hooks personnalisés** pour faciliter l'utilisation de Redux
7. **Composants UI principaux** :
   - Composants de cartes (PriceCard, ProductCard, AlertCard)
   - Composants de mise en page (MainLayout, AuthLayout, etc.)
   - Composants de graphiques avec Recharts
8. **Pages principales** :
   - Pages d'authentification (Login, Register, ForgotPassword)
   - Page de tableau de bord (Dashboard)
   - Pages de gestion des produits (liste et détail)
9. **Animations** avec Framer Motion sur plusieurs composants
10. **Responsive design** avec adaptation pour différentes tailles d'écran

## Structure complète visée (roadmap)

```
/src
  /assets                  # Images, icônes et ressources statiques
    /images                # Images et logos
    /icons                 # Icônes personnalisées
    /animations            # Fichiers d'animation Lottie
  
  /components              # Composants partagés et réutilisables
    /ui                    # Composants d'interface utilisateur génériques
    /layout                # Composants de mise en page
    /charts                # Composants de visualisation
    /forms                 # Composants de formulaire
    /animations            # Composants d'animation
  
  /features                # Architecture basée sur les fonctionnalités
    /auth                  # Authentification
    /products              # Fonctionnalité produits
    /alerts                # Fonctionnalité alertes
    /analytics             # Fonctionnalité analyse
    /profile               # Fonctionnalité profil utilisateur
    /ui                    # Fonctionnalité UI globale
  
  /hooks                   # Hooks personnalisés
  
  /services                # Services partagés
    /api                   # Configuration de base de l'API
    /notifications         # Service de notifications
    /storage               # Service de stockage local
    /analytics             # Service d'analytique
    /theme                 # Service de thème
  
  /store                   # Configuration Redux
  
  /theme                   # Configuration du thème Material-UI
  
  /types                   # Types globaux
  
  /utils                   # Fonctions utilitaires
  
  /pages                   # Pages principales de l'application
    /login
    /register
    /forgot-password
    /reset-password
    /dashboard
    /products
    /alerts
    /analytics
    /settings
    /error
  
  /routes                  # Configuration des routes
  
  /tests                   # Tests
    /unit                  # Tests unitaires
    /integration           # Tests d'intégration
    /e2e                   # Tests end-to-end
  
  /config                  # Configuration de l'application
  
  App.tsx                  # Composant racine de l'application
  index.tsx                # Point d'entrée
```

## Pages à développer en priorité

1. ✅ **Pages d'authentification** (Login, Register, ForgotPassword)
2. ✅ **Dashboard** - Vue d'ensemble avec statistiques et produits suivis
3. ✅ **Pages de produits** - Liste et détails des produits
4. **Pages d'alertes** - Gestion des alertes de prix
5. **Pages d'analytics** - Analyse de prix et insights
6. **Pages de paramètres** - Profil utilisateur et préférences

## Composants prioritaires à développer

1. ✅ **Composants de carte** - PriceCard, ProductCard, AlertCard
2. ✅ **Graphiques** - PriceHistoryChart, PricePredictionChart, etc.
3. ✅ **Layouts** - MainLayout, AuthLayout
4. **Formulaires** - ProductForm, AlertForm, etc.
5. **Composants d'animation** - Transitions entre les pages

## Comment contribuer

1. Cloner le dépôt
2. Installer les dépendances avec `npm install`
3. Lancer l'application en mode développement avec `npm start`
4. Exécuter les tests avec `npm test`
5. Créer une pull request pour vos modifications