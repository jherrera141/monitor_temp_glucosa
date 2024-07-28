import paho.mqtt.client as mqtt
import json
import csv
import os
from datetime import datetime
from threading import Thread
from dash import Dash, html, dash_table, dcc, Input, Output, State
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import callback_context
import io
import base64

# Configuración del broker MQTT y el tema al que se suscribe
MQTT_BROKER = "broker.hivemq.com"
MQTT_TOPIC = "Diplomado/LabSolutions/Proyectofinal12"

# Encabezado para el archivo CSV
header = ['Fecha', 'Humedad', 'Temperatura']

# Escribir el encabezado solo una vez al inicio
if not os.path.isfile("datos_mqtt.csv"):
    with open("datos_mqtt.csv", "w", newline='') as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(header)


# Función que se llama cuando se establece la conexión con el broker MQTT
def on_connect(client, userdata, flags, rc):
    print("Se conecto con MQTT " + str(MQTT_BROKER))
    # Suscribirse al tema especificado
    client.subscribe(MQTT_TOPIC)


# Función que se llama cuando se recibe un mensaje MQTT
def on_message(client, userdata, msg):
    if msg.topic == MQTT_TOPIC:
        print(f"Datos: {str(msg.payload)}")
        # Decodificar el mensaje JSON recibido
        dato = json.loads(msg.payload)
        humidity = int(dato["Humedad"])
        temperature = int(dato["Temperatura"])
        # Obtener la fecha y hora actual
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        print(dt_string, humidity, temperature)

        # Abrir el archivo CSV en modo anexar y escribir los datos recibidos
        with open("datos_mqtt.csv", "a", newline='') as f:
            writer = csv.writer(f, delimiter=",")
            writer.writerow([dt_string, humidity, temperature])


# Crear una instancia del cliente MQTT y configurar las funciones de callback
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message


# Función para cargar los datos del archivo CSV
def cargar_datos():
    return pd.read_csv('datos_mqtt.csv')


# Inicializar la aplicación
app = Dash(__name__)

# Diseño de la aplicación
app.layout = html.Div(
    children=[
        html.Div(className='header', children=[
            html.H1(children=[
                html.Span('Lab', style={'color': '#8FFFFF'}),
                html.Span('-solutions', style={'color': 'white'})
            ]),
            html.H1('Datos de Sensores')
        ]),
        html.Div(className='dash-table-container', style={'backgroundColor': 'rgba(33, 33, 33, 0.5)'}, children=[
            dash_table.DataTable(
                id='tabla-datos',
                page_size=10,
                style_table={'height': '300px', 'overflowY': 'auto'},
                style_header={'backgroundColor': '#869FB2', 'color': 'white', 'fontWeight': 'bold'},
                style_cell={'textAlign': 'center', 'padding': '10px'},
                style_data={'backgroundColor': 'rgba(33, 33, 33, 0.5)', 'color': 'White'}
            )
        ]),
        html.Div(className='date-picker-container',
                 style={'display': 'flex', 'justifyContent': 'center', 'gap': '10px', 'marginBottom': '20px'},
                 children=[
                     dcc.DatePickerRange(
                         id='date-picker-range',
                         start_date_placeholder_text='Start Date',
                         end_date_placeholder_text='End Date',
                         calendar_orientation='horizontal'
                     ),
                     html.Button('Filtrar', id='filter-button', n_clicks=0),
                     html.Button('Descargar CSV', id='download-button', n_clicks=0),
                     dcc.Download(id='download-csv')
                 ]),
        html.Div(
            className='dash-graph-container',
            style={'display': 'flex', 'justifyContent': 'center', 'flexWrap': 'wrap', 'gap': '20px'},
            children=[
                dcc.Graph(id='grafico-temp', style={'width': '45%', 'display': 'inline-block'}),
                dcc.Graph(id='grafico-humedad', style={'width': '45%', 'display': 'inline-block'}),
                dcc.Graph(id='indicador-temp', style={'width': '45%', 'display': 'inline-block'}),
                dcc.Graph(id='indicador-humedad', style={'width': '45%', 'display': 'inline-block'}),
                dcc.ConfirmDialog(id='alerta-temperatura', message=''),
                dcc.ConfirmDialog(id='alerta-humedad', message=''),
            ]
        ),
        dcc.Interval(
            id='intervalo-actualizacion',
            interval=30000,  # Intervalo de actualización en milisegundos (30 segundos)
            n_intervals=0
        ),
        html.Div(id='modal', style={'display': 'none', 'position': 'fixed', 'top': '50%', 'left': '50%',
                                    'transform': 'translate(-50%, -50%)', 'backgroundColor': 'white', 'padding': '20px',
                                    'zIndex': 1000}, children=[
            html.H2('Datos Filtrados'),
            dcc.Graph(id='filtered-grafico-temp'),
            dcc.Graph(id='filtered-grafico-humedad'),
            html.Button('Cerrar', id='close-modal', n_clicks=0)
        ]),
        html.Div(id='overlay',
                 style={'display': 'none', 'position': 'fixed', 'top': 0, 'left': 0, 'width': '100%', 'height': '100%',
                        'backgroundColor': 'rgba(0,0,0,0.5)', 'zIndex': 999}),
        html.Div(className='footer', style={'text-align': 'center'}, children=[
            html.P('© 2024 Lab-solution. Todos los derechos reservados.')
        ])
    ]
)


# Callback para actualizar los datos y las gráficas
@app.callback(
    [Output('tabla-datos', 'data'),
     Output('grafico-temp', 'figure'),
     Output('grafico-humedad', 'figure'),
     Output('indicador-temp', 'figure'),
     Output('indicador-humedad', 'figure'),
     Output('alerta-temperatura', 'displayed'),
     Output('alerta-temperatura', 'message'),
     Output('alerta-humedad', 'displayed'),
     Output('alerta-humedad', 'message')],
    [Input('intervalo-actualizacion', 'n_intervals')]
)
def actualizar_datos(n_intervals):
    df = cargar_datos()  # Cargar los datos desde el CSV
    df['Fecha'] = pd.to_datetime(df['Fecha'])  # Asegurarse de que la columna 'Fecha' sea de tipo datetime
    df = df.sort_values('Fecha', ascending=False)  # Ordenar los datos por fecha en orden descendente

    # Gráficos de línea para temperatura y humedad
    fig_temp = px.line(df, x='Fecha', y='Temperatura', line_shape='spline', title='Temperatura')
    fig_temp.add_shape(
        type="line",
        x0=df['Fecha'].min(),
        y0=3,
        x1=df['Fecha'].max(),
        y1=3,
        line=dict(color="blue", width=2, dash="dash"),
    )
    fig_temp.add_shape(
        type="line",
        x0=df['Fecha'].min(),
        y0=7,
        x1=df['Fecha'].max(),
        y1=7,
        line=dict(color="red", width=2, dash="dash"),
    )
    fig_temp.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

    fig_humedad = px.line(df, x='Fecha', y='Humedad', line_shape='spline', title='Humedad')
    fig_humedad.add_shape(
        type="line",
        x0=df['Fecha'].min(),
        y0=10,
        x1=df['Fecha'].max(),
        y1=10,
        line=dict(color="blue", width=2, dash="dash"),
    )
    fig_humedad.add_shape(
        type="line",
        x0=df['Fecha'].min(),
        y0=70,
        x1=df['Fecha'].max(),
        y1=70,
        line=dict(color="red", width=2, dash="dash"),
    )
    fig_humedad.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

    # Indicadores de temperatura y humedad
    temp_valor = df['Temperatura'].iloc[0] if not df.empty else 0
    humedad_valor = df['Humedad'].iloc[0] if not df.empty else 0

    indicador_temp = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temp_valor,  # Último valor de temperatura
        title={'text': "Temperatura °C"},
        gauge={'axis': {'range': [-40, 80]},
               'bar': {'color': "darkblue"},
               'bgcolor': "#8FFFFF",
               'threshold': {
                   'line': {'color': "black", 'width': 4},
                   'thickness': 0.75,
                   'value': temp_valor
               },
               'steps': [
                   {'range': [-40, 3], 'color': "blue"},
                   {'range': [3, 7], 'color': "green"},
                   {'range': [7, 80], 'color': "red"}
               ]
               }
    ))
    indicador_temp.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

    indicador_humedad = go.Figure(go.Indicator(
        mode="gauge+number",
        value=humedad_valor,  # Último valor de humedad
        title={'text': "Humedad %"},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': "darkblue"},
               'bgcolor': "white",
               'threshold': {
                   'line': {'color': "black", 'width': 4},
                   'thickness': 0.75,
                   'value': humedad_valor
               },
               'steps': [
                   {'range': [0, 30], 'color': "blue"},
                   {'range': [10, 70], 'color': "green"},
                   {'range': [70, 100], 'color': "red"}
               ]}
    ))
    indicador_humedad.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

    # Verificar si la temperatura supera los 7 grados o es menor a 3 grados
    temp_superior = temp_valor > 7
    temp_inferior = temp_valor < 3

    # Verificar si la humedad supera el 70% o es menor al 30%
    humedad_alta = humedad_valor > 70
    humedad_baja = humedad_valor < 10

    alerta_temp_display = temp_superior or temp_inferior
    alerta_temp_message = ''
    if temp_superior:
        alerta_temp_message = 'Temperatura superior superada!'
    elif temp_inferior:
        alerta_temp_message = 'Temperatura inferior superada!'

    alerta_humedad_display = humedad_alta or humedad_baja
    alerta_humedad_message = ''
    if humedad_alta:
        alerta_humedad_message = 'Humedad alta!'
    elif humedad_baja:
        alerta_humedad_message = 'Humedad muy baja!'

    return (df.to_dict('records'), fig_temp, fig_humedad, indicador_temp, indicador_humedad,
            alerta_temp_display, alerta_temp_message, alerta_humedad_display, alerta_humedad_message)


# Callback combinado para mostrar la ventana emergente con los datos filtrados y manejar el modal
@app.callback(
    [Output('filtered-grafico-temp', 'figure'),
     Output('filtered-grafico-humedad', 'figure'),
     Output('modal', 'style'),
     Output('overlay', 'style')],
    [Input('filter-button', 'n_clicks'),
     Input('close-modal', 'n_clicks')],
    [State('date-picker-range', 'start_date'),
     State('date-picker-range', 'end_date'),
     State('modal', 'style')]
)
def manejar_modal(n_clicks_filter, n_clicks_close, start_date, end_date, modal_style):
    ctx = callback_context  # Usar el contexto de callback importado
    if not ctx.triggered:
        return {}, {}, {'display': 'none'}, {'display': 'none'}

    trigger = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger == 'filter-button' and n_clicks_filter > 0:
        df = cargar_datos()
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df = df[(df['Fecha'] >= start_date) & (df['Fecha'] <= end_date)]
        if df.empty:
            return {}, {}, {'display': 'none'}, {'display': 'none'}

        fig_temp = px.line(df, x='Fecha', y='Temperatura', line_shape='spline', title='Temperatura Filtrada')
        fig_temp.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

        fig_humedad = px.line(df, x='Fecha', y='Humedad', line_shape='spline', title='Humedad Filtrada')
        fig_humedad.update_layout(paper_bgcolor='rgba(33, 33, 33, 0.5)', font=dict(color='white'))

        return fig_temp, fig_humedad, {'display': 'block'}, {'display': 'block'}

    if trigger == 'close-modal' and n_clicks_close > 0:
        return {}, {}, {'display': 'none'}, {'display': 'none'}

    return {}, {}, modal_style, {'display': 'block'}


# Callback para descargar los datos filtrados como CSV
@app.callback(
    Output('download-csv', 'data'),
    Input('download-button', 'n_clicks'),
    State('date-picker-range', 'start_date'),
    State('date-picker-range', 'end_date'),
    prevent_initial_call=True
)
def descargar_csv(n_clicks, start_date, end_date):
    df = cargar_datos()
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df = df[(df['Fecha'] >= start_date) & (df['Fecha'] <= end_date)]

    # Crear el archivo CSV en memoria
    csv_string = df.to_csv(index=False, encoding='utf-8')
    csv_bytes = csv_string.encode('utf-8')
    b64 = base64.b64encode(csv_bytes).decode()

    return dcc.send_data_frame(df.to_csv, "datos_filtrados.csv")

def run_mqtt():
    # Conectar al broker MQTT y comenzar el bucle de eventos
    client.connect(MQTT_BROKER, 1883, 60)
    client.loop_forever()


# Ejecutar la aplicación si es el script principal
if __name__ == '__main__':
    # Ejecutar el cliente MQTT en un hilo separado
    mqtt_thread = Thread(target=run_mqtt)
    mqtt_thread.start()

    # Ejecutar la aplicación Dash
    app.run_server(debug=True)
