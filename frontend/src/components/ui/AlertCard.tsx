import React from 'react';
import { 
  Card, 
  CardContent, 
  CardActions, 
  Box, 
  Typography, 
  IconButton, 
  Chip, 
  Button, 
  styled,
  useTheme,
  Skeleton
} from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import DeleteIcon from '@mui/icons-material/Delete';
import { motion } from 'framer-motion';
import { Alert, AlertType } from '../../features/alerts/types';

interface AlertCardProps {
  alert: Alert;
  onMarkAsRead?: (alertId: number) => void;
  onDelete?: (alertId: number) => void;
  onClick?: (alert: Alert) => void;
  isLoading?: boolean;
}

const MotionCard = styled(motion.div)`
  height: 100%;
`;

const StyledCard = styled(Card)<{ isread: string }>`
  height: 100%;
  opacity: ${({ isread }) => isread === 'true' ? 0.8 : 1};
  background-color: ${({ theme, isread }) => isread === 'true' ? theme.palette.background.default : theme.palette.background.paper};
  border-left: 4px solid ${({ theme, isread }) => isread === 'true' ? theme.palette.divider : theme.palette.primary.main};
  transition: all 0.3s ease;
  
  &:hover {
    box-shadow: ${({ theme }) => theme.shadows[3]};
  }
`;

const getAlertTypeColor = (type: AlertType, theme: any) => {
  switch (type) {
    case 'price_drop':
      return theme.palette.success.main;
    case 'target_reached':
      return theme.palette.primary.main;
    case 'back_in_stock':
      return theme.palette.info.main;
    case 'lowest_ever':
      return theme.palette.warning.main;
    default:
      return theme.palette.primary.main;
  }
};

const getAlertTypeLabel = (type: AlertType) => {
  switch (type) {
    case 'price_drop':
      return 'Baisse de prix';
    case 'target_reached':
      return 'Prix cible atteint';
    case 'back_in_stock':
      return 'De retour en stock';
    case 'lowest_ever':
      return 'Prix le plus bas jamais vu';
    default:
      return 'Alerte';
  }
};

export const AlertCard: React.FC<AlertCardProps> = ({
  alert,
  onMarkAsRead,
  onDelete,
  onClick,
  isLoading = false,
}) => {
  const theme = useTheme();
  
  // Formatter les prix
  const formatPrice = (price: number, currency: string = 'EUR') => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency,
    }).format(price);
  };

  // Formatage de la date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('fr-FR', {
      day: 'numeric',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  // Animation variants
  const cardVariants = {
    hidden: { opacity: 0, x: -10 },
    visible: { opacity: 1, x: 0, transition: { duration: 0.3 } },
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" height={28} />
          <Skeleton variant="text" width="100%" height={24} />
          <Skeleton variant="text" width="40%" height={20} />
        </CardContent>
        <CardActions>
          <Skeleton variant="rectangular" width={80} height={36} />
          <Skeleton variant="circular" width={36} height={36} />
        </CardActions>
      </Card>
    );
  }

  return (
    <MotionCard
      initial="hidden"
      animate="visible"
      variants={cardVariants}
    >
      <StyledCard isread={alert.is_read.toString()} onClick={() => onClick?.(alert)}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Chip 
              label={getAlertTypeLabel(alert.type)}
              size="small" 
              style={{ backgroundColor: getAlertTypeColor(alert.type, theme), color: '#fff' }} 
            />
            <Typography variant="caption" color="text.secondary">
              {formatDate(alert.created_at)}
            </Typography>
          </Box>
          
          <Typography variant="subtitle1" component="div" gutterBottom>
            {alert.product.title}
          </Typography>
          
          <Box display="flex" alignItems="center" mb={0.5}>
            <Typography variant="h6" color="success.main" mr={1}>
              {formatPrice(alert.price_point.price)}
            </Typography>
            <Typography variant="body2" color="text.secondary" component="span">
              {alert.previous_price && (
                <>
                  au lieu de <span style={{ textDecoration: 'line-through' }}>{formatPrice(alert.previous_price)}</span>
                </>
              )}
            </Typography>
          </Box>
          
          {alert.percentage_drop && (
            <Typography variant="body2" color="success.main">
              Baisse de {Math.abs(alert.percentage_drop).toFixed(1)}%
            </Typography>
          )}
        </CardContent>
        
        <CardActions>
          <Button 
            size="small" 
            onClick={(e) => {
              e.stopPropagation();
              onClick?.(alert);
            }}
          >
            Voir le produit
          </Button>
          
          <Box flexGrow={1} />
          
          {!alert.is_read && onMarkAsRead && (
            <IconButton 
              size="small" 
              color="primary"
              onClick={(e) => {
                e.stopPropagation();
                onMarkAsRead(alert.id);
              }}
              title="Marquer comme lu"
            >
              <CheckIcon fontSize="small" />
            </IconButton>
          )}
          
          {onDelete && (
            <IconButton 
              size="small" 
              color="error"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(alert.id);
              }}
              title="Supprimer"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          )}
        </CardActions>
      </StyledCard>
    </MotionCard>
  );
};