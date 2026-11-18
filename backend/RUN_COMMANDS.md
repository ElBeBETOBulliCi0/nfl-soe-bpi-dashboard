# Comandos para ejecutar el backend SOE/BPI

Todos los comandos son para **Windows CMD** y se ejecutan desde la carpeta `hackathon-unam`.

## Notas previas

- La revisión estática encontró que `.venv` tiene `numpy` y `pandas`, pero **no** `fastapi`, `pydantic`, `httpx`, `pytest` ni `uvicorn`.
- Verifica si faltan con:

  ```cmd
  .venv\Scripts\python -c "import fastapi, pytest, httpx, uvicorn"
  ```

  Si falla, instala tú mismo la lista fijada en `.hackathon\requirements.txt` (es el stack fijado del proyecto, no una dependencia nueva):

  ```cmd
  .venv\Scripts\python -m pip install -r .hackathon\requirements.txt
  ```

  o, con uv:

  ```cmd
  uv pip install -r .hackathon\requirements.txt
  ```

- El paso de construcción (paso 1) espera encontrar en `data/` los CSV `games.csv`, `players.csv`, `plays.csv` y `pffScoutingData.csv`, además de la carpeta `data/tracking/` con archivos `tracking_*.csv`. Si falta alguno, el script imprime las rutas faltantes, termina con código 1 y no escribe nada.
- Los archivos `backend/precomputed/*.csv` **sí** deben subirse al repositorio (commit). La carpeta `data/tracking/` está ignorada por git y **no** se sube.
- La API arranca aunque no existan los CSV precalculados; en ese caso responde con resultados vacíos y `data_loaded: false`.

## 1. Entrar a la carpeta del proyecto

```cmd
cd /d C:\Users\thega\OneDrive\Documents\NFLTRIPLET\plantilla-hackathon\hackathon-unam
```

## 2. Construir los CSV precalculados

```cmd
.venv\Scripts\python scripts\build_precomputed.py
```

Genera `backend/precomputed/soe_routes.csv`, `play_release_frames.csv` y `bpi_plays.csv`.

Vuelve a ejecutarlo tras actualizar el código del dashboard: añade la columna `playDescription` a `bpi_plays.csv`. Sin regenerar los CSV la API sigue funcionando, pero `playDescription` es `null`.

## 3. Ejecutar las pruebas

```cmd
.venv\Scripts\python -m pytest backend/tests -q
```

## 4. Levantar (o reiniciar) la API

Si uvicorn ya corre, detenlo con `Ctrl+C` y vuelve a ejecutar:

```cmd
.venv\Scripts\python -m uvicorn backend.main:app --port 8000
```

Deja este CMD abierto: la API debe seguir en el puerto 8000 para que el dashboard funcione.

## 5. Probar los endpoints (en un segundo CMD)

Abre otro CMD, entra a la carpeta con `cd /d` como en el punto 1 y ejecuta:

```cmd
curl http://localhost:8000/health
curl http://localhost:8000/api/health
curl http://localhost:8000/api/filters
```

`/health` y `/api/health` deben devolver el mismo cuerpo, con `status: "ok"` y `data_loaded` en `true` si los CSV precalculados existen.

## 6. Levantar el dashboard React (en un segundo CMD)

Con la API del paso 4 corriendo, abre otro CMD y ejecuta:

```cmd
cd /d C:\Users\thega\OneDrive\Documents\NFLTRIPLET\plantilla-hackathon\hackathon-unam\dashboard
npm run dev
```

- Solo si no existe la carpeta `dashboard\node_modules` (hoy no existe), ejecuta antes una vez `npm install`.
- Vite imprime la URL local, normalmente `http://localhost:5173/`. Ábrela en el navegador.
- Vite redirige `/api` a `http://localhost:8000` (ver `dashboard/vite.config.ts`), así que no hace falta configurar nada más.
- Opcional: `npm run typecheck` revisa los tipos de TypeScript.
