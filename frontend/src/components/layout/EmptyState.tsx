import React from 'react';
import { Box, Typography, Button, Paper, useTheme, styled } from '@mui/material';
import { motion } from 'framer-motion';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const EmptyContainer = styled(Paper)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  padding: theme.spacing(8),
  textAlign: 'center',
  borderRadius: 16,
}));

const IconContainer = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(3),
  color: theme.palette.text.secondary,
  '& svg': {
    fontSize: 80,
  }
}));

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon, action }) => {
  const theme = useTheme();
  
  const containerVariants = {
    hidden: { opacity: 0, scale: 0.9 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.5 } },
  };
  
  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <EmptyContainer>
        {icon && <IconContainer>{icon}</IconContainer>}
        
        <Typography variant="h5" gutterBottom>
          {title}
        </Typography>
        
        <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 500, mb: 4 }}>
          {description}
        </Typography>
        
        {action && (
          <Button
            variant="contained"
            color="primary"
            onClick={action.onClick}
          >
            {action.label}
          </Button>
        )}
      </EmptyContainer>
    </motion.div>
  );
};