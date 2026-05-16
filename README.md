# Recava Auditor AI (V2.Final)

**Observatorio IBEX 35 – Auditoría Automatizada de Sostenibilidad (NEIS S1 / CSRD)**

Recava Auditor es una plataforma avanzada diseñada para auditar informes de sostenibilidad de forma automatizada, rigurosa y escalable. Utiliza inteligencia artificial de última generación (Gemini 2.5 Pro) y una arquitectura RAG (Retrieval-Augmented Generation) optimizada para evaluar 37 indicadores clave del estándar NEIS S1.

---

## 🚀 Funcionalidades Principales

- **Auditoría Senior Automatizada**: Análisis profundo de PDFs de sostenibilidad con criterios de auditoría senior.
- **Smart Cache Normativo**: Sistema RAG de latencia cero que precarga el corpus legal en RAM.
- **Historial de Auditorías**: Persistencia completa vinculada a Firebase Auth para consultar informes pasados sin re-procesar.
- **Human-in-the-Loop**: Interfaz para validación humana de los hallazgos de la IA.
- **Exportación CSV**: Descarga de resultados estructurados para informes externos.

---

## 🏗️ Arquitectura Técnica (V2.Final)

El sistema opera bajo un modelo de microservicios desplegado en Google Cloud Platform:

- **Frontend**: React + Material UI (MUI).
- **Backend**: Python Flask desplegado en **Cloud Run**.
- **Base de Datos**: 
  - **Firestore**: Almacena resultados, metadatos y configuración del sistema.
  - **Pinecone**: Base vectorial para el corpus legal (utilizada para sincronización semanal).
- **Almacenamiento**: **Google Cloud Storage** para alojar el cache normativo estático.
- **IA**: **Gemini 2.5 Pro** vía Google AI Studio (File API para procesamiento de contexto largo).

---

## 🧠 Motor de Análisis y RAG

### Ciclo de Vida del Análisis
1. **Upload**: El PDF se sube una única vez a la Gemini File API.
2. **Smart Cache**: El sistema carga `normativa_cache.json` (sincronizado semanalmente desde Pinecone a GCS) directamente en la RAM del contenedor.
3. **Paralelismo**: Se evalúan los 37 indicadores de forma concurrente, inyectando en cada petición los 20 fragmentos legales más relevantes para ese indicador específico.
4. **Rigor de Salida**: Cada resultado incluye `cumple` (SI/NO/NA/FE), `evidencia_literal`, `pagina_real` y un `razonamiento` técnico con `ubicacion_contextual`.

### Eficiencia de APIs
| Recurso | Flujo V2.Final |
| :--- | :--- |
| **Pinecone** | **0 llamadas** por documento (uso de caché estática). |
| **Gemini** | **1 upload** de PDF y 37 llamadas de inferencia paralelas. |

---

## 🛠️ Configuración y Despliegue

### Requisitos Previos
- Cuenta en Google Cloud con Cloud Run y Cloud Storage habilitados.
- Instancia de Pinecone con el corpus legal vectorizado.
- API Key de Gemini.
- Proyecto Firebase configurado para autenticación y Firestore.

### Variables de Entorno (`env.yaml`)
El sistema requiere las siguientes claves para operar en producción:
- `GEMINI_API_KEY`: Clave para el modelo 2.5 Pro.
- `PINECONE_API_KEY`: Acceso a la base vectorial.
- `LEGAL_CACHE_BUCKET`: Nombre del bucket GCS para el Smart Cache.

---

## 📂 Estructura del Proyecto
- `/public/admin-panel`: Frontend en React.
- `/src`: Lógica del backend (servicios de auditoría, caché legal y vectores).
- `app.py`: Servidor Flask y endpoints de la API.
- `normativa_cache.json`: (Generado automáticamente) Cache local del corpus experto.