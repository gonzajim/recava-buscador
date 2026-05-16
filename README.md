# Recava Auditor AI (V3.1)

**Observatorio IBEX 35 – Auditoría Automatizada de Sostenibilidad (NEIS S1 / CSRD)**

Recava Auditor es una plataforma avanzada diseñada para auditar informes de sostenibilidad de forma automatizada, rigurosa y escalable. Utiliza inteligencia artificial de última generación (Gemini 2.5 Pro) y una arquitectura RAG (Retrieval-Augmented Generation) optimizada para evaluar matrices de indicadores personalizables bajo los estándares NEIS S1 y CSRD/ESRS.

---

## 🚀 Funcionalidades Principales

- **Auditoría Senior Automatizada**: Análisis profundo de PDFs de sostenibilidad con criterios de auditoría senior, rigor normativo y prohibición explícita de extrapolación.
- **Matriz de Indicadores Dinámica**: Los usuarios pueden subir un Excel/CSV propio para sobrescribir los 37 indicadores base y auditar cualquier marco normativo.
- **Smart Cache Normativo**: Sistema RAG de latencia cero que precarga el corpus legal en RAM. Sincronización semanal automática desde Pinecone a GCS.
- **Background Warm-up al Login**: Al iniciar sesión, el sistema comprueba y regenera la caché en segundo plano para que la auditoría sea instantánea.
- **Historial de Auditorías**: Persistencia completa vinculada a Firebase Auth con snapshot de los indicadores usados para integridad histórica.
- **Human-in-the-Loop**: Interfaz para validación humana de los hallazgos de la IA.
- **Exportación CSV**: Descarga de resultados estructurados para informes externos.

---

## 🏗️ Arquitectura Técnica (V3.1)

El sistema opera bajo un modelo de microservicios desplegado en Google Cloud Platform:

- **Frontend**: React + Material UI (MUI).
- **Backend**: Python Flask desplegado en **Cloud Run** (4Gi RAM / 2 CPU).
- **Base de Datos**:
  - **Firestore**: Resultados, metadatos, configuración de sistema y matrices de indicadores por usuario (`usuarios_config`).
  - **Pinecone**: Base vectorial del corpus legal (solo para sincronización semanal).
- **Almacenamiento**: **Google Cloud Storage** — cache normativo global (`normativa_cache.json`) y por usuario (`normativa_cache_[UID].json`).
- **IA**: **Gemini 2.5 Pro** vía Gemini File API (una sola carga por documento, referenciado por `file_uri` en los N análisis).

---

## 🧠 Motor de Análisis y RAG

### Ciclo de Vida de un Análisis
1. **Login**: El sistema comprueba en segundo plano si la caché normativa del usuario está vigente (<7 días) y la regenera si es necesario.
2. **Upload**: El PDF se sube una única vez a la Gemini File API (`file_uri` reutilizado en todas las consultas).
3. **Smart Cache**: El sistema carga desde GCS los 20 fragmentos legales por indicador directamente en RAM.
4. **Paralelismo Adaptativo**: Se evalúan los N indicadores (37 base o los del Excel personalizado) de forma concurrente.
5. **Rigor de Salida**: Cada resultado incluye `cumple` (SI/NO/NA/FE), `evidencia_literal`, `pagina_real` y un `razonamiento` técnico con `ubicacion_contextual`.
6. **Snapshot Histórico**: El documento de Firestore guarda una copia inmutable de los indicadores usados para proteger la integridad del historial.

### Eficiencia de APIs
| Recurso | Flujo V3.1 |
| :--- | :--- |
| **Pinecone** | **0 llamadas** por auditoría (caché global o por usuario). Solo 37+ llamadas una vez a la semana. |
| **Gemini** | **1 upload** de PDF + N llamadas de inferencia paralelas. |

---

## 📋 Matriz de Indicadores Personalizable

Los usuarios pueden subir su propia matriz en formato `.xlsx` o `.csv` con las columnas obligatorias:

| Columna | Descripción |
| :--- | :--- |
| `NEIS` | Identificador de la norma (ej. `S1-9`) |
| `Epígrafe` | Referencia del apartado técnico (ej. `66. a)`) |
| `Indicador` | Pregunta de divulgación explícita |

Al subir el archivo, el sistema invalida la caché previa y regenera en background los 20 chunks normativos para cada nuevo indicador.

---

## 🛠️ API Endpoints

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `POST` | `/api/audit/empirical` | Lanza una nueva auditoría (multipart PDF) |
| `GET` | `/api/audit/empirical` | Lista las auditorías del usuario (historial) |
| `GET` | `/api/audit/empirical/<id>` | Detalle completo de una auditoría |
| `PATCH` | `/api/audit/empirical/<id>/feedback` | Valida manualmente un indicador (IA Acertó) |
| `GET` | `/api/indicators` | Lista los indicadores activos del usuario |
| `POST` | `/api/indicators/upload` | Sube una nueva matriz Excel/CSV de indicadores |
| `POST` | `/api/admin/sync-legal-cache` | Fuerza sincronización del corpus normativo |
| `GET` | `/health` | Health check del servicio |

---

## 🛠️ Configuración y Despliegue

### Variables de Entorno (`env.yaml`)
- `GEMINI_API_KEY`: Clave para Gemini 2.5 Pro.
- `PINECONE_API_KEY`: Acceso a la base vectorial.
- `LEGAL_CACHE_BUCKET`: Nombre del bucket GCS para el Smart Cache.

### Requisitos Previos
- Cuenta en Google Cloud con Cloud Run y Cloud Storage habilitados.
- Bucket GCS creado: `gs://recava-buscador-legal-cache`
- Instancia de Pinecone con el corpus legal vectorizado.
- Proyecto Firebase configurado (Auth + Firestore).

---

## 📂 Estructura del Proyecto

```
recava-buscador/
├── app.py                      # Servidor Flask y endpoints de la API
├── src/
│   ├── config.py               # Configuración base y clientes externos
│   ├── empirical_audit_service.py  # Motor de auditoría asíncrono (V3.1)
│   ├── legal_cache_service.py  # Smart Cache RAG (global + por usuario)
│   ├── indicator_service.py    # Gestión de matrices de indicadores dinámicas
│   └── vector_service.py       # Integración con Pinecone
├── public/admin-panel/         # Frontend React + MUI
├── requirements.txt            # Dependencias Python
└── env.yaml                    # Variables de entorno (producción)
```