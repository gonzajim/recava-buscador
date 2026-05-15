import React, { useState } from 'react';
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  signInWithPopup 
} from 'firebase/auth';
import { auth, googleProvider } from './firebase';
import { 
  Box, 
  Button, 
  TextField, 
  Typography, 
  Divider, 
  Alert,
  Link
} from '@mui/material';
import GoogleIcon from '@mui/icons-material/Google';

function Auth() {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleEmailAuth = async (e) => {
    e.preventDefault();
    setError('');
    try {
      if (isRegister) {
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
    } catch (err) {
      console.error(err);
      setError(mapErrorToSpanish(err.code));
    }
  };

  const handleGoogleAuth = async () => {
    setError('');
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.error(err);
      setError('Error al conectar con Google. Inténtalo de nuevo.');
    }
  };

  const mapErrorToSpanish = (code) => {
    switch (code) {
      case 'auth/email-already-in-use': return 'Este email ya está registrado.';
      case 'auth/invalid-email': return 'Email no válido.';
      case 'auth/weak-password': return 'La contraseña es muy débil (mínimo 6 caracteres).';
      case 'auth/user-not-found': return 'Usuario no encontrado.';
      case 'auth/wrong-password': return 'Contraseña incorrecta.';
      default: return 'Error en la autenticación. Revisa tus datos.';
    }
  };

  return (
    <Box sx={{ maxWidth: 400, width: '100%' }}>
      <Typography variant="h4" align="center" gutterBottom fontWeight="bold">
        {isRegister ? 'Crear Cuenta' : 'Bienvenido'}
      </Typography>
      <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 3 }}>
        {isRegister ? 'Únete a ReCaVa para empezar a auditar' : 'Accede a tu panel de control'}
      </Typography>

      <form onSubmit={handleEmailAuth}>
        <TextField
          fullWidth
          label="Email"
          variant="outlined"
          margin="normal"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <TextField
          fullWidth
          label="Contraseña"
          variant="outlined"
          margin="normal"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        
        {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}

        <Button
          fullWidth
          variant="contained"
          color="primary"
          type="submit"
          size="large"
          sx={{ mt: 3, mb: 2, py: 1.5, borderRadius: 2 }}
        >
          {isRegister ? 'Registrarse' : 'Iniciar Sesión'}
        </Button>
      </form>

      <Box sx={{ my: 2, display: 'flex', alignItems: 'center' }}>
        <Divider sx={{ flexGrow: 1 }} />
        <Typography variant="body2" sx={{ px: 2, color: 'text.secondary' }}>O</Typography>
        <Divider sx={{ flexGrow: 1 }} />
      </Box>

      <Button
        fullWidth
        variant="outlined"
        startIcon={<GoogleIcon />}
        onClick={handleGoogleAuth}
        size="large"
        sx={{ mb: 3, py: 1.5, borderRadius: 2, color: 'text.primary', borderColor: 'divider' }}
      >
        Continuar con Google
      </Button>

      <Typography variant="body2" align="center">
        {isRegister ? '¿Ya tienes cuenta?' : '¿No tienes cuenta?'}
        {' '}
        <Link 
          component="button" 
          onClick={() => setIsRegister(!isRegister)}
          sx={{ fontWeight: 'bold', textDecoration: 'none' }}
        >
          {isRegister ? 'Inicia Sesión' : 'Regístrate aquí'}
        </Link>
      </Typography>
    </Box>
  );
}

export default Auth;
