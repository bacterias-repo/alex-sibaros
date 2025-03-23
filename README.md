# Proyecto Dashboard

Este es un proyecto de dashboard interactivo, donde puedes visualizar datos y ejecutar diferentes funcionalidades. A continuación, se detallan los pasos necesarios para ejecutar este proyecto en tu máquina local.

## Requisitos

1. **Python**: Asegúrate de tener Python 3.6 o superior instalado en tu sistema.

## Pasos de Instalación

1. **Instalar Python**:
   Si aún no tienes Python, puedes descargarlo desde [python.org](https://www.python.org/downloads/).

2. **Crear un entorno virtual**:
   Para asegurarte de que las dependencias no afecten a otros proyectos en tu máquina, se recomienda crear un entorno virtual. En tu terminal, navega al directorio donde está el proyecto y ejecuta:
   ```bash
   python -m venv venv

3. **Activar el entorno virtual**:
- **Windows**:
  ```bash
     python -m venv venv
     venv\Scripts\activate

4. **Ejecutar la aplicación**:
   ```bash
      python app.py


## Estructura de Archivos

```plaintext
dashboard/
├── static/
│   ├── css/
│   │   └── styles.css
│   ├── images/
│   └── js/
│       └── scripts.js
├── templates/
│   └── dashboard/
│       ├── components/
│       │   ├── cooking/
│       │   ├── fermentation/
│       │   ├── filtros_coccion/
│       │   ├── filtros_fermentacion/
│       │   ├── generar_reportes/
│       │   ├── reporte/
│       │   └── reporte_imprimir/
│       └── home/
├── routes.py
└── app.py

