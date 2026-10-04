# INTERFAZ GRAFICA - RED ELECTRICA DE CHIMBOTE
#
# Muestra el grafo y permite simular fallas para ver, con los algoritmos propios:
#   - BFS/DFS: conectividad
#   - Ordenamiento topologico: distribucion de energia
#   - SCC: redundancias (aristas sin respaldo)
#
# Ejecutar:  python interfaz_red.py
# Archivos necesarios en la misma carpeta: red_electrica_chimbote.py,
# analisis_red.py y SED_1500_CHIMBOTE.csv

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap
from matplotlib.patches import Circle, Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import red_electrica_chimbote as red
import analisis_red as an


# COLORES

COLOR_FONDO = "#eef1f6"
COLOR_OSCURO = "#1f2a44"
COLOR_ACENTO = "#2563eb"
COLOR_ACENTO_OSC = "#1d4ed8"
COLOR_AVISO = "#d97706"
COLOR_AVISO_OSC = "#b45309"
COLOR_BORDE = "#c7cedb"


def aplicar_estilo(raiz):
    # tema "clam" de ttk con colores propios (no necesita librerias extra)
    estilo = ttk.Style(raiz)
    estilo.theme_use("clam")
    raiz.configure(bg=COLOR_FONDO)
    estilo.configure(".", background=COLOR_FONDO, font=("Segoe UI", 10))
    estilo.configure("TFrame", background=COLOR_FONDO)
    estilo.configure("TLabel", background=COLOR_FONDO)
    estilo.configure("TCheckbutton", background=COLOR_FONDO)
    estilo.configure("TLabelframe", background=COLOR_FONDO, bordercolor=COLOR_BORDE)
    estilo.configure("TLabelframe.Label", background=COLOR_FONDO, foreground=COLOR_OSCURO,
                     font=("Segoe UI", 10, "bold"))

    estilo.configure("TButton", padding=5, background="#ffffff", bordercolor=COLOR_BORDE)
    estilo.map("TButton", background=[("active", "#e2e8f5")])
    estilo.configure("Accent.TButton", background=COLOR_ACENTO, foreground="white",
                     bordercolor=COLOR_ACENTO, font=("Segoe UI", 10, "bold"))
    estilo.map("Accent.TButton", background=[("active", COLOR_ACENTO_OSC)],
               foreground=[("active", "white")])
    estilo.configure("Aviso.TButton", background=COLOR_AVISO, foreground="white",
                     bordercolor=COLOR_AVISO, font=("Segoe UI", 10, "bold"))
    estilo.map("Aviso.TButton", background=[("active", COLOR_AVISO_OSC)],
               foreground=[("active", "white")])

    estilo.configure("TNotebook", background=COLOR_FONDO, borderwidth=0)
    estilo.configure("TNotebook.Tab", padding=(14, 6), font=("Segoe UI", 10, "bold"),
                     background="#dfe5f0")
    estilo.map("TNotebook.Tab", background=[("selected", "#ffffff")],
               foreground=[("selected", COLOR_ACENTO)])

    estilo.configure("Banner.TFrame", background=COLOR_OSCURO)
    estilo.configure("Titulo.TLabel", background=COLOR_OSCURO, foreground="white",
                     font=("Segoe UI", 16, "bold"))
    estilo.configure("Sub.TLabel", background=COLOR_OSCURO, foreground="#b8c4e0",
                     font=("Segoe UI", 9))


# ESTADO DE LA APLICACION

estado = {
    "fuente": 0,             # indice de la subestacion que alimenta la red
    "nodos_caidos": set(),   # subestaciones que fallan
    "aristas_caidas": set(), # enlaces que fallan, como clave(a, b)
    "enlaces": [],           # enlaces de frontera que se muestran en la lista
    "grupos": [],            # los 3 grupos de nodos (uno por integrante)
    "vista": None,           # ultima vista dibujada (para refrescar al cambiar fallas)
    "nodo_sel": None,        # nodo que se esta mirando en la vista de grafos
    "nivel_dyv": 1,          # nivel de la recursion que se muestra en divide y venceras
    "niveles": [],           # niveles[d] = regiones que existen en el nivel d de la recursion
    "parte": [],             # parte[d][i] = numero de region del nodo i en el nivel d
    "union": {},             # nivel en que se creo cada enlace de frontera
    "zona_de": {},           # zona a la que pertenece cada nodo
    "nodos_frontera": set(), # nodos que tienen un enlace de frontera
    "ej_nodos": [],          # los 6 nodos del ejemplo pequeno (indices reales del dataset)
    "ej_grafo": {},          # subgrafo del ejemplo: {nodo: {vecino: distancia}}
    "ej_letra": {},          # letra con que se dibuja cada nodo del ejemplo
    "ej_pos": {},            # posicion de cada nodo en el dibujo del ejemplo
}

# widgets (se crean en construir_interfaz)
figura = None
eje = None
lienzo = None
caja_texto = None
lista_enlaces = None
entrada_fuente = None
entrada_nodo = None
etiqueta_fallas = None
entrada_ver = None
etiqueta_nivel = None
variable_zoom = None
variable_falla_ej = None
barra_herramientas = None
indice_por_etiqueta = {}


# CONSTRUCCION DEL GRAFO

def preparar_datos():
    red.leer_datos()
    red.dividir(list(range(len(red.nodos))))

    # fuente: la subestacion de mayor potencia instalada
    fuente = 0
    for i in range(len(red.nodos)):
        if red.nodos[i]["potencia"] > red.nodos[fuente]["potencia"]:
            fuente = i
    estado["fuente"] = fuente

    for i in range(len(red.nodos)):
        indice_por_etiqueta[red.nodos[i]["etiqueta"]] = i

    # los 3 ultimos enlaces de frontera unen las dos mitades principales.
    # Se muestran primero en la lista
    estado["enlaces"] = list(reversed(red.fronteras))

    # un grupo por integrante: se corta el orden de las zonas en 3 partes iguales
    plano = []
    for zona in red.zonas:
        plano = plano + zona
    tercio = len(plano) // 3
    estado["grupos"] = [plano[:tercio], plano[tercio:2 * tercio], plano[2 * tercio:]]

    # divide y venceras: se reconstruye la recursion nivel por nivel para poder verla
    n = len(red.nodos)
    estado["niveles"] = niveles_divide_y_venceras()
    estado["parte"] = []
    for regiones in estado["niveles"]:
        numero = [0] * n
        for k in range(len(regiones)):
            for u in regiones[k]:
                numero[u] = k
        estado["parte"].append(numero)

    # un enlace de frontera se crea en el nivel donde sus dos extremos se separan
    estado["union"] = {}
    for a, b in red.fronteras:
        d = 0
        while estado["parte"][d][a] == estado["parte"][d][b]:
            d = d + 1
        estado["union"][(a, b)] = d

    estado["zona_de"] = {}
    for k in range(len(red.zonas)):
        for u in red.zonas[k]:
            estado["zona_de"][u] = k
    estado["nodos_frontera"] = set()
    for a, b in red.fronteras:
        estado["nodos_frontera"].add(a)
        estado["nodos_frontera"].add(b)
    estado["nodo_sel"] = estado["fuente"]
    preparar_ejemplo()


def preparar_ejemplo():
    # Ejemplo pequeno con datos reales: la primera union de la recursion junta dos zonas
    # vecinas con 3 enlaces. Se toman los 6 nodos de esos enlaces (3 de cada zona).
    enlaces = red.fronteras[:3]
    nodos = [a for a, b in enlaces] + [b for a, b in enlaces]
    mini = {}
    for u in nodos:
        mini[u] = {}
        for v in nodos:
            if v in red.grafo[u]:
                mini[u][v] = red.grafo[u][v]
    # dibujo: zona izquierda A, B, C; zona derecha D, E, F (A-D, B-E y C-F son los enlaces)
    posiciones = [(1.0, 5.0), (1.0, 1.0), (3.4, 3.0), (9.0, 5.0), (9.0, 1.0), (6.6, 3.0)]
    estado["ej_nodos"] = nodos
    estado["ej_grafo"] = mini
    estado["ej_letra"] = {}
    estado["ej_pos"] = {}
    for k in range(6):
        estado["ej_letra"][nodos[k]] = "ABCDEF"[k]
        estado["ej_pos"][nodos[k]] = posiciones[k]


def niveles_divide_y_venceras():
    # Hace la misma division que red.dividir, pero un nivel a la vez.
    # Una region de TAM_ZONA nodos o menos ya es zona y no se vuelve a dividir.
    niveles = [[list(range(len(red.nodos)))]]
    while True:
        siguiente = []
        dividio = False
        for region in niveles[-1]:
            if len(region) <= red.TAM_ZONA:
                siguiente.append(region)
                continue
            xs = [red.nodos[i]["x"] for i in region]
            ys = [red.nodos[i]["y"] for i in region]
            if max(xs) - min(xs) >= max(ys) - min(ys):
                ordenada = sorted(region, key=lambda i: red.nodos[i]["x"])
            else:
                ordenada = sorted(region, key=lambda i: red.nodos[i]["y"])
            mitad = len(ordenada) // 2
            siguiente.append(ordenada[:mitad])
            siguiente.append(ordenada[mitad:])
            dividio = True
        if not dividio:
            break
        niveles.append(siguiente)
    return niveles


def nombre(i):
    return red.nodos[i]["etiqueta"]


# DIBUJO

def dibujar(titulo, valores, cmap, resaltadas=(), etiqueta_resaltada="", vmin=0, vmax=19,
            zoom=None, tamanos=None):
    # valores[i] es el numero que da el color del nodo i (None = sin energia/alcance)
    nc = estado["nodos_caidos"]
    ac = estado["aristas_caidas"]
    eje.clear()

    # aristas que siguen funcionando
    xs = []
    ys = []
    for a, b in an.aristas_activas(red.grafo, nc, ac):
        xs = xs + [red.nodos[a]["x"], red.nodos[b]["x"], None]
        ys = ys + [red.nodos[a]["y"], red.nodos[b]["y"], None]
    eje.plot(xs, ys, color="lightgray", linewidth=0.2)

    # aristas caidas (rojo punteado)
    xs = []
    ys = []
    for a, b in ac:
        if a in nc or b in nc:
            continue
        xs = xs + [red.nodos[a]["x"], red.nodos[b]["x"], None]
        ys = ys + [red.nodos[a]["y"], red.nodos[b]["y"], None]
    if xs:
        eje.plot(xs, ys, color="red", linestyle="--", linewidth=1.2, label="enlace caido")

    # aristas resaltadas (por ejemplo, las que no tienen respaldo)
    xs = []
    ys = []
    for a, b in resaltadas:
        xs = xs + [red.nodos[a]["x"], red.nodos[b]["x"], None]
        ys = ys + [red.nodos[a]["y"], red.nodos[b]["y"], None]
    if xs:
        eje.plot(xs, ys, color="red", linewidth=2.5, label=etiqueta_resaltada)

    # nodos
    px, py, pc, ps = [], [], [], []
    gx, gy = [], []
    for i in range(len(red.nodos)):
        if i in nc:
            continue
        if valores[i] is None:
            gx.append(red.nodos[i]["x"])
            gy.append(red.nodos[i]["y"])
        else:
            px.append(red.nodos[i]["x"])
            py.append(red.nodos[i]["y"])
            pc.append(valores[i])
            ps.append(5 if tamanos is None else tamanos[i])
    if gx:
        eje.scatter(gx, gy, s=5, color="gray", label="sin energia")
    eje.scatter(px, py, s=ps, c=pc, cmap=cmap, vmin=vmin, vmax=vmax)

    # subestaciones caidas
    if nc:
        cx = [red.nodos[i]["x"] for i in nc]
        cy = [red.nodos[i]["y"] for i in nc]
        eje.scatter(cx, cy, s=80, color="red", marker="x", linewidths=2, label="subestacion caida")

    # fuente
    f = estado["fuente"]
    if f not in nc:
        eje.scatter([red.nodos[f]["x"]], [red.nodos[f]["y"]], s=140, color="black",
                    marker="*", label="fuente " + nombre(f))

    eje.set_title(titulo, fontsize=11, fontweight="bold", color=COLOR_OSCURO)
    eje.spines["top"].set_visible(False)
    eje.spines["right"].set_visible(False)
    eje.set_xlabel("Este (m)")
    eje.set_ylabel("Norte (m)")
    eje.set_aspect("equal")
    if zoom is not None:
        eje.set_xlim(zoom[0], zoom[1])
        eje.set_ylim(zoom[2], zoom[3])
    if eje.get_legend_handles_labels()[0]:
        eje.legend(loc="upper left", fontsize=7)
    lienzo.draw()
    barra_herramientas.update()


def escribir(texto):
    caja_texto.config(state="normal")
    caja_texto.delete("1.0", "end")
    primera, _, resto = texto.partition("\n")
    caja_texto.insert("end", primera + "\n", "titulo")
    caja_texto.insert("end", resto)
    caja_texto.config(state="disabled")


def actualizar_fallas():
    texto = "Subestaciones caidas: "
    if estado["nodos_caidos"]:
        texto = texto + ", ".join(nombre(i) for i in estado["nodos_caidos"])
    else:
        texto = texto + "ninguna"
    texto = texto + "\nEnlaces caidos: " + str(len(estado["aristas_caidas"]))
    etiqueta_fallas.config(text=texto)


# VISTAS (cada una dibuja y escribe sus resultados)

def vista_grafo():
    estado["vista"] = vista_grafo
    n = len(red.nodos)
    zona = [0] * n
    for k in range(len(red.zonas)):
        for u in red.zonas[k]:
            zona[u] = k % 20
    aristas = an.aristas_activas(red.grafo, estado["nodos_caidos"], estado["aristas_caidas"])
    dibujar("Grafo completo: " + str(n) + " nodos, " + str(len(aristas))
            + " aristas (cada color es una zona)", zona, "tab20")
    escribir("GRAFO COMPLETO (divide y venceras)\n"
             "Nodos: " + str(n) + "\n"
             "Aristas activas: " + str(len(aristas)) + "\n"
             "Zonas: " + str(len(red.zonas)) + " (maximo " + str(red.TAM_ZONA) + " nodos)\n"
             "Aristas de frontera: " + str(len(red.fronteras)) + "\n"
             "Grado promedio: " + str(round(2 * len(aristas) / n, 1)))


def vista_regiones():
    estado["vista"] = vista_regiones
    n = len(red.nodos)
    grupo = [0] * n
    for k in range(3):
        for u in estado["grupos"][k]:
            grupo[u] = k
    internas = [0, 0, 0]
    cruzan = 0
    for a, b in an.aristas_activas(red.grafo, estado["nodos_caidos"], estado["aristas_caidas"]):
        if grupo[a] == grupo[b]:
            internas[grupo[a]] += 1
        else:
            cruzan += 1
    colores = ListedColormap(["tab:blue", "tab:orange", "tab:green"])
    dibujar("Regiones: un grupo de nodos por integrante", grupo, colores, vmin=0, vmax=2)

    texto = "REGIONES (un grupo por integrante)\n"
    for k in range(3):
        demanda = sum(red.nodos[u]["demanda"] for u in estado["grupos"][k])
        texto += ("Integrante " + str(k + 1) + ": " + str(len(estado["grupos"][k])) + " nodos, "
                  + str(internas[k]) + " aristas internas, demanda "
                  + str(round(demanda, 1)) + "\n")
    texto += "Aristas que cruzan entre regiones: " + str(cruzan)
    escribir(texto)


def vista_conectividad():
    estado["vista"] = vista_conectividad
    nc = estado["nodos_caidos"]
    ac = estado["aristas_caidas"]
    n = len(red.nodos)
    comp_bfs = an.componentes_conexas(red.grafo, nc, ac, "bfs")
    comp_dfs = an.componentes_conexas(red.grafo, nc, ac, "dfs")

    color = [None] * n
    for k in range(len(comp_bfs)):
        for u in comp_bfs[k]:
            color[u] = k % 20
    dibujar("Conectividad (BFS/DFS): " + str(len(comp_bfs)) + " componente(s)", color, "tab20")

    tamanos = sorted([len(c) for c in comp_bfs], reverse=True)
    f = estado["fuente"]
    texto = "CONECTIVIDAD (BFS/DFS)\n"
    texto += "Componentes con BFS: " + str(len(comp_bfs)) + " | con DFS: " + str(len(comp_dfs)) + "\n"
    texto += "Tamanos: " + str(tamanos[:6]) + ("..." if len(tamanos) > 6 else "") + "\n"
    if len(comp_bfs) == 1:
        texto += "La red es CONEXA: todas las subestaciones se alcanzan entre si."
    else:
        texto += "La red esta PARTIDA en " + str(len(comp_bfs)) + " partes."
    if f not in nc:
        nivel, _, _ = an.bfs(red.grafo, f, nc, ac)
        activos = n - len(nc)
        texto += ("\nDesde la fuente " + nombre(f) + " se alcanzan " + str(len(nivel))
                  + " de " + str(activos) + " subestaciones.")
    escribir(texto)


def vista_distribucion():
    estado["vista"] = vista_distribucion
    nc = estado["nodos_caidos"]
    ac = estado["aristas_caidas"]
    f = estado["fuente"]
    if f in nc:
        dibujar("La fuente esta caida: no hay distribucion", [None] * len(red.nodos), "viridis")
        escribir("La subestacion fuente " + nombre(f) + " esta caida. No se puede distribuir energia.")
        return

    n = len(red.nodos)
    nivel, orden, acumulada, hay_ciclo = an.distribucion(red.grafo, f, nc, ac)
    valido = an.orden_valido(red.grafo, orden, nivel, nc, ac)

    valores = [None] * n
    for u in nivel:
        valores[u] = nivel[u]
    maximo = max(nivel.values())
    dibujar("Distribucion de energia (orden topologico): nivel desde " + nombre(f),
            valores, "viridis", vmin=0, vmax=max(maximo, 1))

    demanda_total = sum(red.nodos[i]["demanda"] for i in range(n) if i not in nc)
    atendida = acumulada[f]
    sin_servicio = demanda_total - atendida
    texto = "ORDENAMIENTO TOPOLOGICO: DISTRIBUCION\n"
    texto += "Fuente: " + nombre(f) + " | niveles: " + str(maximo + 1) + "\n"
    texto += ("Subestaciones con energia: " + str(len(nivel)) + " | sin energia: "
              + str(n - len(nc) - len(nivel)) + "\n")
    texto += "Hay ciclo: " + str(hay_ciclo) + " | orden valido: " + str(valido) + "\n"
    texto += ("Demanda atendida: " + str(round(atendida, 1)) + " de " + str(round(demanda_total, 1))
              + " | sin servicio: " + str(round(sin_servicio, 1)) + " ("
              + str(round(100 * sin_servicio / demanda_total, 1)) + "%)\n")
    texto += "Primeras del orden: " + ", ".join(nombre(u) for u in orden[:6]) + "\n"

    # subestaciones de las que mas carga depende (carga aguas abajo)
    otros = [u for u in nivel if u != f]
    otros.sort(key=lambda u: acumulada[u], reverse=True)
    texto += "Mayor carga aguas abajo: "
    texto += ", ".join(nombre(u) + " (" + str(round(acumulada[u])) + ")" for u in otros[:4])
    escribir(texto)


def vista_redundancia():
    estado["vista"] = vista_redundancia
    nc = estado["nodos_caidos"]
    ac = estado["aristas_caidas"]
    n = len(red.nodos)
    componentes, numero, puentes = an.redundancia(red.grafo, nc, ac)

    color = [None] * n
    for k in range(len(componentes)):
        for u in componentes[k]:
            color[u] = k % 20
    dibujar("Redundancia (SCC): " + str(len(componentes)) + " componente(s), "
            + str(len(puentes)) + " arista(s) sin respaldo",
            color, "tab20", puentes, "sin respaldo")

    tamanos = sorted([len(c) for c in componentes], reverse=True)
    texto = "SCC: REDUNDANCIAS\n"
    texto += "Componentes fuertemente conexas: " + str(len(componentes)) + "\n"
    texto += "Tamanos: " + str(tamanos[:6]) + ("..." if len(tamanos) > 6 else "") + "\n"
    texto += "Aristas sin respaldo (puentes): " + str(len(puentes)) + "\n"
    if not puentes:
        texto += "No hay puntos unicos de falla: ninguna arista desconecta la red."
    else:
        for a, b in puentes[:8]:
            texto += "  " + nombre(a) + " - " + nombre(b) + "\n"
        if len(puentes) > 8:
            texto += "  ... y " + str(len(puentes) - 8) + " mas"
    escribir(texto)


# VISTAS: GRAFOS Y DIVIDE Y VENCERAS

def vista_nodo():
    # muestra como se modela un nodo: sus datos y su lista de vecinos
    estado["vista"] = vista_nodo
    n = len(red.nodos)
    i = estado["nodo_sel"]
    entrada_ver.delete(0, "end")
    entrada_ver.insert(0, nombre(i))
    nodo = red.nodos[i]
    vecinos_i = red.grafo[i]          # {vecino: distancia en metros}

    valores = [0] * n
    tamanos = [5] * n
    for v in vecinos_i:
        valores[v] = 1
        tamanos[v] = 18
    valores[i] = 2
    tamanos[i] = 70
    resaltadas = [(i, v) for v in vecinos_i]

    zoom = None
    if variable_zoom.get():
        xs = [nodo["x"]] + [red.nodos[v]["x"] for v in vecinos_i]
        ys = [nodo["y"]] + [red.nodos[v]["y"] for v in vecinos_i]
        margen = max(150, 0.15 * max(max(xs) - min(xs), max(ys) - min(ys)))
        zoom = (min(xs) - margen, max(xs) + margen, min(ys) - margen, max(ys) + margen)

    colores = ListedColormap(["#b0c4de", "tab:orange", "tab:red"])
    dibujar("Grafo: nodo " + nombre(i) + " y sus " + str(len(vecinos_i)) + " vecinos",
            valores, colores, resaltadas, "conexiones del nodo", vmin=0, vmax=2,
            zoom=zoom, tamanos=tamanos)

    zona = estado["zona_de"][i]
    cercanos = sorted(vecinos_i, key=lambda v: vecinos_i[v])
    texto = "GRAFOS: MODELO DE LA RED\n"
    texto += ("Nodo " + nombre(i) + " (codigo " + nodo["codigo"] + ") | zona " + str(zona + 1)
              + " de " + str(len(red.zonas)) + " (" + str(len(red.zonas[zona])) + " nodos) | "
              + "nodo de frontera: " + ("si" if i in estado["nodos_frontera"] else "no") + "\n")
    texto += ("Tension: " + nodo["tension"] + " | demanda: " + str(round(nodo["demanda"], 1))
              + " | potencia instalada: " + str(nodo["potencia"]) + "\n")
    texto += "Coordenadas UTM: " + str(round(nodo["x"])) + ", " + str(round(nodo["y"])) + "\n"
    texto += "Grado (aristas del nodo): " + str(len(vecinos_i)) + " | mas cercanos: "
    texto += ", ".join(nombre(v) + " (" + str(round(vecinos_i[v])) + " m)" for v in cercanos[:4]) + "\n"
    texto += ("Representacion: lista de adyacencia grafo[nodo][vecino] = distancia (m). "
              "El grafo tiene " + str(n) + " nodos y " + str(red.contar_aristas()) + " aristas.\n")
    texto += "Haz clic en otro nodo del mapa para ver el suyo."
    escribir(texto)


def vista_dyv():
    # muestra la recursion de divide y venceras, un nivel a la vez
    estado["vista"] = vista_dyv
    n = len(red.nodos)
    ultimo = len(estado["niveles"]) - 1
    k = estado["nivel_dyv"]
    regiones = estado["niveles"][k]
    parte = estado["parte"][k]
    etiqueta_nivel.config(text="Nivel " + str(k) + "/" + str(ultimo))

    valores = [parte[i] % 20 for i in range(n)]
    uniones = [e for e in red.fronteras if estado["union"][e] <= k]
    dibujar("Divide y venceras: nivel " + str(k) + " de " + str(ultimo) + " ("
            + str(len(regiones)) + " regiones)", valores, "tab20", uniones, "enlaces de union")

    tamanos = [len(r) for r in regiones]
    texto = "DIVIDE Y VENCERAS (nivel " + str(k) + " de " + str(ultimo) + ")\n"
    texto += ("Regiones en este nivel: " + str(len(regiones)) + " | nodos por region: de "
              + str(min(tamanos)) + " a " + str(max(tamanos)) + "\n")
    texto += "Enlaces de union creados hasta este nivel: " + str(len(uniones)) + "\n"
    texto += ("DIVIDIR: cada region se parte por la mitad segun su eje mas largo.\n"
              "CASO BASE: una region de " + str(red.TAM_ZONA) + " nodos o menos es una zona "
              "(todos sus nodos se conectan entre si).\n"
              "UNIR: se crean " + str(red.NUM_ENLACES) + " enlaces cortos entre las dos mitades (rojo).")
    if k == ultimo:
        dentro = sum(len(z) * (len(z) - 1) // 2 for z in red.zonas)
        texto += ("\nRESULTADO: " + str(len(red.zonas)) + " zonas, " + str(dentro)
                  + " aristas dentro de zonas, " + str(len(red.fronteras)) + " enlaces de frontera.\n"
                  "Pares comparados: " + str(red.comparaciones) + " (fuerza bruta: "
                  + str(n * (n - 1) // 2) + ")")
    escribir(texto)


def cambiar_nivel(cambio):
    ultimo = len(estado["niveles"]) - 1
    estado["nivel_dyv"] = max(0, min(ultimo, estado["nivel_dyv"] + cambio))
    vista_dyv()


def ver_nodo_escrito():
    codigo = entrada_ver.get().strip().upper()
    if codigo not in indice_por_etiqueta:
        messagebox.showerror("Subestacion no encontrada",
                             "No existe la etiqueta '" + codigo + "'. Ejemplo: E343801")
        return
    estado["nodo_sel"] = indice_por_etiqueta[codigo]
    vista_nodo()


def al_hacer_clic(evento):
    # en la vista de grafos, un clic selecciona el nodo mas cercano
    if estado["vista"] != vista_nodo:
        return
    if evento.inaxes != eje or evento.xdata is None:
        return
    if str(barra_herramientas.mode) != "":
        return                      # la barra esta en modo zoom o desplazamiento
    mejor = 0
    mejor_dist = None
    for i in range(len(red.nodos)):
        dx = red.nodos[i]["x"] - evento.xdata
        dy = red.nodos[i]["y"] - evento.ydata
        d = dx * dx + dy * dy
        if mejor_dist is None or d < mejor_dist:
            mejor = i
            mejor_dist = d
    estado["nodo_sel"] = mejor
    vista_nodo()


# EJEMPLO PEQUENO (6 subestaciones reales, para explicar cada algoritmo)

PALETA = ["#93c5fd", "#fcd34d", "#86efac", "#fca5a5", "#c4b5fd", "#fdba74"]


def ej_nodo(u):
    return estado["ej_letra"][u]


def ej_base(titulo, color_nodo, estilos=None, dirigidas=None, extra=None):
    # Dibuja el grafo pequeno a la izquierda. El panel de la derecha lo llena cada paso.
    #   estilos[(a, b)] = (color, grosor, trazo) para resaltar aristas
    #   dirigidas = lista de (desde, hasta) si se quieren flechas en vez de lineas
    #   extra[u] = texto que se escribe junto al nodo
    eje.clear()
    pos = estado["ej_pos"]
    mini = estado["ej_grafo"]
    estilos = estilos or {}
    extra = extra or {}

    for a in mini:
        for b in mini[a]:
            if a > b:
                continue
            color, grosor, trazo = estilos.get(an.clave(a, b), ("#94a3b8", 1.8, "-"))
            (x1, y1), (x2, y2) = pos[a], pos[b]
            if dirigidas is None or trazo == "--":
                eje.plot([x1, x2], [y1, y2], color=color, linewidth=grosor, linestyle=trazo, zorder=1)
            largo = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            px, py = -(y2 - y1) / largo, (x2 - x1) / largo      # perpendicular a la arista
            if py < -1e-9 or (abs(py) < 1e-9 and px < 0):
                px, py = -px, -py                               # siempre hacia arriba o la derecha
            lx, ly = (x1 + x2) / 2 + px * 0.42, (y1 + y2) / 2 + py * 0.42
            eje.text(lx, ly, str(round(mini[a][b])) + " m", fontsize=8, ha="center", va="center",
                     color="#475569", zorder=3, bbox=dict(facecolor="white", edgecolor="none", pad=0.6))
    if dirigidas is not None:
        for desde, hasta in dirigidas:
            color, grosor, trazo = estilos.get(an.clave(desde, hasta), ("#334155", 1.8, "-"))
            eje.annotate("", xy=pos[hasta], xytext=pos[desde], zorder=2,
                         arrowprops=dict(arrowstyle="-|>", color=color, lw=grosor,
                                         shrinkA=22, shrinkB=22, mutation_scale=15))

    for u in mini:
        x, y = pos[u]
        eje.add_patch(Circle((x, y), 0.68, facecolor=color_nodo[u], edgecolor=COLOR_OSCURO,
                             linewidth=1.5, zorder=4))
        eje.text(x, y, ej_nodo(u), ha="center", va="center", fontsize=15, fontweight="bold",
                 color=COLOR_OSCURO, zorder=5)
        eje.text(x, y - 1.05, nombre(u), ha="center", va="center", fontsize=8, color="#475569")
        if u in extra:
            # el texto extra va a la izquierda, a la derecha o encima segun donde este el nodo
            if x < 2:
                ex, ey, alin = x - 0.95, y, "right"
            elif x > 8:
                ex, ey, alin = x + 0.95, y, "left"
            else:
                ex, ey, alin = x, y + 1.05, "center"
            eje.text(ex, ey, extra[u], ha=alin, va="center", fontsize=9, fontweight="bold",
                     color=COLOR_ACENTO)

    eje.set_title(titulo, fontsize=11, fontweight="bold", color=COLOR_OSCURO)
    eje.set_xlim(-2.2, 20.6)
    eje.set_ylim(-1.4, 6.9)
    eje.set_aspect("equal")
    eje.axis("off")


def ej_caja(x, y, texto, color="#dbeafe", lado=0.8):
    eje.add_patch(Rectangle((x, y - lado / 2), lado, lado, facecolor=color,
                            edgecolor=COLOR_OSCURO, linewidth=1.2, zorder=3))
    eje.text(x + lado / 2, y, texto, ha="center", va="center", fontsize=11,
             fontweight="bold", color=COLOR_OSCURO, zorder=4)


def ej_fila(x, y, titulo, letras, colores=None, notas=None, separaciones=()):
    # una fila de cajas con letras (como las listas del ejemplo de clase)
    eje.text(x, y + 0.75, titulo, fontsize=9, fontweight="bold", color=COLOR_OSCURO)
    posicion = x
    for k in range(len(letras)):
        if k in separaciones:
            posicion += 0.45
        ej_caja(posicion, y, letras[k], colores[k] if colores else "#dbeafe")
        if notas:
            eje.text(posicion + 0.4, y - 0.62, notas[k], ha="center", va="center", fontsize=7.5,
                     color="#475569")
        posicion += 1.0


def ej_cerrar():
    lienzo.draw()
    barra_herramientas.update()


def ej_colores_zona():
    colores = {}
    for k in range(6):
        colores[estado["ej_nodos"][k]] = "#bfdbfe" if k < 3 else "#fde68a"
    return colores


def ej_enlaces():
    # los 3 enlaces entre las dos zonas: A-D, B-E y C-F
    nodos = estado["ej_nodos"]
    return [an.clave(nodos[k], nodos[k + 3]) for k in range(3)]


def ej_modelo():
    estado["vista"] = ej_modelo
    estilos = {}
    for e in ej_enlaces():
        estilos[e] = ("#dc2626", 2.4, "--")
    ej_base("Ejemplo: 6 subestaciones reales del dataset", ej_colores_zona(), estilos)
    eje.text(12.6, 6.0, "Nodo  Etiqueta   Tension  Demanda", fontsize=8.5, family="monospace",
             fontweight="bold", color=COLOR_OSCURO)
    for k in range(6):
        u = estado["ej_nodos"][k]
        fila = ("  " + ej_nodo(u) + "   " + nombre(u) + "  " + red.nodos[u]["tension"].ljust(8)
                + " " + str(round(red.nodos[u]["demanda"], 1)))
        eje.text(12.6, 5.2 - 0.75 * k, fila, fontsize=8.5, family="monospace", color="#334155")
    eje.text(12.6, 0.3, "Azul: zona 1   |   Amarillo: zona 2\nRojo punteado: enlaces de frontera",
             fontsize=8.5, color="#475569", va="center")
    ej_cerrar()
    escribir("EJEMPLO PEQUENO - PASO 1: EL MODELO\n"
             "Cada circulo es una subestacion real del dataset (nodo) y cada linea es una conexion (arista) "
             "con su distancia en metros.\n"
             "Son 2 zonas vecinas de 3 nodos cada una: dentro de una zona todos se conectan entre si, y las "
             "dos zonas se unen con 3 enlaces de frontera (divide y venceras).\n"
             "Los mismos algoritmos del programa se ejecutan sobre este mini grafo en los pasos siguientes.")


def ej_lista():
    estado["vista"] = ej_lista
    colores = ej_colores_zona()
    estilos = {}
    for e in ej_enlaces():
        estilos[e] = ("#dc2626", 2.4, "--")
    ej_base("Representacion: lista de adyacencia", colores, estilos)
    eje.text(12.6, 6.2, "grafo[nodo] = vecinos", fontsize=9, fontweight="bold", color=COLOR_OSCURO)
    ejemplo_codigo = ""
    for k in range(6):
        u = estado["ej_nodos"][k]
        y = 5.4 - 0.95 * k
        ej_caja(12.6, y, ej_nodo(u), colores[u])
        eje.text(13.55, y, "->", fontsize=11, va="center", color=COLOR_OSCURO)
        vecinos_u = sorted(estado["ej_grafo"][u], key=lambda v: ej_nodo(v))
        for j in range(len(vecinos_u)):
            ej_caja(14.2 + 0.95 * j, y, ej_nodo(vecinos_u[j]), "#e2e8f0")
        if k == 0:
            ejemplo_codigo = ("grafo['" + ej_nodo(u) + "'] = {"
                              + ", ".join("'" + ej_nodo(v) + "': " + str(round(estado["ej_grafo"][u][v]))
                                          for v in vecinos_u) + "}")
    ej_cerrar()
    escribir("EJEMPLO PEQUENO - PASO 2: LISTA DE ADYACENCIA\n"
             "Cada nodo guarda la lista de sus vecinos (y la distancia a cada uno). En el programa es el "
             "diccionario grafo[a][b] = distancia.\n"
             "Ejemplo: " + ejemplo_codigo + "\n"
             "El grafo real tiene " + str(len(red.nodos)) + " nodos y " + str(red.contar_aristas())
             + " aristas guardadas de esta forma.")


def ej_busqueda():
    estado["vista"] = ej_busqueda
    mini = estado["ej_grafo"]
    inicio = estado["ej_nodos"][0]
    nivel, padre, orden_bfs = an.bfs(mini, inicio)
    orden_dfs = an.dfs(mini, inicio)
    colores = {}
    for u in mini:
        colores[u] = PALETA[nivel[u] % len(PALETA)]
    estilos = {}
    for u in padre:
        if padre[u] is not None:
            estilos[an.clave(u, padre[u])] = (COLOR_OSCURO, 3.2, "-")
    ej_base("BFS desde " + ej_nodo(inicio) + ": nivel de cada nodo", colores, estilos,
            extra={u: "nivel " + str(nivel[u]) for u in mini})
    ej_fila(12.6, 5.2, "Orden BFS (por niveles)", [ej_nodo(u) for u in orden_bfs],
            [colores[u] for u in orden_bfs])
    ej_fila(12.6, 3.5, "Orden DFS (en profundidad)", [ej_nodo(u) for u in orden_dfs],
            [colores[u] for u in orden_dfs])
    ej_fila(12.6, 1.8, "Nivel de cada nodo", [ej_nodo(u) for u in sorted(mini, key=ej_nodo)],
            [colores[u] for u in sorted(mini, key=ej_nodo)],
            notas=[str(nivel[u]) for u in sorted(mini, key=ej_nodo)])
    ej_cerrar()
    componentes = an.componentes_conexas(mini)
    sin_enlaces = an.componentes_conexas(mini, quitar_aristas=set(ej_enlaces()))
    escribir("EJEMPLO PEQUENO - PASO 3: BFS/DFS (CONECTIVIDAD)\n"
             "BFS visita primero los vecinos de " + ej_nodo(inicio) + " (nivel 1), luego los de ellos (nivel 2). "
             "DFS baja por un camino hasta el fondo antes de volver.\n"
             "Las lineas gruesas son el arbol que recorre el BFS. Como se alcanzan los 6 nodos, hay "
             + str(len(componentes)) + " componente: el grafo es conexo.\n"
             "Si fallan los 3 enlaces de frontera, BFS/DFS encuentran " + str(len(sin_enlaces))
             + " componentes (la red se parte en dos).")


def ej_topologico():
    estado["vista"] = ej_topologico
    mini = estado["ej_grafo"]
    fuente = estado["ej_nodos"][0]
    nivel, orden, acumulada, hay_ciclo = an.distribucion(mini, fuente)
    posicion = {}
    for k in range(len(orden)):
        posicion[orden[k]] = k + 1
    colores = {}
    for u in mini:
        colores[u] = PALETA[nivel[u] % len(PALETA)]
    dirigidas = []
    for a in mini:
        for b in mini[a]:
            if a < b:
                if (nivel[a], a) < (nivel[b], b):
                    dirigidas.append((a, b))
                else:
                    dirigidas.append((b, a))
    ej_base("Orden topologico: la energia sale de " + ej_nodo(fuente), colores, None, dirigidas,
            extra={u: "orden " + str(posicion[u]) for u in mini})
    ej_fila(12.6, 5.0, "Orden topologico (Kahn)", [ej_nodo(u) for u in orden],
            [colores[u] for u in orden])
    ej_fila(12.6, 3.2, "Demanda acumulada hacia la fuente", [ej_nodo(u) for u in orden],
            [colores[u] for u in orden], notas=[str(round(acumulada[u])) for u in orden])
    ej_cerrar()
    total = sum(red.nodos[u]["demanda"] for u in mini)
    escribir("EJEMPLO PEQUENO - PASO 4: ORDENAMIENTO TOPOLOGICO\n"
             "Se orientan las aristas desde la fuente " + ej_nodo(fuente) + " (flechas: de menor a mayor nivel BFS). "
             "El grafo dirigido no tiene ciclos (hay ciclo: " + str(hay_ciclo) + ").\n"
             "Kahn: se toma un nodo sin flechas entrantes (" + ej_nodo(fuente) + "), se agrega al orden y se "
             "elimina; se repite. Ninguna flecha va hacia atras en el orden.\n"
             "Recorriendo el orden al reves, cada nodo entrega su demanda a su padre: en la fuente llegan "
             + str(round(acumulada[fuente])) + " (demanda total del ejemplo: " + str(round(total)) + ").")


def ej_scc():
    estado["vista"] = ej_scc
    mini = estado["ej_grafo"]
    enlaces = ej_enlaces()
    quitar = set()
    if variable_falla_ej.get():
        quitar = {enlaces[0], enlaces[1]}
    dirigido = an.orientar_dfs(mini, (), quitar)
    pila_final, transpuesto, componentes = an.kosaraju_detallado(dirigido)
    _, numero, puentes = an.redundancia(mini, (), quitar)
    claves_puentes = set(an.clave(a, b) for a, b in puentes)

    colores = {}
    for u in mini:
        colores[u] = PALETA[numero[u] % len(PALETA)]
    estilos = {}
    for e in quitar:
        estilos[e] = ("#dc2626", 2.0, "--")
    for e in claves_puentes:
        estilos[e] = ("#dc2626", 3.2, "-")
    dirigidas = []
    for u in dirigido:
        for v in dirigido[u]:
            if an.clave(u, v) not in quitar:
                dirigidas.append((u, v))
    ej_base("SCC (Kosaraju): " + str(len(componentes)) + " componente(s)", colores, estilos, dirigidas)

    ej_fila(12.6, 5.0, "Paso 1: pila final (tope = ultimo)", [ej_nodo(u) for u in pila_final],
            [colores[u] for u in pila_final])
    # componentes que encuentra el paso 3, una tras otra
    ordenadas = []
    separaciones = []
    for comp in componentes:
        if ordenadas:
            separaciones.append(len(ordenadas))
        ordenadas = ordenadas + sorted(comp, key=ej_nodo)
    ej_fila(12.6, 3.0, "Paso 3: componentes (SCC)", [ej_nodo(u) for u in ordenadas],
            [colores[u] for u in ordenadas], separaciones=separaciones)
    items = [ej_nodo(u) + "<-" + "".join(sorted(ej_nodo(v) for v in transpuesto[u]))
             for u in sorted(transpuesto, key=ej_nodo)]
    eje.text(12.6, 1.6, "Paso 2: grafo invertido", fontsize=9, fontweight="bold", color=COLOR_OSCURO)
    eje.text(12.6, 0.95, "   ".join(items[:3]), fontsize=8.5, family="monospace", color="#334155")
    eje.text(12.6, 0.4, "   ".join(items[3:]), fontsize=8.5, family="monospace", color="#334155")
    ej_cerrar()
    invertido = "  ".join(items)
    if puentes:
        a, b = puentes[0]
        conclusion = ("Hay " + str(len(puentes)) + " arista sin respaldo (rojo, " + ej_nodo(a) + "-" + ej_nodo(b)
                      + "): si falla, la red se parte. Con los 3 enlaces la red seria una sola SCC.")
    else:
        conclusion = ("Con los 3 enlaces hay una sola SCC: no hay ninguna arista sin respaldo. "
                      "Activa la casilla para ver que pasa si fallan 2 enlaces.")
    escribir("EJEMPLO PEQUENO - PASO 5: SCC CON KOSARAJU\n"
             "Primero se orienta el grafo con un DFS (las SCC solo existen en grafos dirigidos). "
             + ("Fallan 2 de los 3 enlaces de frontera (punteados).\n" if quitar else "Estan los 3 enlaces.\n")
             + "Kosaraju: 1) DFS y pila final, 2) invertir las flechas, 3) DFS en el invertido empezando por el tope.\n"
             "Invertido (X<-Y: antes Y apuntaba a X): " + invertido + "\n" + conclusion)


# ACCIONES DE LOS BOTONES

def refrescar():
    actualizar_fallas()
    if estado["vista"] is None:
        vista_grafo()
    else:
        estado["vista"]()


def limpiar_fallas():
    estado["nodos_caidos"] = set()
    estado["aristas_caidas"] = set()
    lista_enlaces.selection_clear(0, "end")
    refrescar()


def fallar_enlaces_seleccionados():
    for k in lista_enlaces.curselection():
        a, b = estado["enlaces"][k]
        estado["aristas_caidas"].add(an.clave(a, b))
    refrescar()


def fallar_subestacion():
    codigo = entrada_nodo.get().strip().upper()
    if codigo not in indice_por_etiqueta:
        messagebox.showerror("Subestacion no encontrada",
                             "No existe la etiqueta '" + codigo + "'. Ejemplo: E343801")
        return
    estado["nodos_caidos"].add(indice_por_etiqueta[codigo])
    refrescar()


def cambiar_fuente():
    codigo = entrada_fuente.get().strip().upper()
    if codigo not in indice_por_etiqueta:
        messagebox.showerror("Subestacion no encontrada",
                             "No existe la etiqueta '" + codigo + "'.")
        return
    estado["fuente"] = indice_por_etiqueta[codigo]
    refrescar()


def principales():
    # los 3 enlaces que unen las dos mitades mas grandes de la red
    return [an.clave(a, b) for a, b in red.fronteras[-3:]]


def escenario_a():
    estado["nodos_caidos"] = set()
    estado["aristas_caidas"] = {principales()[0], principales()[1]}
    actualizar_fallas()
    vista_redundancia()


def escenario_b():
    estado["nodos_caidos"] = set()
    estado["aristas_caidas"] = set(principales())
    actualizar_fallas()
    vista_distribucion()


def escenario_c():
    mayor = 0
    for i in range(len(red.nodos)):
        if i != estado["fuente"] and red.nodos[i]["demanda"] > red.nodos[mayor]["demanda"]:
            mayor = i
    estado["nodos_caidos"] = {mayor}
    estado["aristas_caidas"] = set()
    actualizar_fallas()
    vista_conectividad()


def guardar_imagen():
    ruta = filedialog.asksaveasfilename(defaultextension=".png",
                                        filetypes=[("Imagen PNG", "*.png")])
    if ruta:
        figura.savefig(ruta, dpi=150)
        messagebox.showinfo("Guardado", "Imagen guardada en:\n" + ruta)


# VENTANA

def construir_interfaz():
    global figura, eje, lienzo, caja_texto, lista_enlaces
    global entrada_fuente, entrada_nodo, etiqueta_fallas
    global entrada_ver, etiqueta_nivel, variable_zoom, variable_falla_ej, barra_herramientas

    raiz = tk.Tk()
    raiz.title("Red electrica de Chimbote - BFS/DFS, orden topologico y SCC")
    raiz.geometry("1350x850")
    aplicar_estilo(raiz)

    # banner superior
    banner = ttk.Frame(raiz, style="Banner.TFrame", padding=(16, 10))
    banner.pack(side="top", fill="x")
    ttk.Label(banner, text="Red electrica de Chimbote", style="Titulo.TLabel").pack(anchor="w")
    ttk.Label(banner, text="Grafos  |  Divide y venceras  |  BFS/DFS  |  Orden topologico  |  SCC (Kosaraju)",
              style="Sub.TLabel").pack(anchor="w")

    cuerpo = ttk.Frame(raiz)
    cuerpo.pack(side="top", fill="both", expand=True)

    # panel izquierdo: pestanas
    izquierda = ttk.Frame(cuerpo, padding=8)
    izquierda.pack(side="left", fill="y")
    pestanas = ttk.Notebook(izquierda, width=345, height=370)
    pestanas.pack(fill="x")

    # --- pestana 1: grafo y divide y venceras ---
    pagina = ttk.Frame(pestanas, padding=8)
    pestanas.add(pagina, text="Grafo")

    marco = ttk.LabelFrame(pagina, text="Grafo y nodos", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Button(marco, text="Grafo completo", command=vista_grafo).pack(fill="x")
    fila = ttk.Frame(marco)
    fila.pack(fill="x", pady=(4, 1))
    entrada_ver = ttk.Entry(fila, width=10)
    entrada_ver.pack(side="left", padx=(0, 4))
    ttk.Button(fila, text="Ver nodo y vecinos", command=ver_nodo_escrito).pack(side="left", fill="x", expand=True)
    variable_zoom = tk.BooleanVar(value=True)
    ttk.Checkbutton(marco, text="Zoom al nodo (o haz clic en un nodo)",
                    variable=variable_zoom).pack(anchor="w", pady=(2, 0))

    marco = ttk.LabelFrame(pagina, text="Divide y venceras", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Button(marco, text="Ver paso a paso", command=vista_dyv).pack(fill="x")
    fila = ttk.Frame(marco)
    fila.pack(fill="x", pady=(4, 1))
    ttk.Button(fila, text="< Anterior", command=lambda: cambiar_nivel(-1)).pack(side="left", fill="x", expand=True)
    etiqueta_nivel = ttk.Label(fila, text="", width=8, anchor="center")
    etiqueta_nivel.pack(side="left")
    ttk.Button(fila, text="Siguiente >", command=lambda: cambiar_nivel(1)).pack(side="left", fill="x", expand=True)
    ttk.Button(marco, text="Regiones (3 integrantes)", command=vista_regiones).pack(fill="x", pady=(4, 0))

    # --- pestana: ejemplo pequeno ---
    pagina = ttk.Frame(pestanas, padding=8)
    pestanas.add(pagina, text="Ejemplo")

    marco = ttk.LabelFrame(pagina, text="6 subestaciones reales", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Label(marco, text="Un grafo pequeno para explicar\ncada paso del proyecto.",
              justify="left").pack(anchor="w", pady=(0, 4))
    for texto, comando in [("1. El modelo (nodos y aristas)", ej_modelo),
                           ("2. Lista de adyacencia", ej_lista),
                           ("3. BFS / DFS", ej_busqueda),
                           ("4. Orden topologico", ej_topologico),
                           ("5. SCC (Kosaraju)", ej_scc)]:
        ttk.Button(marco, text=texto, command=comando).pack(fill="x", pady=1)
    variable_falla_ej = tk.BooleanVar(value=True)
    ttk.Checkbutton(marco, text="Paso 5: fallan 2 de los 3 enlaces", variable=variable_falla_ej,
                    command=ej_scc).pack(anchor="w", pady=(6, 0))

    # --- pestana 2: analisis ---
    pagina = ttk.Frame(pestanas, padding=8)
    pestanas.add(pagina, text="Analisis")

    marco = ttk.LabelFrame(pagina, text="Algoritmos", padding=6)
    marco.pack(fill="x", pady=3)
    for texto, comando in [("Conectividad (BFS/DFS)", vista_conectividad),
                           ("Distribucion (orden topologico)", vista_distribucion),
                           ("Redundancia (SCC)", vista_redundancia)]:
        ttk.Button(marco, text=texto, command=comando, style="Accent.TButton").pack(fill="x", pady=1)

    marco = ttk.LabelFrame(pagina, text="Escenarios rapidos", padding=6)
    marco.pack(fill="x", pady=3)
    for texto, comando in [("A: fallan 2 de 3 enlaces principales", escenario_a),
                           ("B: fallan los 3 enlaces principales", escenario_b),
                           ("C: cae la de mayor demanda", escenario_c)]:
        ttk.Button(marco, text=texto, command=comando, style="Aviso.TButton").pack(fill="x", pady=1)

    marco = ttk.LabelFrame(pagina, text="Fuente de energia", padding=6)
    marco.pack(fill="x", pady=3)
    entrada_fuente = ttk.Entry(marco)
    entrada_fuente.insert(0, nombre(estado["fuente"]))
    entrada_fuente.pack(fill="x")
    ttk.Button(marco, text="Cambiar fuente", command=cambiar_fuente).pack(fill="x", pady=(4, 0))

    # --- pestana 3: fallas manuales ---
    pagina = ttk.Frame(pestanas, padding=8)
    pestanas.add(pagina, text="Fallas")

    marco = ttk.LabelFrame(pagina, text="Enlaces de frontera", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Label(marco, text="Selecciona uno o varios (Ctrl):").pack(anchor="w")
    contenedor = ttk.Frame(marco)
    contenedor.pack(fill="x", pady=2)
    lista_enlaces = tk.Listbox(contenedor, selectmode="extended", height=6, exportselection=False,
                               width=34, font=("Consolas", 9), bg="#ffffff", relief="flat",
                               highlightthickness=1, highlightbackground=COLOR_BORDE,
                               selectbackground=COLOR_ACENTO)
    barra = ttk.Scrollbar(contenedor, command=lista_enlaces.yview)
    lista_enlaces.config(yscrollcommand=barra.set)
    lista_enlaces.pack(side="left", fill="x", expand=True)
    barra.pack(side="right", fill="y")
    for k in range(len(estado["enlaces"])):
        a, b = estado["enlaces"][k]
        marca = "[PRINCIPAL] " if k < 3 else ""
        lista_enlaces.insert("end", marca + nombre(a) + " - " + nombre(b)
                             + " (" + str(round(red.grafo[a][b])) + " m)")
    ttk.Button(marco, text="Hacer fallar los seleccionados",
               command=fallar_enlaces_seleccionados).pack(fill="x", pady=(4, 0))

    marco = ttk.LabelFrame(pagina, text="Subestacion", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Label(marco, text="Etiqueta (ej. E343801):").pack(anchor="w")
    entrada_nodo = ttk.Entry(marco)
    entrada_nodo.pack(fill="x")
    ttk.Button(marco, text="Hacer fallar subestacion", command=fallar_subestacion).pack(fill="x", pady=(4, 0))

    # estado de fallas (se ve siempre, en cualquier pestana)
    marco = ttk.LabelFrame(izquierda, text="Estado de fallas", padding=6)
    marco.pack(fill="x", pady=(8, 3))
    etiqueta_fallas = ttk.Label(marco, text="", wraplength=310, justify="left")
    etiqueta_fallas.pack(anchor="w", pady=(0, 4))
    ttk.Button(marco, text="Limpiar todas las fallas", command=limpiar_fallas).pack(fill="x")

    ttk.Button(izquierda, text="Guardar imagen actual (PNG)", command=guardar_imagen).pack(fill="x", pady=(6, 0))

    # panel derecho: grafico y resultados
    derecha = ttk.Frame(cuerpo, padding=4)
    derecha.pack(side="right", fill="both", expand=True)

    figura = Figure(figsize=(9, 5.2), dpi=100, facecolor="#ffffff")
    eje = figura.add_subplot(111)
    figura.subplots_adjust(left=0.1, right=0.97, top=0.93, bottom=0.13)
    lienzo = FigureCanvasTkAgg(figura, master=derecha)
    barra_herramientas = NavigationToolbar2Tk(lienzo, derecha)
    barra_herramientas.update()
    lienzo.mpl_connect("button_press_event", al_hacer_clic)

    caja_texto = tk.Text(derecha, height=9, wrap="word", font=("Consolas", 10), state="disabled",
                         bg="#ffffff", relief="flat", padx=10, pady=8,
                         highlightthickness=1, highlightbackground=COLOR_BORDE)
    caja_texto.tag_configure("titulo", font=("Consolas", 10, "bold"), foreground=COLOR_ACENTO)
    caja_texto.pack(side="bottom", fill="x", pady=(4, 0))
    lienzo.get_tk_widget().pack(side="top", fill="both", expand=True)

    actualizar_fallas()
    vista_grafo()
    return raiz


def main():
    preparar_datos()
    raiz = construir_interfaz()
    raiz.mainloop()


if __name__ == "__main__":
    main()