

import os
import csv
import math
import collections
import matplotlib.pyplot as plt

# el CSV se busca en la misma carpeta que este archivo .py
CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO = os.path.join(CARPETA, "SED_1500_CHIMBOTE.csv")
GRADO_MIN = 3       # conexiones minimas que se le piden a cada subestacion
CAP_LINEA = 6200    # capacidad de cada linea en kW (= potencia de la SED mas grande)
INFINITO = 10 ** 9
EPS = 0.000001

nodos = []
grafo = {}



# DATOS

def leer_datos():
    archivo = open(ARCHIVO, encoding="utf-8")
    lector = csv.DictReader(archivo)
    for fila in lector:
        nodo = {
            "codigo": fila["COD"],
            "etiqueta": fila["ETIQUETA"],
            "x": float(fila["X"]),
            "y": float(fila["Y"]),
            "potencia": float(fila["POT_INST"]),
            "demanda": float(fila["MAX_DEM_SP"]) + float(fila["MAX_DEM_AP"]),
        }
        nodos.append(nodo)
    archivo.close()


def distancia(a, b):
    dx = nodos[a]["x"] - nodos[b]["x"]
    dy = nodos[a]["y"] - nodos[b]["y"]
    return math.sqrt(dx * dx + dy * dy)


def lineas_candidatas():
    # todas las lineas posibles entre dos subestaciones,
    # ordenadas de la mas corta a la mas larga
    candidatas = []
    for a in range(len(nodos)):
        for b in range(a + 1, len(nodos)):
            candidatas.append((distancia(a, b), a, b))
    candidatas.sort()
    return candidatas



# PARTE 1: ALGORITMO VORAZ (seleccion de conexiones)


def seleccionar_conexiones(candidatas, grado_min):
    n = len(nodos)
    grado = [0] * n
    elegidas = []

    for peso, a, b in candidatas:
        if grado[a] < grado_min or grado[b] < grado_min:
            elegidas.append((peso, a, b))
            grado[a] = grado[a] + 1
            grado[b] = grado[b] + 1

    # grupos que quedaron despues del paso 1
    grupo = etiquetar_grupos(elegidas)
    cantidad_grupos = max(grupo) + 1

    uniones = []
    for peso, a, b in candidatas:
        if cantidad_grupos == 1:
            break
        if grupo[a] != grupo[b]:
            uniones.append((peso, a, b))
            elegidas.append((peso, a, b))
            viejo = grupo[b]
            for i in range(n):
                if grupo[i] == viejo:
                    grupo[i] = grupo[a]
            cantidad_grupos = cantidad_grupos - 1

    return elegidas, uniones


def etiquetar_grupos(lineas):
    # recorrido BFS: cada nodo recibe el numero de su grupo
    n = len(nodos)
    vecinos = {}
    for i in range(n):
        vecinos[i] = []
    for peso, a, b in lineas:
        vecinos[a].append(b)
        vecinos[b].append(a)

    grupo = [-1] * n
    actual = 0
    for inicio in range(n):
        if grupo[inicio] == -1:
            grupo[inicio] = actual
            cola = collections.deque([inicio])
            while len(cola) > 0:
                u = cola.popleft()
                for v in vecinos[u]:
                    if grupo[v] == -1:
                        grupo[v] = actual
                        cola.append(v)
            actual = actual + 1
    return grupo


def armar_grafo(lineas):
    red = {}
    for i in range(len(nodos)):
        red[i] = {}
    for peso, a, b in lineas:
        red[a][b] = peso
        red[b][a] = peso
    return red


def largo_total(lineas):
    total = 0
    for peso, a, b in lineas:
        total = total + peso
    return total



# PARTE 2: FLUJO MAXIMO (Ford-Fulkerson con BFS)

def nodo_fuente():
    mejor = 0
    for i in range(len(nodos)):
        if nodos[i]["potencia"] > nodos[mejor]["potencia"]:
            mejor = i
    return mejor


def armar_red(capacidad):
    # red residual: red[u][v] = capacidad que todavia se puede usar de u a v
    n = len(nodos)
    fuente = nodo_fuente()
    red = {}
    for i in range(n + 2):
        red[i] = {}

    for a in grafo:
        for b in grafo[a]:
            red[a][b] = capacidad

    red[n][fuente] = INFINITO       # S -> fuente
    red[fuente][n] = 0
    for i in range(n):
        red[i][n + 1] = nodos[i]["demanda"]   # subestacion -> T
        red[n + 1][i] = 0
    return red


def flujo_maximo(red, s, t):
    flujo = 0
    caminos = 0
    while True:
        # BFS: busca un camino de s a t con capacidad libre
        padre = {s: None}
        cola = collections.deque([s])
        while len(cola) > 0 and t not in padre:
            u = cola.popleft()
            for v in red[u]:
                if red[u][v] > EPS and v not in padre:
                    padre[v] = u
                    cola.append(v)

        if t not in padre:
            break   # ya no hay caminos: el flujo es maximo

        # cuello de botella del camino
        minimo = INFINITO
        v = t
        while padre[v] is not None:
            u = padre[v]
            if red[u][v] < minimo:
                minimo = red[u][v]
            v = u

        # se actualiza la red residual
        v = t
        while padre[v] is not None:
            u = padre[v]
            red[u][v] = red[u][v] - minimo
            red[v][u] = red[v][u] + minimo
            v = u

        flujo = flujo + minimo
        caminos = caminos + 1
    return flujo, caminos


def corte_minimo(red, s):
    # nodos que todavia se alcanzan desde S en la red residual
    alcanzables = {s}
    cola = collections.deque([s])
    while len(cola) > 0:
        u = cola.popleft()
        for v in red[u]:
            if red[u][v] > EPS and v not in alcanzables:
                alcanzables.add(v)
                cola.append(v)

    # lineas llenas que separan los alcanzables del resto
    corte = []
    for a in alcanzables:
        if a < len(nodos):
            for b in grafo[a]:
                if b not in alcanzables:
                    corte.append((a, b))
    return corte, alcanzables


def resolver_flujo(capacidad):
    n = len(nodos)
    red = armar_red(capacidad)
    flujo, caminos = flujo_maximo(red, n, n + 1)
    return flujo, caminos, red


def capacidad_minima(demanda_total):
    # busqueda binaria: menor capacidad de linea que atiende toda la demanda
    bajo = 0
    alto = demanda_total
    for vuelta in range(18):
        medio = (bajo + alto) / 2
        flujo, caminos, red = resolver_flujo(medio)
        if flujo >= demanda_total - 0.01:
            alto = medio
        else:
            bajo = medio
    return alto



# PARTE 3: REFUERZO VORAZ GUIADO POR EL FLUJO


def reforzar_red(candidatas, demanda_total):
    n = len(nodos)
    red = armar_red(CAP_LINEA)
    usadas = set()
    for a in grafo:
        for b in grafo[a]:
            usadas.add((a, b))

    flujo = 0
    agregadas = []
    while True:
        # se sigue desde el flujo que ya habia (la red residual se conserva)
        extra, caminos = flujo_maximo(red, n, n + 1)
        flujo = flujo + extra
        if flujo >= demanda_total - 0.01:
            break

        corte, alcanzables = corte_minimo(red, n)
        for peso, a, b in candidatas:
            if (a in alcanzables) != (b in alcanzables) and (a, b) not in usadas:
                grafo[a][b] = peso
                grafo[b][a] = peso
                red[a][b] = CAP_LINEA
                red[b][a] = CAP_LINEA
                usadas.add((a, b))
                agregadas.append((peso, a, b))
                break
    return agregadas, flujo



# GRAFICOS

def trazar_lineas(lineas, color, ancho, nombre):
    xs = []
    ys = []
    for peso, a, b in lineas:
        xs = xs + [nodos[a]["x"], nodos[b]["x"], None]
        ys = ys + [nodos[a]["y"], nodos[b]["y"], None]
    plt.plot(xs, ys, color=color, linewidth=ancho, label=nombre)


def trazar_nodos():
    xs = []
    ys = []
    for nodo in nodos:
        xs.append(nodo["x"])
        ys.append(nodo["y"])
    plt.scatter(xs, ys, s=3, color="black")


def cerrar_grafico(titulo, archivo):
    plt.title(titulo)
    plt.xlabel("Este (m)")
    plt.ylabel("Norte (m)")
    plt.axis("equal")
    plt.legend(markerscale=2, fontsize=8)
    plt.savefig(archivo, dpi=150)


def dibujar_voraz(elegidas, uniones):
    plt.figure(1, figsize=(9, 8))
    trazar_lineas(elegidas, "steelblue", 0.5, "lineas elegidas (" + str(len(elegidas)) + ")")
    trazar_lineas(uniones, "red", 2, "uniones entre grupos (paso 2)")
    trazar_nodos()
    cerrar_grafico("Conexiones elegidas por el voraz", os.path.join(CARPETA, "fig_voraz.png"))


def dibujar_flujo(red, corte):
    n = len(nodos)
    plt.figure(2, figsize=(9, 8))

    # lineas del corte minimo (el cuello de botella)
    xs = []
    ys = []
    for a, b in corte:
        xs = xs + [nodos[a]["x"], nodos[b]["x"], None]
        ys = ys + [nodos[a]["y"], nodos[b]["y"], None]
    plt.plot(xs, ys, color="red", linewidth=4, label="corte minimo (" + str(len(corte)) + " linea)")

    # nodos: verde si recibe toda su demanda, naranja si recibe una parte, gris si nada
    for color, nombre in [("green", "abastecida"), ("orange", "parcial"), ("lightgray", "sin energia")]:
        xs = []
        ys = []
        for i in range(n):
            demanda = nodos[i]["demanda"]
            fraccion = (demanda - red[i][n + 1]) / demanda
            if nombre == "abastecida" and fraccion >= 0.999:
                xs.append(nodos[i]["x"])
                ys.append(nodos[i]["y"])
            if nombre == "parcial" and 0.001 < fraccion < 0.999:
                xs.append(nodos[i]["x"])
                ys.append(nodos[i]["y"])
            if nombre == "sin energia" and fraccion <= 0.001:
                xs.append(nodos[i]["x"])
                ys.append(nodos[i]["y"])
        plt.scatter(xs, ys, s=5, color=color, label=nombre + " (" + str(len(xs)) + ")")

    fuente = nodo_fuente()
    plt.scatter([nodos[fuente]["x"]], [nodos[fuente]["y"]], s=120, color="black",
                marker="*", label="fuente " + nodos[fuente]["etiqueta"])
    cerrar_grafico("Flujo maximo con " + str(CAP_LINEA) + " kW por linea", os.path.join(CARPETA, "fig_flujo.png"))


def dibujar_refuerzo(elegidas, agregadas):
    plt.figure(3, figsize=(9, 8))
    trazar_lineas(elegidas, "lightsteelblue", 0.5, "red del voraz")
    trazar_lineas(agregadas, "red", 1.5, "lineas agregadas (" + str(len(agregadas)) + ")")
    trazar_nodos()
    cerrar_grafico("Refuerzo guiado por el corte minimo", os.path.join(CARPETA, "fig_refuerzo.png"))



# PROGRAMA PRINCIPAL

leer_datos()
n = len(nodos)
demanda_total = 0
for nodo in nodos:
    demanda_total = demanda_total + nodo["demanda"]

candidatas = lineas_candidatas()

print("Subestaciones:", n)
print("Demanda total (kW):", round(demanda_total, 2))
print("Subestacion fuente:", nodos[nodo_fuente()]["etiqueta"])
print("Lineas posibles:", len(candidatas))

# 1. voraz
print()
print("=== 1. ALGORITMO VORAZ ===")
print("Grado minimo -> lineas, largo (km), uniones del paso 2, demanda atendida con", CAP_LINEA, "kW por linea")
for grado_min in [2, 3, 4, 5]:
    elegidas, uniones = seleccionar_conexiones(candidatas, grado_min)
    grafo = armar_grafo(elegidas)
    f, c, r = resolver_flujo(CAP_LINEA)
    print(grado_min, "->", len(elegidas), "lineas,",
          round(largo_total(elegidas) / 1000, 1), "km,",
          len(uniones), "uniones,",
          round(100 * f / demanda_total, 1), "%")

elegidas, uniones = seleccionar_conexiones(candidatas, GRADO_MIN)
grafo = armar_grafo(elegidas)
grupos = etiquetar_grupos(elegidas)
print()
print("Con GRADO_MIN =", GRADO_MIN)
print("Lineas elegidas:", len(elegidas), "de", len(candidatas),
      "(", round(100 * len(elegidas) / len(candidatas), 2), "% )")
print("Largo (km):", round(largo_total(elegidas) / 1000, 1))
print("Uniones del paso 2:", len(uniones))
print("Grupos finales:", max(grupos) + 1)
dibujar_voraz(elegidas, uniones)

#  2. flujo maximo sobre la red elegida
print()
print("=== 2. FLUJO MAXIMO ===")
flujo, caminos, red = resolver_flujo(CAP_LINEA)
corte, alcanzables = corte_minimo(red, n)
print("Capacidad por linea (kW):", CAP_LINEA)
print("Flujo maximo (kW):", round(flujo, 2))
print("Demanda atendida:", round(100 * flujo / demanda_total, 2), "%")
print("Caminos de aumento:", caminos)
print("Lineas en el corte minimo:", len(corte))

sin_servicio = 0
for i in range(n):
    if red[i][n + 1] > 0.001:
        sin_servicio = sin_servicio + 1
print("Subestaciones con demanda sin atender:", sin_servicio)

# teorema flujo maximo - corte minimo: la capacidad del corte es igual al flujo
# (lineas del corte + demanda de las subestaciones que quedan del lado de la fuente)
demanda_lado_fuente = 0
for i in alcanzables:
    if i < n:
        demanda_lado_fuente = demanda_lado_fuente + nodos[i]["demanda"]
print("Subestaciones del lado de la fuente:", len(alcanzables) - 1)
print("Capacidad del corte (kW):", round(len(corte) * CAP_LINEA + demanda_lado_fuente, 2))

print()
print("Capacidad por linea -> flujo maximo")
for cap in [1000, 3000, 6200, 15000, 30000]:
    f, c, r = resolver_flujo(cap)
    print(cap, "kW ->", round(f, 2), "kW (", round(100 * f / demanda_total, 1), "%)")
minima = capacidad_minima(demanda_total)
print("Capacidad minima por linea para atender el 100% (kW):", round(minima, 1))
dibujar_flujo(red, corte)

# 3. refuerzo voraz guiado por el flujo
print()
print("=== 3. REFUERZO GUIADO POR EL CORTE MINIMO ===")
agregadas, flujo_final = reforzar_red(candidatas, demanda_total)
print("Lineas agregadas:", len(agregadas))
print("Cable agregado (km):", round(largo_total(agregadas) / 1000, 2))
print("Red final:", len(elegidas) + len(agregadas), "lineas,",
      round((largo_total(elegidas) + largo_total(agregadas)) / 1000, 1), "km")
print("Flujo maximo final (kW):", round(flujo_final, 2),
      "(", round(100 * flujo_final / demanda_total, 2), "% de la demanda )")
dibujar_refuerzo(elegidas, agregadas)

plt.show()
