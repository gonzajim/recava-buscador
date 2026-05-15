// src/App.js
import React, { useState, useEffect } from 'react';
import { onAuthStateChanged, signOut } from 'firebase/auth';
import { auth } from './firebase';
import Login from './Login';
import EmpiricalAuditViewer from './EmpiricalAuditViewer';

// --- NUEVAS IMPORTACIONES PARA EL TEMA ---
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from './theme'; // Importamos nuestro tema personalizado
import { AppBar, Toolbar, Typography, Button, Box, Paper } from '@mui/material';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });
    return () => unsubscribe();
  }, []);

  if (loading) {
    return <div>Cargando...</div>;
  }

  // Usamos el ThemeProvider para envolver toda la aplicación
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline /> {/* Normaliza los estilos del navegador */}
      <Box sx={{ flexGrow: 1 }}>
        {/* Cabecera superior */}
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              ReCaVa Buscador
            </Typography>
            {user && (
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Button color="inherit" onClick={() => signOut(auth)}>Cerrar Sesión</Button>
              </Box>
            )}
          </Toolbar>
        </AppBar>

        {/* Contenido Principal */}
        <main>
          {user ? (
            <EmpiricalAuditViewer />
          ) : (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
              <Paper elevation={3} sx={{ padding: 4 }}>
                <Login />
              </Paper>
            </Box>
          )}
        </main>
      </Box>
    </ThemeProvider>
  );
}

export default App;