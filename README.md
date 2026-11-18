# SOE y BPI: Analítica de Separación y Presión en la NFL

## Hallazgos principales
- **SOE (Separation Over Expected):** Analizamos 35,132 rutas en 7,541 jugadas de pase (122 juegos), con una separación promedio de 3.74 yardas. El SOE compara la separación real de cada receptor contra la esperada según cobertura y posición; la cobertura que más separación permite es Prevent (5.68 yd).
- **BPI (Blitz Pressure Index):** Fórmula `round((pressure_rate * 100) - (mean_yards_allowed * 5), 2)` sobre 8,556 jugadas (37.1% de presión y 6.56 yd permitidas promedio). Presionar más no siempre compensa: **JAX** presiona en 39.2% pero cede 8.18 yd (**BPI -1.69**), mientras que **BUF** logra 43.0% de presión permitiendo solo 4.61 yd (**BPI +19.90**).
- **Cuándo conviene presionar:** El mayor retorno del BPI se concentra en 3er y 4to down medio/largo (+16.71 a +36.54), mientras que en 1st & Long (-4.03) y 2nd & Medium (-1.79) el blitz sale caro.

## Para quién es
Coordinadores ofensivos y defensivos, analistas de scouting y equipos de analítica deportiva que necesitan evaluar matchups de receptores y decisiones de blitz por down, distancia y cobertura.

## Cómo verlo y ejecutarlo
1. **Backend (FastAPI + datos precalculados en `backend/precomputed/`):**
   ```bash
   .venv\Scripts\python -m uvicorn backend.main:app --port 8000
   ```
2. **Frontend (React + Vite):**
   ```bash
   cd dashboard
   npm install
   npm run dev
   ```
3. Abrir `http://localhost:5173/` en el navegador. El dashboard incluye pestañas interactivas de **SOE** (KPIs, mapa de calor, ranking y cancha NFL 2D con `playDescription`) y **BPI** (tasa de presión por rushers, matriz Down x Distancia y ranking defensivo).

## Pruebas
```bash
.venv\Scripts\python -m pytest
```
(76 pruebas automatizadas pasando.)
