import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  Box, 
  Chip, 
  Skeleton,
  useTheme,
  styled
} from '@mui/material';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import TrendingFlatIcon from '@mui/icons-material/TrendingFlat';
import { motion } from 'framer-motion';

interface PriceCardProps {
  currentPrice: number;
  previousPrice?: number;
  lowestPrice?: number;
  highestPrice?: number;
  currency?: string;
  showTrend?: boolean;
  isLoading?: boolean;
  variant?: 'default' | 'compact';
}

const MotionCard = styled(motion.div)`
  width: 100%;
  height: 100%;
`;

export const PriceCard: React.FC<PriceCardProps> = ({
  currentPrice,
  previousPrice,
  lowestPrice,
  highestPrice,
  currency = 'EUR',
  showTrend = true,
  isLoading = false,
  variant = 'default',
}) => {
  const theme = useTheme();
  
  // Calculer la variation de prix
  const priceDifference = previousPrice ? currentPrice - previousPrice : 0;
  const priceChangePercentage = previousPrice ? (priceDifference / previousPrice) * 100 : 0;
  
  // Déterminer la tendance (hausse, baisse, stable)
  const trend = priceDifference === 0 
    ? 'stable' 
    : priceDifference < 0 
      ? 'down' 
      : 'up';
  
  // Formatter les prix
  const formatPrice = (price: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency,
    }).format(price);
  };

  // Formatter les pourcentages
  const formatPercentage = (percentage: number) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'percent',
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }).format(Math.abs(percentage) / 100);
  };

  // Composant pour la tendance
  const TrendIcon = () => {
    switch (trend) {
      case 'up':
        return <TrendingUpIcon color="error" />;
      case 'down':
        return <TrendingDownIcon color="success" />;
      case 'stable':
      default:
        return <TrendingFlatIcon color="action" />;
    }
  };

  // Animation variants
  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent>
          <Skeleton variant="text" width="60%" height={40} />
          <Skeleton variant="text" width="40%" height={24} />
          <Skeleton variant="text" width="80%" height={24} />
        </CardContent>
      </Card>
    );
  }

  if (variant === 'compact') {
    return (
      <MotionCard
        initial="hidden"
        animate="visible"
        variants={cardVariants}
      >
        <Card>
          <CardContent>
            <Typography variant="h5" component="div" color="text.primary">
              {formatPrice(currentPrice)}
            </Typography>
            {showTrend && previousPrice && (
              <Box display="flex" alignItems="center" mt={0.5}>
                <TrendIcon />
                <Typography 
                  variant="body2" 
                  color={trend === 'down' ? 'success.main' : trend === 'up' ? 'error.main' : 'text.secondary'}
                  ml={0.5}
                >
                  {formatPercentage(priceChangePercentage)}
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </MotionCard>
    );
  }

  return (
    <MotionCard
      initial="hidden"
      animate="visible"
      variants={cardVariants}
    >
      <Card>
        <CardContent>
          <Typography variant="h4" component="div" color="text.primary" gutterBottom>
            {formatPrice(currentPrice)}
          </Typography>
          
          {showTrend && previousPrice && (
            <Box display="flex" alignItems="center" mb={1}>
              <Chip 
                icon={<TrendIcon />}
                label={`${formatPercentage(priceChangePercentage)} ${trend === 'down' ? 'Baisse' : trend === 'up' ? 'Hausse' : 'Stable'}`}
                color={trend === 'down' ? 'success' : trend === 'up' ? 'error' : 'default'}
                size="small"
                variant="filled"
              />
              <Typography variant="body2" color="text.secondary" ml={1}>
                {previousPrice && `Prix précédent: ${formatPrice(previousPrice)}`}
              </Typography>
            </Box>
          )}
          
          <Box mt={2}>
            {lowestPrice && (
              <Typography variant="body2" color="text.secondary">
                Prix le plus bas: <b>{formatPrice(lowestPrice)}</b>
              </Typography>
            )}
            
            {highestPrice && (
              <Typography variant="body2" color="text.secondary">
                Prix le plus haut: <b>{formatPrice(highestPrice)}</b>
              </Typography>
            )}
          </Box>
        </CardContent>
      </Card>
    </MotionCard>
  );
};