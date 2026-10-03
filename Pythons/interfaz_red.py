# INTERFAZ GRAFICA - RED ELECTRICA DE CHIMBOTE
#
#
# Ejecutar:  python interfaz_red.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.colors import ListedColormap
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

import red_electrica_chimbote as red
import analisis_red as an


# ESTADO DE LA APLICACION

estado = {
    "fuente": 0,             # indice de la subestacion que alimenta la red
    "nodos_caidos": set(),   # subestaciones que fallan
    "aristas_caidas": set(), # enlaces que fallan, como clave(a, b)
    "enlaces": [],           # enlaces de frontera que se muestran en la lista
    "grupos": [],            # los 3 grupos de nodos (uno por integrante)
    "vista": None,           # ultima vista dibujada (para refrescar al cambiar fallas)
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


def nombre(i):
    return red.nodos[i]["etiqueta"]


# DIBUJO

def dibujar(titulo, valores, cmap, resaltadas=(), etiqueta_resaltada="", vmin=0, vmax=19):
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
    px, py, pc = [], [], []
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
    if gx:
        eje.scatter(gx, gy, s=5, color="gray", label="sin energia")
    eje.scatter(px, py, s=5, c=pc, cmap=cmap, vmin=vmin, vmax=vmax)

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

    eje.set_title(titulo, fontsize=10)
    eje.set_xlabel("Este (m)")
    eje.set_ylabel("Norte (m)")
    eje.set_aspect("equal")
    if eje.get_legend_handles_labels()[0]:
        eje.legend(loc="upper left", fontsize=7)
    lienzo.draw()


def escribir(texto):
    caja_texto.config(state="normal")
    caja_texto.delete("1.0", "end")
    caja_texto.insert("1.0", texto)
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

    raiz = tk.Tk()
    raiz.title("Red electrica de Chimbote - BFS/DFS, orden topologico y SCC")
    raiz.geometry("1350x820")

    # panel izquierdo
    izquierda = ttk.Frame(raiz, padding=8)
    izquierda.pack(side="left", fill="y")

    marco = ttk.LabelFrame(izquierda, text="1. Ver", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Button(marco, text="Grafo completo", command=vista_grafo).pack(fill="x")
    ttk.Button(marco, text="Regiones (3 integrantes)", command=vista_regiones).pack(fill="x")

    marco = ttk.LabelFrame(izquierda, text="2. Analizar", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Button(marco, text="Conectividad (BFS/DFS)", command=vista_conectividad).pack(fill="x")
    ttk.Button(marco, text="Distribucion (orden topologico)", command=vista_distribucion).pack(fill="x")
    ttk.Button(marco, text="Redundancia (SCC)", command=vista_redundancia).pack(fill="x")

    marco = ttk.LabelFrame(izquierda, text="3. Escenarios rapidos", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Button(marco, text="A: fallan 2 de 3 enlaces principales", command=escenario_a).pack(fill="x")
    ttk.Button(marco, text="B: fallan los 3 enlaces principales", command=escenario_b).pack(fill="x")
    ttk.Button(marco, text="C: cae la subestacion de mayor demanda", command=escenario_c).pack(fill="x")

    marco = ttk.LabelFrame(izquierda, text="4. Fallas manuales", padding=6)
    marco.pack(fill="x", pady=3)
    ttk.Label(marco, text="Enlaces de frontera (varios con Ctrl):").pack(anchor="w")
    contenedor = ttk.Frame(marco)
    contenedor.pack(fill="x")
    lista_enlaces = tk.Listbox(contenedor, selectmode="extended", height=7, exportselection=False,
                               width=34)
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
               command=fallar_enlaces_seleccionados).pack(fill="x", pady=2)

    ttk.Label(marco, text="Subestacion (etiqueta, ej. E343801):").pack(anchor="w")
    entrada_nodo = ttk.Entry(marco)
    entrada_nodo.pack(fill="x")
    ttk.Button(marco, text="Hacer fallar subestacion", command=fallar_subestacion).pack(fill="x", pady=2)

    etiqueta_fallas = ttk.Label(marco, text="", wraplength=250, justify="left")
    etiqueta_fallas.pack(anchor="w", pady=2)
    ttk.Button(marco, text="Limpiar todas las fallas", command=limpiar_fallas).pack(fill="x")

    marco = ttk.LabelFrame(izquierda, text="5. Fuente de energia", padding=6)
    marco.pack(fill="x", pady=3)
    entrada_fuente = ttk.Entry(marco)
    entrada_fuente.insert(0, nombre(estado["fuente"]))
    entrada_fuente.pack(fill="x")
    ttk.Button(marco, text="Cambiar fuente", command=cambiar_fuente).pack(fill="x", pady=2)

    ttk.Button(izquierda, text="Guardar imagen actual (PNG)", command=guardar_imagen).pack(fill="x", pady=6)

    # panel derecho: grafico y resultados
    derecha = ttk.Frame(raiz, padding=4)
    derecha.pack(side="right", fill="both", expand=True)

    figura = Figure(figsize=(9, 6.2), dpi=100)
    eje = figura.add_subplot(111)
    lienzo = FigureCanvasTkAgg(figura, master=derecha)
    barra_herramientas = NavigationToolbar2Tk(lienzo, derecha)
    barra_herramientas.update()
    lienzo.get_tk_widget().pack(side="top", fill="both", expand=True)

    caja_texto = tk.Text(derecha, height=9, wrap="word", font=("Consolas", 10), state="disabled")
    caja_texto.pack(side="bottom", fill="x")

    actualizar_fallas()
    vista_grafo()
    return raiz


def main():
    preparar_datos()
    raiz = construir_interfaz()
    raiz.mainloop()


if __name__ == "__main__":
    main()
