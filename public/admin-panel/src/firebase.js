// public/admin-panel/src/firebase.js
import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";
import { getFunctions, httpsCallable } from "firebase/functions";

const firebaseConfig = {
  apiKey: "AIzaSyBY2jzaOYNl_9gMNKO2hVoVkIYqY_X5oiI",
  authDomain: "recava-buscador.firebaseapp.com",
  projectId: "recava-buscador",
  storageBucket: "recava-buscador.firebasestorage.app",
  messagingSenderId: "613261744640",
  appId: "1:613261744640:web:d4a22517ba12d8ebce96e5"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
// Firestore exportado con la instancia correcta del app
export const firestoreDb = getFirestore(app);

const functions = getFunctions(app, 'europe-west1');

// Exportamos las funciones callable
export const getChatHistory = httpsCallable(functions, 'getChatHistory');
export const updateExpertResponse = httpsCallable(functions, 'updateExpertResponse');