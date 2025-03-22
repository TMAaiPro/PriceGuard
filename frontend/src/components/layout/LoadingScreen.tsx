import React from 'react';
import { Box, CircularProgress, Typography, useTheme, styled } from '@mui/material';
import { motion } from 'framer-motion';

interface LoadingScreenProps {
  message?: string;
}

const LoadingContainer = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  minHeight: '50vh',
}));

export const LoadingScreen: React.FC<LoadingScreenProps> = ({ message = 'Chargement en cours...' }) => {
  const theme = useTheme();
  
  return (
    <LoadingContainer>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <CircularProgress size={60} thickness={4} />
          <Typography variant="body1" color="text.secondary" sx={{ mt: 3 }}>
            {message}
          </Typography>
        </Box>
      </motion.div>
    </LoadingContainer>
  );
};