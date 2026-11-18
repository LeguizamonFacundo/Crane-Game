#=====================================================
#TP integrador - Lenguaje de programación Python
#Materia: LABORATORIO DE COMPUTACIÓN II-2026-2do Cuat.
#Alumno: Leguizamón Facundo
#Profesora: MONICA HENCEK
#=====================================================

# Import de librerias
import glob #busca archivos en carpetas
import io #permite guardar imágenes en memoria
import math #utiles matemáticos
import os #rutas de archivos
import random #eleccion aleatoria
import time # pausas de gifs
import streamlit as st #interfaz de pagina
from PIL import Image, ImageDraw, ImageFont #utilidades de imagenes

st.set_page_config(page_title="Crane Game", layout="wide") #titulo
CARPETA = os.path.dirname(os.path.abspath(__file__))   # carpeta donde está app.py

#creacion de variables en memoria para que no se borren
s = st.session_state
s.setdefault("pantalla", "inicio")              #pantallas 
s.setdefault("fase", "espera")                  #espera -> moneda -> listo -> bajando -> espera
s.setdefault("x", 450)                          #posicion de la garra
s.setdefault("gif", None)                       #gif
s.setdefault("gif_ms", 0)                       #duracion gif
s.setdefault("bajando", False)                  #garra bajando
s.setdefault("resultado", (None, None, None))   #resultado de la tirada
s.setdefault("msg", "")                         #mensaje resultado
s.setdefault("ganado", None)                    #indicie premio ganado
s.setdefault("quitado", None)                   #si el premio fue sacado
s.setdefault("tiradas", 0)
s.setdefault("sacados", set())     # nombres de premios ya ganados

# ----- Parámetros -----
#premios
N_PREMIOS = 11          #cantidad de premios secreto
X0 = 150                #posicion horizontal del primer premio
PREMIO_Y = 490          #altura de los premios secretos
SEP = 60                #separacion entre pemios
PREMIO = 100            #tamaño de premio
COSTO = 5               #valor de cada tirada

#garra
X_MIN, X_MAX = 170, 730 #limites laterales de la garra
MOV_GARRA = 60          #movimiento lateral de la garra
Y_BASE = 252            #posicion inicial de la garra en y
BAJADA = 171            #cuantos px baja la garra
SUELTA = 0.7            #hasta que punto llega el premio secreto al subir

#moneda
COIN = 100              #tamaño de la moneda
COIN_X = 450            #posicion lateral de la moneda
COIN_Y_INI = 60         #posicion y inicial de la moneda
COIN_Y_FIN = 550        #posicion y final de la moneda
VEL_MONEDA = 0.6        #velociodad de la moneda

TAM = 500               #tamaño final de resolucion
PROB_GANAR = 0.45       #probabilidad de ganar (0 a 1)
ATTACH = PREMIO_Y - (Y_BASE + BAJADA)    # distancia de la garra al premio secreto colgado

# diccionrio de premios: (tier, probabilidad, color)
RAREZAS = {
    "comun":      ("Tier 1 y 2",      60, "#32a309"),
    "raro":       ("Tier 3",       20, "#9749d7"),
    "legendario": ("Tier 4",  7, "#ffd000da"),
}


#===========Creacion de imagenes===========

#genera la portada para el juego
@st.cache_data          #almacena en caché el resultado de la función, evita volver a generar la portada nuevamente 
def crear_portada():
    ancho, alto = 900, 300                      #define ancho y alto
    banner = Image.new("RGB", (ancho, alto))    #crea imagen
    draw = ImageDraw.Draw(banner)               #crea dibujo
    for y in range(alto):                       #loop para rellenar el
        t = y / alto
        draw.line([(0, y), (ancho, y)],         #dibuja una línea horizontal que ocupa todo el ancho de la imagen con degradado.
                  fill=(int(255 - 120 * t), int(120 + 40 * t), int(200 - 40 * t)))
    try:                                        #genera el titulo con arial, caso contrario usa una fuente generica
        fuente = ImageFont.truetype("arial.ttf", 90)
    except OSError:
        fuente = ImageFont.load_default(size=90)
    texto = "CRANE GAME"
    caja = draw.textbbox((0, 0), texto, font=fuente)    #genera la caja de  la portada
    x = (ancho - (caja[2] - caja[0])) // 2      #calcula la coordenada horizontal
    y = (alto - (caja[3] - caja[1])) // 2 - caja[1]#calcula la coordenada vertical
    draw.text((x + 4, y + 4), texto, font=fuente, fill=(60, 30, 90))    #dibuja sombra
    draw.text((x, y), texto, font=fuente, fill=(255, 255, 255))         #dibuja titulo
    return banner

# Carga,prepara y conserva las imágenes del juegoen memoria para no tener que abrirlas repetidamente.
@st.cache_resource      #almacena funcion en caché para ahorrar procesamiento de computo
def cargar_imagenes():
    fija = Image.open(os.path.join(CARPETA, "crane_game.png")).convert("RGBA").resize((900, 900)) #combina carpeta con nombre para abrir imagen con pillow, aplica rgba y reescala px
    movil = Image.open(os.path.join(CARPETA, "claw.png")).convert("RGBA").resize((340, 340))
    return fija, movil

# Crea las imagenes de premios secreto sobre la maquina.
@st.cache_resource
def crear_premios():
    ruta = os.path.join(CARPETA, "pregunta.png") #combina carpeta y nombre de la imagen
    if not os.path.exists(ruta): #comprueba si existe
        return None
    base = Image.open(ruta).convert("RGBA").resize((PREMIO, PREMIO))
    return [base] * N_PREMIOS

#crea la imagen de la moneda.
@st.cache_resource
def crear_moneda():
    #crea ruta, comprueba si existe, y sino la crea
    ruta = os.path.join(CARPETA, "nickel.png")
    if not os.path.exists(ruta):
        return None
    moneda = Image.open(ruta).convert("RGBA").resize((COIN, COIN))
    return moneda
   

#crea los premios que pueden salir: [(nombre, imagen_completa, imagen_chica, rareza)]"""
@st.cache_resource
def crear_ganados():
    
    ruta = os.path.join(CARPETA, "ganados") 
    resultado = []

    #se cargan todos los premios
    def cargar(carpeta, rareza):
        rutas = []
        for patron in ("*.png", "*.jpg", "*.jpeg", "*.webp"):   #busca imagenes por extensiones.
            rutas += glob.glob(os.path.join(carpeta, patron))   #agrega las rutas a la lista.
        #borra duplicados
        for r in sorted(set(rutas)):                            #convierte la lista en un conjunto ordenado alfabeticamente.
            img = Image.open(r).convert("RGBA")
            nombre = os.path.splitext(os.path.basename(r))[0].replace("_", " ").capitalize() #transforma el nombre del archivo para mostrar al usuario.
            chica = img.copy()                                  #copia de imagen pequeña.
            chica.thumbnail((PREMIO, PREMIO))                   #reduce los pixeles proporcionalmente.
            resultado.append((nombre, img, chica, rareza))      #agregar el premio a la lista.

    for clave in RAREZAS:                                       #busca los premios según su rareza.
        cargar(os.path.join(ruta, clave), clave)
    return resultado


#generar una tabla con todos los premios disponibles 
#identifica cuáles ya fueron ganados y los tacha
@st.cache_data
def dibujar_tabla(sacados):                     #recibe premios que ya se ganaron      
    premios = crear_ganados()                   #crea lista con todos los premios
    alto_fila, mini_tam, margen = 48, 40, 8     
    try:                                        #carga fuente
        fuente = ImageFont.truetype("arial.ttf", 16)
    except OSError:
        fuente = ImageFont.load_default(size=16)

    
    medidor = ImageDraw.Draw(Image.new("RGB", (1, 1)))  #crea imagen para guardar el largo del nombre de los premios
    ancho_texto = max(
        (medidor.textbbox((0, 0), n, font=fuente)[2] for n, _, _, _ in premios), #obtiene el nombre mas largo
        default=50)
    ancho = margen + mini_tam + margen + ancho_texto + margen   #calcula el largo de la tabla

    img = Image.new("RGB", (ancho, alto_fila * max(1, len(premios))), "white") #crea imagen
    d = ImageDraw.Draw(img)     #imagen para miniaturas

    for i, (nombre, _, chica, _) in enumerate(premios):      #recorre los premios
        y = i * alto_fila           
        sacado = nombre in sacados                           #define cual esta sacado
        mini = chica.copy()                                     
        mini.thumbnail((mini_tam, mini_tam))                 #redimensiona miniatura

        if sacado:                                           #Si el premio fue ganado, se atenua la imagen
            mini = Image.blend(Image.new("RGBA", mini.size, "white"), mini, 0.35)
        img.paste(mini, (margen + (mini_tam - mini.width) // 2,     #copia en una imagen premio chico y fondo blanco
                         y + (alto_fila - mini.height) // 2), mini) #en la tabla

        x_txt = margen + mini_tam + margen                  #pos x
        y_txt = y + (alto_fila - 16) // 2 - 2               #pos y
        color = (150, 150, 150) if sacado else (30, 30, 30) #color si fue sacado o no
        d.text((x_txt, y_txt), nombre, font=fuente, fill=color) #dibuja nombre

        if sacado:                                          #agrega linea si fue sacado
            caja = d.textbbox((x_txt, y_txt), nombre, font=fuente) #calcula rectangulo
            medio = (caja[1] + caja[3]) // 2                        #calcula medio
            d.line([(x_txt, medio), (caja[2], medio)], fill=color, width=2)#dibuja linea

        d.line([(0, y + alto_fila - 1), (ancho, y + alto_fila - 1)], #dibuja lineas divisorias
               fill=(220, 220, 220))
    return img

#crea la imagen de la tabla, ordena los nombres de los premios en una tupla
def tabla_premios():
    img = dibujar_tabla(tuple(sorted(s.sacados)))   
    st.image(img, width=img.width)  #muestra la tabla


#combinando la garra, el marco de la máquina, los premios y la moneda en un único lienzo
#permite modificar la posición y bajada de la garra, mostrar un premio levantado y ocultar un premio que ya fue retirado.
#Orden: garra -> marco -> premios fijos -> premio colgado -> moneda
def componer(x, y=0, angulo=0, moneda=None, colgado=None, quitado=None): 
    fija, movil = cargar_imagenes()
    premios = crear_premios() or []
    lienzo = Image.new("RGBA", (900, 900), (255, 255, 255, 255))#crear una imagen nueva donde se combinarán todos los elementos.

    garra = movil.rotate(angulo, expand=True, resample=Image.Resampling.BICUBIC)# generar una versión rotada de la imagen de la garra.
    pos = (int(x - garra.width / 2), int(Y_BASE + y - garra.height / 2))#calcula la posición donde se colocará la garra en el lienzo.
    lienzo.paste(garra, pos, garra)                             #colocar la garra sobre lienzo.
    lienzo.alpha_composite(fija)                                #Combina la maquina con el lienzo utilizando el canal alfa.

    for i, p in enumerate(premios):                             #recorre la lista de premios. y dibuja.
        if i == quitado:                                        #si es el que levantó la garra no lo dibuja.
            continue
        px = X0 + i * SEP
        lienzo.alpha_composite(p, (int(px - PREMIO / 2), int(PREMIO_Y - PREMIO / 2)))#combina la imagen del premio con el lienzo. (en base al primer premio).

    if colgado and premios:                    
        px, py = colgado
        lienzo.alpha_composite(                                 #dibuja una copia de premio en la posición indicada.
            premios[0], (int(px - PREMIO / 2), int(py - PREMIO / 2)))

    if moneda:
        cx, cy = moneda
        lienzo.alpha_composite(crear_moneda(),                  #dibuja la moneda:
                               (int(cx - COIN / 2), int(cy - COIN / 2)))

    return lienzo.convert("RGB").resize((TAM, TAM), Image.Resampling.LANCZOS) #devuelve la imagen final.


#===========Creacion de gifs===========

#recibe una lista de imágenes y la duración de cada fotograma para crear un gif.
def a_gif(cuadros, ms):
    buf = io.BytesIO()                                          #crea un objeto que funciona como un archivo.
    cuadros[0].save(buf, format="GIF", save_all=True, append_images=cuadros[1:],
                    duration=ms, disposal=1)                    #guardar las imágenes como un único GIF animado.
    return buf.getvalue()                                       #obtiene y retorna todo el contenido almacenado en el buffer.


#cargar el archivo GIF correspondiente a las rarezas
@st.cache_resource
def cargar_gif_rareza(rareza):
    ruta = os.path.join(CARPETA, "gifs", f"{rareza}.gif")       #construye la ruta.
    if not os.path.exists(ruta):                                #comrueba si existe.
        return None
    with open(ruta, "rb") as f:                                 #abre el archivo en modo lectura binaria.
        return f.read()                                         #lee el contenido y lo devuelve como una secuencia de bytes.

#genera el gif de la moneda cayendo dentro de la maquina
@st.cache_data
def gif_moneda(x):
    ms = 30
    n = max(4, int(24 / VEL_MONEDA))        #calcula la cantidad de fotogramas.
    cuadros = []
    for i in range(n + 1):                  #genera los fotogramas de la caída.
        t = i / n
        cy = COIN_Y_INI + (COIN_Y_FIN - COIN_Y_INI) * t ** 2   #calcula la coordenada vertical de la moneda en cada fotograma.
        cuadros.append(componer(x, moneda=(COIN_X, cy)))       #generar una imagen de la máquina con la moneda en la posición calculada.
    cuadros += [cuadros[-1]] * 4                               #mantiene la moneda en la ranura.
    cuadros.append(componer(x))                                #desaparece.
    return a_gif(cuadros, ms), len(cuadros) * ms

#genera gif de la garra levantando el premio secreto, puede levantarlo para ganar o resvalarse y perderlo.
@st.cache_data
def gif_bajar(x, modo, idx):                #recibe posicion x de la garra, si gana o resbala y que premio levanta.
    ms = 30                         
    px0 = X0 + idx * SEP                    #calcula la posición horizontal original del premio.
    cuadros = []

    for i in range(21):                     #for para bajar
        t = i / 20
        cuadros.append(componer(x, BAJADA * (1 - (1 - t) ** 2),
                                6 * math.sin(math.pi * t))) #angulo de inclinacion.
        #hace que la garra comience descendiendo rápidamente y vaya frenando a medida que se acerca al premio.
        
    for i in range(12):                     #el premio se acerca a la garra.
        t = i / 11
        px = px0 + (x - px0) * t            #formula de posicion del premio hacia la garra.
        cuadros.append(componer(x, BAJADA, 0, #la garra agarra el premio.
                                colgado=(px, PREMIO_Y), quitado=idx))

    y_suelta = BAJADA * (1 - SUELTA ** 2) + Y_BASE + ATTACH   # calcula la altura donde se suelta.
    for i in range(21):                     #garra subiendo
        t = i / 20                          #calcular la posición vertical de la garra.
        yg = BAJADA * (1 - t ** 2)
        ang = -6 * math.sin(math.pi * t)    #calcula inclinacion y vuelve a su lugar.

        if modo == "gana" or t < SUELTA:    #el premio acopmapaña la garra.
            cuadros.append(componer(x, yg, ang,
                                    colgado=(x, Y_BASE + yg + ATTACH), quitado=idx))
        else:                               #el premio se resbala y cae a su lugar.
            f = min(1, (t - SUELTA) / 0.2)  #calcula el progreso de la caída.
            if f >= 1:                      #si terminó de caer.
                cuadros.append(componer(x, yg, ang)) #el premio vuelve a su lugar y la garra sigue subiendo.
            else:                           #si sigue cayendo
                px = x + (px0 - x) * f      #se desplaza desde la garra a su lugar.
                py = y_suelta + (PREMIO_Y - y_suelta) * f ** 2  #calcula pos vertical.
                cuadros.append(componer(x, yg, ang,
                                        colgado=(px, py), quitado=idx))
    return a_gif(cuadros, ms), len(cuadros) * ms
     

# ----- Lógica -----

#prepara las variables para comenzar una partida desde cero.
def ir_a_juego():
    s.pantalla, s.fase, s.x = "juego", "espera", 450
    s.gif, s.bajando, s.msg, s.ganado, s.quitado = None, False, "", None, None
    s.tiradas, s.sacados = 0, set()


#inicia una tirada de la máquina, prepara las variables y generando la animación de la moneda.
def tirar():
    s.fase = "moneda"
    s.msg = ""
    s.ganado = None
    s.quitado = None
    s.tiradas += 1                      #cuenta la tirada.
    s.gif, s.gif_ms = gif_moneda(s.x)


#vuelve a la pantalla inicial del juego.
def ir_a_inicio():
    s.pantalla = "inicio"


#controla el movimiento horizontal de la garra.
def mover(d):       #recibe d para mover la garra
    s.x = max(X_MIN, min(X_MAX, s.x + d * MOV_GARRA)) #calcula su nueva posición y no permite que se salga de la maquina


#selecciona aleatoriamente que premio puede salir.
def elegir_premio():
    por_rareza = {}
    for i, (_, _, _, rareza) in enumerate(crear_ganados()): #guarda las rarezas de los premios.
        por_rareza.setdefault(rareza, []).append(i)         #asocia rarezas con imagenes.
    claves = list(por_rareza)                               
    rareza = random.choices(claves, weights=[RAREZAS[c][1] for c in claves])[0] #selecciona aleatoria de una rareza segun probabilidad.
    return random.choice(por_rareza[rareza])


#inicia el movimiento de descenso de la garra y determinar el resultado del intento.
def bajar():
    if not crear_ganados():                 #si no se genera ganados retorna.
        return                              #evita que la garra intente levantar un premio cuando no hay ninguno disponible.
    gana = random.random() < PROB_GANAR     #determina si gana o no.
    g = elegir_premio()                     
    modo = "gana" if gana else "resbala"
    idx = min(range(N_PREMIOS), key=lambda i: abs(s.x - (X0 + i * SEP))) #pos del premio mas cercano.
    s.resultado = (g, modo, idx)            #guarda indice, resultado y pos premio secreto
    s.bajando = True
    s.gif, s.gif_ms = gif_bajar(s.x, modo, idx) #genera gif


# ------------ juego que se recarga en cada click ------------
#construir y administrar la interfaz principal de la partida.
#gestiona la visualización de la máquina, las animaciones GIF, los premios disponibles y la tabla de premios conseguidos.
#
@st.fragment    #permite ejecutar la funcion como un fragmento independiente de la aplicación, sin necesidad de volver a ejecutarla.
def juego():
    listo = s.fase == "listo" and not s.bajando

    if crear_premios() is None:         #comprueba imagenes de premios
        st.error("No encuentro premio.png. Ponelo en la misma carpeta que app.py.")
    if not crear_ganados():
        st.error("No encuentro imágenes en la carpeta 'ganados' (junto a app.py).")

    st.button("TIRAR", on_click=tirar, disabled=s.fase != "espera",     #crea el boton en la interfaz.
              use_container_width=True, type="primary")

    izq, centro, der = st.columns(3)                                    #crea 3 columnas para los 3 botones que manejan la maquina
    izq.button("◀", on_click=mover, args=(-1,), disabled=not listo,
               use_container_width=True)
    centro.button("⬇ Bajar", on_click=bajar, disabled=not listo,
                  use_container_width=True)
    der.button("▶", on_click=mover, args=(1,), disabled=not listo,
               use_container_width=True)

    #contenedores para mostrar las estadisticas del juego: tiradas, monedas gastadas y premios sacados
    c_t, c_g, c_p = st.columns(3)
    c_t.metric("Tiradas", s.tiradas)
    c_g.metric("Gastado", f"${s.tiradas * COSTO}")
    c_p.metric("Premios", f"{len(s.sacados)} / {len(crear_ganados())}")

    #compueba si hay mensaje segun fase y lo muestra
    if s.msg:
        if s.ganado is not None:    #si es ganado muestra nombre, premio y rareza
            nombre, img, _, rareza = crear_ganados()[s.ganado]
            etiqueta, _, _ = RAREZAS[rareza]
            st.success(s.msg)
            st.badge(etiqueta, color="yellow")
            st.image(img, width=150)
        else:
            st.warning(s.msg)       #no obtuvo premio
    elif s.fase == "listo":
        st.info("Mueve la garra con ◀ ▶ y presioná Bajar")  #jugando
    else:
        st.info("Presioná TIRAR para insertar la moneda")    #antes de jugar

    #muestra la máquina, reproducir las animaciones, presentar un GIF y la tabla de premios.
    col_escena, col_gif = st.columns([3, 1])    #divide en columnas
    with col_escena:
        with st.container(height=TAM + 20, border=False):
            if s.fase == "moneda" or s.bajando:     #si esta la moneda o bajando la garra
                st.image(s.gif, width=TAM)          #muestra el gif generado 
            else:
                st.image(componer(s.x, quitado=s.quitado), width=TAM)   #maquina 

    with col_gif:
        if s.ganado is not None and not s.bajando and s.fase == "espera":
            rareza = crear_ganados()[s.ganado][3]   #obtiene rareza del premio
            gif = cargar_gif_rareza(rareza)
            if gif:
                st.image(gif, use_container_width=True)

    col_tabla, _ = st.columns([1, 3])
    with col_tabla:
        st.caption("Pool de la maquina")    #texto pequeño
        tabla_premios()
   

    if s.fase == "moneda":                      #si esta la moneda cayendo espera, actualiza fase y limpia gif
        time.sleep(s.gif_ms / 1000 + 0.1)
        s.fase, s.gif = "listo", None
        st.rerun(scope="fragment")              #vuelve a juego

    if s.bajando:                               #si esta la la garra cayendo espera, actualiza fase y limpia gif
        time.sleep(s.gif_ms / 1000 + 0.2)
        g, modo, idx = s.resultado
        if modo == "gana":
            s.ganado = g
            s.quitado = idx                         #queda fuera hasta la próxima tirada
            s.sacados.add(crear_ganados()[g][0])    #se guarda en ganados
            s.msg = f"¡Ganaste: {crear_ganados()[g][0]}!"
        else:
            s.ganado = None
            s.quitado = None
            s.msg = "Casi ganas, el premio se resbaló. ¡Insertá otra moneda!"
        s.bajando, s.fase, s.gif = False, "espera", None
        st.rerun(scope="fragment")

#muestra pantalla de inicio
if s.pantalla == "inicio":
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.image(crear_portada(), use_container_width=True)
        st.button("Jugar", on_click=ir_a_juego,
                  use_container_width=True, type="primary")
else:
    st.button("⬅ Volver al inicio", on_click=ir_a_inicio)
    c1, c2, c3 = st.columns([1, 4, 1])
    with c2:
        juego()