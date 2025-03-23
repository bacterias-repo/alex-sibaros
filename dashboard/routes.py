from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session
from datetime import datetime, timedelta
import os

dashboard_bp = Blueprint('dashboard', __name__,
                         template_folder='templates',
                         static_folder='static',
                         static_url_path='/dashboard/static')

@dashboard_bp.route('/')
def home():
    return render_template('dashboard/home.html')


# Configuración de MongoDB
from pymongo import MongoClient
URI = 'mongodb://alexbalboa:pk72l8Cy65K8HmO8@cluster0-shard-00-01.pw11t.mongodb.net:27017,cluster0-shard-00-02.pw11t.mongodb.net:27017,cluster0-shard-00-00.pw11t.mongodb.net:27017/?ssl=true'
client = MongoClient(URI)
db = client['sibaros_db']

coleccion_productos_en_coccion = db['productos_en_coccion']
coleccion_coccion = db['coccion']
coleccion_productos_en_batches = db['productos_en_batches']
coleccion_fermentacion = db['fermentacion']
coleccion_historic_batches = db['historic_batches']
coleccion_productos = db['productos']
coleccion_historic_coccion = db['historic_coccion']

# Crear un Blueprint para la API
api_bp = Blueprint('api', __name__, url_prefix='/api',
                         template_folder='templates',
                         static_folder='static',
                         static_url_path='/dashboard/static')

@api_bp.route('/productos', methods=['GET'])
def obtener_productos():
    # Recuperamos los productos de la colección
    productos = db.productos.find({}, {"_id": 0, "nombre": 1})
    nombres_productos = [producto['nombre'] for producto in productos]
    return jsonify(nombres_productos)

@api_bp.route('/actualizar_producto_y_serie', methods=['POST'])
def actualizar_producto_y_serie():
    data = request.json
    
    fermentador = data.get('fermentador')
    producto = data.get('producto')
    codigo_serie = data.get('codigo_serie')

    imagen_producto = coleccion_productos.find_one({'nombre': producto})['imagen']
    
    if not (fermentador and producto and codigo_serie):
        return jsonify({"success": False, "message": "Faltan datos obligatorios"}), 400
    
    try:
        batch_id = int(fermentador[-1])  # Extrae el número de batch desde el ID del fermentador
        
        # Encuentra el documento correspondiente en la colección
        producto_batch = db.productos_en_batches.find_one({"batch": batch_id})
        
        if not producto_batch:
            return jsonify({"success": False, "message": "Batch no encontrado"}), 404

        historic_batch = producto_batch.copy()
        historic_batch.pop('_id', None)
        db.historic_batches.insert_one(historic_batch)
        
        # Mantener el proceso existente
        proceso = {
            "coccion": {
                "hervor": 1,
                "macerador": 1,
                "coccion": 1
            },
            "fermentacion": {
                "fermentacion": 1,
                "colonizacion": 0,
                "reproduccion": 0,
                "lactancia": 0
            }
        }
        
        # Actualizar los campos necesarios
        db.productos_en_batches.update_one(
            {"batch": batch_id},
            {"$set": {
                "nombre_producto": producto,
                "codigo_serie": codigo_serie,
                "proceso": proceso,
                "fecha_inicio": datetime.now().strftime('%Y-%m-%d'),
                "fecha_fin": None,
                "lote": f"{producto.replace(' ', '')}_Lote",
                "imagen_producto_path": imagen_producto
            }}
        )
        
        return jsonify({"success": True, "message": "Producto y código de serie actualizados"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route('/actualizar_producto_y_serie_planta_coccion', methods=['POST'])
def actualizar_producto_y_serie_planta_coccion():
    # {'etapa': 'hervor', 'producto': 'Dale color', 'codigo_serie': '1'}
    data = request.json
    etapa = data.get('etapa')
    producto = data.get('producto')
    codigo_serie = data.get('codigo_serie')


    imagen_producto = coleccion_productos.find_one({'nombre': producto})['imagen']

    producto_coccion = coleccion_productos_en_coccion.find_one({"etapa": etapa})

    historic_data = producto_coccion.copy()
    historic_data.pop('_id', None)
    coleccion_historic_coccion.insert_one(historic_data)

    coleccion_productos_en_coccion.update_one(
            {"etapa": etapa},
            {"$set": {
                "nombre_producto": producto,
                "lote": f"{producto.replace(' ', '')}_Lote",
                "codigo_serie": codigo_serie,
                "imagen_producto_path": imagen_producto
            }}
        )

    return jsonify({"success": True, "message": "Producto y código de serie actualizados"})


# Lotes activos en los BATCHS
@api_bp.route('/get_productos_en_batches', methods=['GET'])
def get_productos_en_batches():
    documento_lotes_activos = coleccion_productos_en_batches.find()
    batches_activos = []
    imagenes_productos = []
    lotes_activos = []
    nombres_productos = []
    codigos_series = []
    etapas_procesos = {'coccion': [], 'fermentacion': []}
    
    for doc in documento_lotes_activos:
        lotes_activos.append(doc['lote'])
        batches_activos.append(doc['batch'])
        imagenes_productos.append(url_for('dashboard.static', filename=doc['imagen_producto_path']).replace('"', '').replace("'", ''))
        nombres_productos.append(doc['nombre_producto'])
        codigos_series.append(doc['codigo_serie'])
        
        procesos = doc['proceso']
        for proceso, etapas in procesos.items():
            if proceso == 'coccion':
                if all(valor == 1 for valor in etapas.values()):
                    ultima_etapa = 'terminadas'
                else:
                    ultima_etapa = next((etapa for etapa in reversed(etapas) if etapas[etapa] == 1), None)

                proceso_coccion = ultima_etapa
                
            elif proceso == 'fermentacion':
                if all(valor == 1 for valor in etapas.values()):
                    ultima_etapa = 'terminadas'
                else:
                    ultima_etapa = next((etapa for etapa in reversed(etapas) if etapas[etapa] == 1), None)

                proceso_fermentacion = ultima_etapa
        
        etapas_procesos['coccion'].append(proceso_coccion)
        etapas_procesos['fermentacion'].append(proceso_fermentacion)


    if batches_activos:
        return jsonify({"lotes_activos": lotes_activos,
                        "batches_activos": batches_activos,
                        "imagenes_productos": imagenes_productos,
                        "nombres_productos": nombres_productos,
                        "codigos_series": codigos_series,
                        "etapas_procesos": etapas_procesos})
    else:
        return jsonify({"message": "Ningún lote activo encontrado"}), 404

    
# API para obtener temperaturas de fermentadores en los BATCHS
@api_bp.route('/get_temperaturas_fermentadores', methods=['GET'])
def get_fermentadores_temperaturas():
    # Obtener los parámetros de la consulta
    lote = request.args.get('lote')
    batch = request.args.get('batch')

    query = {"batch": int(batch), "lote": lote}
    last_temperature = coleccion_fermentacion.find_one(query, sort=[("timestamp", -1)])

    # Verificar si se obtuvo un documento
    if last_temperature:
        # Extraer la temperatura del último documento
        temperature = last_temperature.get('temperatura')

        return jsonify({
            'lote': lote,
            'batch': batch,
            'temperatura': round(temperature,2)
        })
    else:
        return jsonify({'error': 'Batch no encontrado'}), 404



# API para obtener el lote que está en el proceso de coccion
@api_bp.route('/get_productos_en_coccion', methods=['GET'])
def get_productos_en_coccion():
    # Obtener los productos en cocción
    productos_en_coccion = list(coleccion_productos_en_coccion.find())

    # Eliminar el campo "_id" de cada producto
    for producto in productos_en_coccion:
        producto['imagen_producto_path'] = url_for('dashboard.static', filename=producto['imagen_producto_path']).replace('"', '').replace("'", '')
        producto.pop("_id", None)

    # Verificar si hay productos en cocción
    if productos_en_coccion:
        return jsonify(productos_en_coccion), 200

    return jsonify({'error': 'No hay lotes en cocción'}), 404


# API para obtener temperaturas de cocción
@api_bp.route('/get_temperaturas_coccion', methods=['GET'])
def get_coccion_temperaturas():
    # Obtener los parámetros de la consulta
    producto = request.args.get('producto')
    codigo_serie = request.args.get('codigo_serie')
    etapa = request.args.get('etapa')

    query = {"producto": producto, "codigo_serie": codigo_serie, "etapa": etapa}
    last_temperature = coleccion_coccion.find_one(query, sort=[("timestamp", -1)])

    # Verificar si se obtuvo un documento
    if last_temperature:
        # Extraer la temperatura del último documento
        temperature = last_temperature.get('temperatura')

        return jsonify({
            'producto': producto,
            'codigo_serie': codigo_serie,
            'etapa': etapa,
            'temperatura': temperature
        })
    else:
        return jsonify({'error': 'Batch no encontrado'}), 404
    

# Endpoint para obtener temperaturas de fermentadores con filtro de rango de fechas y fermentador
@api_bp.route('/fermentadores_filtro', methods=['GET'])
def get_fermentadores_temperaturas_filtro():
    try:
        # Obtener parámetros de rango de fechas y fermentador
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        batch_id = int(request.args.get('batch', 1))        

        # Convertir las fechas a objetos datetime para comparar
        start_date_filter = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_filter = datetime.strptime(end_date, '%Y-%m-%d')        

        # Filtrar documentos por rango de fechas
        pipeline = [
            {
                "$addFields": {
                    "timestampDate": { "$toDate": "$timestamp" }  # Convierte timestamp a ISODate
                }
            },
            {
                "$match": {
                    "batch": batch_id,
                    "timestampDate": {
                        "$gte": start_date_filter,
                        "$lte": end_date_filter
                    }
                }
            },
            {
                "$sort": { "timestampDate": -1 }  # Ordena por timestampDate en orden descendente
            }
        ]

        documentos_filtrados = coleccion_fermentacion.aggregate(pipeline)

        etapas = []
        data = {'fermentacion': [], 'colonizacion': [], 'reproduccion': [], 'lactancia': []}

        # Extraer datos relevantes del fermentador solicitado dentro del rango de fechas
        for documento in documentos_filtrados:
            etapa_documento = documento['etapa']
            data[etapa_documento].append({'x': documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                          'y': round(documento['temperatura'], 2)})                

        return jsonify({
            "data": data
        })

    except Exception as e:
        print(f"Error al obtener las temperaturas filtradas: {e}")
        return jsonify({"error": str(e)}), 500


# Endpoint para obtener temperaturas de los estanques con filtro de rango de fechas y estanque
@api_bp.route('/coccion_filtro', methods=['GET'])
def get_coccion_temperaturas_filtro():
    estanque_tipo = {1: 'macerador',
                     2: 'hervor',
                     3: 'coccion'}
    try:
        # Obtener parámetros de rango de fechas y estanque
        start_date = request.args.get('startDate')
        end_date = request.args.get('endDate')
        estanque_id = estanque_tipo[int(request.args.get('estanque', 1))]

        # Convertir las fechas a objetos datetime para comparar
        start_date_filter = datetime.strptime(start_date, '%Y-%m-%d')
        end_date_filter = datetime.strptime(end_date, '%Y-%m-%d')
        etapa = estanque_id

        pipeline = [
            {
                "$addFields": {
                    "timestampDate": { "$toDate": "$timestamp" }  # Convierte timestamp a ISODate
                }
            },
            {
                "$match": {
                    "etapa": etapa,
                    "timestampDate": {
                        "$gte": start_date_filter,
                        "$lte": end_date_filter
                    }
                }
            },
            {
                "$sort": { "timestampDate": -1 }  # Ordena por timestampDate en orden descendente
            }
        ]

        # Filtrar documentos por rango de fechas
        documentos_filtrados = coleccion_coccion.aggregate(pipeline)

        data = {'hervor': [], 'macerador': [], 'coccion': []}

        # Extraer datos relevantes del estanque solicitado dentro del rango de fechas
        for documento in documentos_filtrados:
            etapa_documento = documento['etapa']
            data[etapa_documento].append({'x': documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                          'y': round(documento['temperatura'], 2)})

        
        for documento in documentos_filtrados:
            for detalle in documento['detalles']:
                if detalle['etapa'] == estanque_id:
                    temperaturas.append(detalle['temperatura'])
                    etapas.append(detalle['etapa'])
                    fechas.append(documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"))
                    data.append({'x': documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                 'y': detalle['temperatura']})

        submuestra = {
            'hervor': [data['hervor'][i] for i in range(0, len(data['hervor']), 30)],  # Submuestreo con un intervalo de 20
            'macerador': [data['macerador'][i] for i in range(0, len(data['macerador']), 30)],  # Submuestreo con un intervalo de 20
            'coccion': [data['coccion'][i] for i in range(0, len(data['coccion']), 30)],  # Submuestreo con un intervalo de 10
        }

        return jsonify({
            "data": data[estanque_id]
        })

    except Exception as e:
        print(f"Error al obtener las temperaturas filtradas: {e}")
        return jsonify({"error": str(e)}), 500


from werkzeug.utils import secure_filename
UPLOAD_FOLDER = 'dashboard/static/images/imagenes_reportes/'
import matplotlib
matplotlib.use('Agg')  # Modo no interactivo para evitar el uso de la GUI
import matplotlib.pyplot as plt

@api_bp.route('/get_serie_data', methods=['GET'])
def get_serie_data():
    codigo_serie = request.args.get('codigo_serie')
    if not codigo_serie:
        return jsonify({"error": "Debe proporcionar el código de serie."}), 400

    query = {'codigo_serie': codigo_serie}
    productos_batches = coleccion_historic_batches.find_one(query, {'_id': 0})
    productos_coccion = coleccion_historic_coccion.find_one(query, {'_id': 0})

    if not productos_batches and not productos_coccion:
        return jsonify({"error": "No existe el código de serie."}), 400
    
    pipeline = [
        {
            "$addFields": {
                "timestampDate": { "$toDate": "$timestamp" }
            }
        },
        {
            "$match": {
                "codigo_serie": codigo_serie
            }
        },
        {
            "$sort": { 
                "timestampDate": -1
            }
        }
    ]

    historic_data_fermentacion_docs = coleccion_fermentacion.aggregate(pipeline)  
    historic_data_coccion_docs = coleccion_coccion.aggregate(pipeline)


    historic_data_fermentacion = []
    historic_data_coccion = []

    for documento in historic_data_fermentacion_docs:
        historic_data_fermentacion.append({'x': documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                           'y': documento['temperatura']})

    for documento in historic_data_coccion_docs:
        historic_data_coccion.append({'x': documento['timestamp'].strftime("%Y-%m-%d %H:%M:%S"),
                                      'y': documento['temperatura']})

    
    productos_batches['existe'] = 1
    productos_batches['historic_data_fermentacion'] = None
    productos_batches['historic_data_coccion'] = None

    # Crear gráficos de los datos históricos
    if historic_data_fermentacion:
        tiempos_fermentacion = [item['x'] for item in historic_data_fermentacion]
        valores_fermentacion = [item['y'] for item in historic_data_fermentacion]
        
        # Crear gráfico de fermentación
        plt.figure(figsize=(12, 6))
        plt.plot(tiempos_fermentacion, valores_fermentacion, marker='o', color='b', linestyle='-', markersize=6)
        plt.title('Histórico de Fermentación', fontsize=16)
        plt.xlabel('Tiempo', fontsize=12)
        plt.ylabel('Temperatura (°C)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.7)

        # Guardar la imagen
        fermentacion_img_path = os.path.join(UPLOAD_FOLDER, secure_filename('historico_fermentacion.png'))
        plt.tight_layout()
        plt.savefig(fermentacion_img_path)
        plt.close()

        productos_batches['historic_data_fermentacion'] = 'dashboard/static/images/imagenes_reportes/historico_fermentacion.png'

    if historic_data_coccion:
        tiempos_coccion = [item['x'] for item in historic_data_coccion]
        valores_coccion = [item['y'] for item in historic_data_coccion]

        # Crear gráfico de cocción
        plt.figure(figsize=(12, 6))
        plt.plot(tiempos_coccion, valores_coccion, marker='x', color='r', linestyle='-', markersize=6)
        plt.title('Histórico de Cocción', fontsize=16)
        plt.xlabel('Tiempo', fontsize=12)
        plt.ylabel('Temperatura (°C)', fontsize=12)
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, linestyle='--', alpha=0.7)

        # Guardar la imagen
        coccion_img_path = os.path.join(UPLOAD_FOLDER, secure_filename('historico_coccion.png'))
        plt.tight_layout()
        plt.savefig(coccion_img_path)
        plt.close()

        
        productos_batches['historic_data_coccion'] = 'dashboard/static/images/imagenes_reportes/historico_coccion.png'
    
    return jsonify(productos_batches)


@api_bp.route('/render_reporte', methods=['POST'])
def render_reporte():
    data = request.get_json()

    nombre_producto = data.get('nombre_producto')
    codigo_serie = data.get('codigo_serie')
    
    lote = data.get('lote', 'Sin lote')
    comentarios = data.get('comentarios', 'Sin comentarios')
    imagen_producto_path = data.get('imagen_producto_path', [])

    historic_data_fermentacion = data.get('historic_data_fermentacion')
    historic_data_coccion = data.get('historic_data_coccion')

    # Renderiza la plantilla Jinja con los datos proporcionados
    reporte_html = render_template('dashboard/components/reporte.html',
                                   fecha_actual=datetime.now().strftime("%d/%m/%Y"),
                                   nombre_producto=nombre_producto,
                                   codigo_serie=codigo_serie,
                                   lote=lote, 
                                   comentarios=comentarios, 
                                   imagen_producto_path=f'dashboard/static/{imagen_producto_path}',
                                   historic_data_fermentacion=historic_data_fermentacion,
                                   historic_data_coccion=historic_data_coccion)
    
    return jsonify({'reporteHtml': reporte_html})


@api_bp.route('/imprimir_reporte', methods=['POST'])
def imprimir_reporte():
    nombre_producto = request.form.get('nombre_producto')
    codigo_serie = request.form.get('codigo_serie')
    lote = request.form.get('lote')
    fecha_actual = request.form.get('fecha_actual')
    notas = request.form.get('notas')
    comentario = request.form.get('comentario')
    product_image_path_global = request.form.get('product_image_path_global')
    imagen = request.files.get('imagen')
    historic_data_fermentacion = request.form.get('historic_data_fermentacion')
    historic_data_coccion = request.form.get('historic_data_coccion')

    if historic_data_fermentacion == 'null':
        historic_data_fermentacion = None

    if historic_data_coccion == 'null':
        historic_data_coccion = None

    if imagen:
        filename = secure_filename(imagen.filename)
        filename = "temporary_image_file" + os.path.splitext(imagen.filename)[1]
        imagen_path = os.path.join(UPLOAD_FOLDER, filename)
        imagen.save(imagen_path)
    else:
        filename = None
        imagen = None

    reporte_html = render_template('dashboard/components/reporte_imprimir.html',
                                   fecha_actual=fecha_actual,
                                   nombre_producto=nombre_producto,
                                   codigo_serie=codigo_serie,
                                   notas=notas,
                                   lote=lote, 
                                   comentarios=comentario, 
                                   imagen=f'dashboard/static/images/imagenes_reportes/{filename}' if filename else None,
                                   imagen_producto_path = f'dashboard/static/{product_image_path_global}',
                                   historic_data_fermentacion=historic_data_fermentacion if historic_data_fermentacion else None,
                                   historic_data_coccion=historic_data_coccion if historic_data_coccion else None)

    return jsonify({"reporteHtml": reporte_html}), 200













    

