# Gambit - Pronósticos de Fútbol ⚽

Gambit es una aplicación web que proporciona pronósticos de partidos de fútbol utilizando datos de la API de Football-Data.org.

## Capturas de Pantalla

### Página Principal
![Página Principal](https://github.com/user-attachments/assets/e34cc883-49f7-4ca2-bfa0-1c349579293d)

### Página de Búsqueda
![Búsqueda de Partidos](https://github.com/user-attachments/assets/0feeb59b-56bf-44c6-8891-0638d3f39072)

## Características

- 📊 Pronósticos de resultados de partidos
- ⚽ Predicción de goles, corners, faltas y tarjetas
- 🔍 Búsqueda de partidos por liga y fecha
- 🏆 Soporte para múltiples ligas:
  - Champions League (CL)
  - Premier League (PL)
  - La Liga (PD)
  - Bundesliga (BL1)
  - Euro Championship (EC)
  - Serie A (SA)
  - UEFA Europa League (EL)
  - Copa Libertadores (CLI)

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/rsojo/Gambit.git
cd Gambit
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura la API key:
Copia el archivo `.env.example` a `.env` y actualiza la API key si es necesario:
```bash
cp .env.example .env
# Edita .env con tu API key de football-data.org
```

Nota: El repositorio ya incluye una API key funcional para propósitos de demostración.

## Uso

1. Inicia la aplicación:
```bash
python app.py
```

2. Abre tu navegador y visita:
```
http://localhost:5000
```

## Estructura del Proyecto

```
Gambit/
├── app.py              # Aplicación principal Flask
├── requirements.txt    # Dependencias de Python
├── .env               # Variables de entorno (API keys)
├── templates/         # Plantillas HTML
│   ├── base.html
│   ├── index.html
│   ├── search.html
│   └── league.html
└── static/            # Archivos estáticos
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

## API Endpoints

- `GET /` - Página principal con pronósticos de hoy
- `GET /search` - Página de búsqueda de partidos
- `GET /leagues/<league_code>` - Pronósticos por liga
- `GET /api/predictions` - API para obtener pronósticos (JSON)
- `GET /api/match/<match_id>` - Pronóstico de un partido específico (JSON)

## Tecnologías Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML5, CSS3, JavaScript
- **API**: Football-Data.org
- **Estilo**: CSS personalizado con gradientes y diseño responsivo

## Fuentes de Datos

- [Football-Data.org API](https://www.football-data.org/documentation/quickstart) - Datos de partidos y estadísticas

## Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.