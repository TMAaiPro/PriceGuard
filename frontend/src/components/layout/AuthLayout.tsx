import React from 'react';
import { Box, Container, Paper, Typography, useTheme, styled } from '@mui/material';
import { motion } from 'framer-motion';

const AuthBackground = styled(Box)(({ theme }) => ({
  minHeight: '100vh',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: theme.spacing(2),
  background: `linear-gradient(45deg, ${theme.palette.primary.main} 0%, ${theme.palette.primary.dark} 100%)`,
}));

const AuthPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  borderRadius: 16,
  boxShadow: theme.shadows[10],
  [theme.breakpoints.up('sm')]: {
    padding: theme.spacing(6),
  },
}));

const MotionContainer = styled(motion.div)({
  width: '100%',
  maxWidth: 450,
}));

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle?: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({ children, title, subtitle }) => {
  const theme = useTheme();
  
  const containerVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } },
  };
  
  return (
    <AuthBackground>
      <MotionContainer
        initial="hidden"
        animate="visible"
        variants={containerVariants}
      >
        <AuthPaper>
          <Box textAlign="center" mb={4}>
            <Typography variant="h4" component="h1" gutterBottom>
              {title}
            </Typography>
            {subtitle && (
              <Typography variant="body1" color="text.secondary">
                {subtitle}
              </Typography>
            )}
          </Box>
          
          {children}
        </AuthPaper>
      </MotionContainer>
    </AuthBackground>
  );
};