import React from 'react';
import { 
  Card, 
  CardContent, 
  CardMedia, 
  Typography, 
  Box, 
  Chip, 
  CardActions, 
  Button, 
  IconButton, 
  Skeleton, 
  useTheme,
  styled 
} from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import NotificationsIcon from '@mui/icons-material/Notifications';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { motion } from 'framer-motion';
import { Product } from '../../features/products/types';

interface ProductCardProps {
  product: Product;
  isTracked?: boolean;
  onTrack?: (product: Product) => void;
  onUntrack?: (product: Product) => void;
  onSetAlert?: (product: Product) => void;
  onClick?: (product: Product) => void;
  isLoading?: boolean;
  variant?: 'default' | 'compact' | 'list';
}

const MotionCard = styled(motion.div)`
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const StyledCard = styled(Card)`
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
  &:hover {
    transform: translateY(-4px);
    box-shadow: ${({ theme }) => theme.shadows[4]};
  }
`;

const CardWrapper = styled(Box)<{ variant: string }>`
  display: flex;
  flex-direction: ${({ variant }) => variant === 'list' ? 'row' : 'column'};
  height: 100%;
`;

const ContentWrapper = styled(CardContent)<{ variant: string }>`
  flex-grow: 1;
  padding: ${({ variant }) => variant === 'compact' ? '12px' : '16px'};
`;

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  isTracked = false,
  onTrack,
  onUntrack,
  onSetAlert,
  onClick,
  isLoading = false,
  variant = 'default',
}) => {
  const theme = useTheme();
  
  // Formatter les prix
  const formatPrice = (price: number, currency: string = 'EUR') => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency: currency,
    }).format(price);
  };

  // Calculer la variation de prix
  const priceDifference = product.current_price - product.highest_price;
  const priceChangePercentage = (priceDifference / product.highest_price) * 100;
  const isPriceDown = priceDifference < 0;

  // Animation variants
  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.3 } },
    hover: { scale: 1.02, transition: { duration: 0.2 } },
  };

  if (isLoading) {
    return (
      <Card sx={{ height: '100%' }}>
        <Skeleton variant="rectangular" height={140} />
        <CardContent>
          <Skeleton variant="text" width="80%" height={24} />
          <Skeleton variant="text" width="60%" height={20} />
          <Skeleton variant="text" width="40%" height={20} />
        </CardContent>
        <CardActions>
          <Skeleton variant="rectangular" width={80} height={36} />
          <Skeleton variant="circular" width={36} height={36} />
        </CardActions>
      </Card>
    );
  }

  if (variant === 'compact') {
    return (
      <MotionCard
        initial="hidden"
        animate="visible"
        whileHover="hover"
        variants={cardVariants}
      >
        <StyledCard>
          <CardWrapper variant={variant}>
            <CardMedia
              component="img"
              height="120"
              image={product.image_url || "/static/images/placeholder.png"}
              alt={product.title}
            />
            <ContentWrapper variant={variant}>
              <Typography gutterBottom variant="body1" component="div" noWrap>
                {product.title}
              </Typography>
              <Typography variant="h6" color="primary">
                {formatPrice(product.current_price, product.currency)}
              </Typography>
              <Box display="flex" justifyContent="space-between" alignItems="center" mt={1}>
                <Typography variant="caption" color="text.secondary">
                  {product.retailer.name}
                </Typography>
                <IconButton 
                  size="small" 
                  color={isTracked ? "primary" : "default"}
                  onClick={(e) => {
                    e.stopPropagation();
                    isTracked ? onUntrack?.(product) : onTrack?.(product);
                  }}
                >
                  {isTracked ? <FavoriteIcon /> : <FavoriteBorderIcon />}
                </IconButton>
              </Box>
            </ContentWrapper>
          </CardWrapper>
        </StyledCard>
      </MotionCard>
    );
  }

  if (variant === 'list') {
    return (
      <MotionCard
        initial="hidden"
        animate="visible"
        whileHover="hover"
        variants={cardVariants}
      >
        <StyledCard onClick={() => onClick?.(product)}>
          <CardWrapper variant={variant}>
            <CardMedia
              component="img"
              sx={{ width: 120, height: 120, objectFit: 'contain' }}
              image={product.image_url || "/static/images/placeholder.png"}
              alt={product.title}
            />
            <ContentWrapper variant={variant}>
              <Box display="flex" justifyContent="space-between">
                <Box>
                  <Typography gutterBottom variant="subtitle1" component="div">
                    {product.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {product.retailer.name}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="h6" color="primary">
                    {formatPrice(product.current_price, product.currency)}
                  </Typography>
                  <Typography variant="caption" color={isPriceDown ? "success.main" : "error.main"} display="block">
                    {isPriceDown ? "↓" : "↑"} {Math.abs(priceChangePercentage).toFixed(1)}% du prix max
                  </Typography>
                </Box>
              </Box>
              <Box display="flex" justifyContent="flex-end" mt={1}>
                <IconButton 
                  size="small" 
                  onClick={(e) => {
                    e.stopPropagation();
                    window.open(product.url, '_blank');
                  }}
                >
                  <OpenInNewIcon fontSize="small" />
                </IconButton>
                <IconButton 
                  size="small" 
                  color="primary"
                  onClick={(e) => {
                    e.stopPropagation();
                    onSetAlert?.(product);
                  }}
                >
                  <NotificationsIcon fontSize="small" />
                </IconButton>
                <IconButton 
                  size="small" 
                  color={isTracked ? "primary" : "default"}
                  onClick={(e) => {
                    e.stopPropagation();
                    isTracked ? onUntrack?.(product) : onTrack?.(product);
                  }}
                >
                  {isTracked ? <FavoriteIcon /> : <FavoriteBorderIcon />}
                </IconButton>
              </Box>
            </ContentWrapper>
          </CardWrapper>
        </StyledCard>
      </MotionCard>
    );
  }

  return (
    <MotionCard
      initial="hidden"
      animate="visible"
      whileHover="hover"
      variants={cardVariants}
    >
      <StyledCard onClick={() => onClick?.(product)}>
        <CardMedia
          component="img"
          height="180"
          image={product.image_url || "/static/images/placeholder.png"}
          alt={product.title}
          sx={{ objectFit: 'contain', p: 1 }}
        />
        <ContentWrapper variant={variant}>
          <Box height="60px" mb={1}>
            <Typography gutterBottom variant="subtitle1" component="div" sx={{ 
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}>
              {product.title}
            </Typography>
          </Box>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="h6" color="primary">
              {formatPrice(product.current_price, product.currency)}
            </Typography>
            <Chip 
              size="small" 
              color={isPriceDown ? "success" : "error"}
              label={`${Math.abs(priceChangePercentage).toFixed(1)}%`}
            />
          </Box>
          <Typography variant="body2" color="text.secondary">
            {product.retailer.name}
          </Typography>
        </ContentWrapper>
        <CardActions>
          <Button 
            size="small" 
            startIcon={<OpenInNewIcon />}
            onClick={(e) => {
              e.stopPropagation();
              window.open(product.url, '_blank');
            }}
          >
            Voir
          </Button>
          {onSetAlert && (
            <IconButton 
              size="small" 
              color="primary"
              onClick={(e) => {
                e.stopPropagation();
                onSetAlert(product);
              }}
            >
              <NotificationsIcon />
            </IconButton>
          )}
          {(onTrack || onUntrack) && (
            <IconButton 
              size="small" 
              color={isTracked ? "primary" : "default"}
              onClick={(e) => {
                e.stopPropagation();
                isTracked ? onUntrack?.(product) : onTrack?.(product);
              }}
            >
              {isTracked ? <FavoriteIcon /> : <FavoriteBorderIcon />}
            </IconButton>
          )}
        </CardActions>
      </StyledCard>
    </MotionCard>
  );
};