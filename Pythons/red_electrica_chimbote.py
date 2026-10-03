#   - Grafos de modelamiento nodos electricos
#   - Divide y venceras: dividir regiones geograficas

import csv
import math
import matplotlib.pyplot as plt

ARCHIVO = "SED_1500_CHIMBOTE.csv"
TAM_ZONA = 24       # maximo de subestaciones por zona
NUM_ENLACES = 3     # enlaces que unen dos regiones vecinas

nodos = []          # cada nodo es una subestacion (un diccionario con sus datos)
grafo = {}          # lista de adyacencia: grafo[a][b] = distancia en metros
zonas = []          # cada zona es una lista de nodos
fronteras = []      # aristas que unen dos regiones
comparaciones = 0   # cuantos pares de nodos se compararon



# GRAFO

def leer_datos():
    archivo = open(ARCHIVO, encoding="utf-8")
    lector = csv.DictReader(archivo)
    for fila in lector:
        nodo = {
            "codigo": fila["COD"],
            "etiqueta": fila["ETIQUETA"],
            "x": float(fila["X"]),
            "y": float(fila["Y"]),
            "tension": fila["TENSION_1"],
            "potencia": float(fila["POT_INST"]),
            "demanda": float(fila["MAX_DEM_SP"]) + float(fila["MAX_DEM_AP"]),
        }
        nodos.append(nodo)
    archivo.close()

    # al inicio el grafo no tiene aristas
    for i in range(len(nodos)):
        grafo[i] = {}


def distancia(a, b):
    global comparaciones
    comparaciones = comparaciones + 1
    dx = nodos[a]["x"] - nodos[b]["x"]
    dy = nodos[a]["y"] - nodos[b]["y"]
    return math.sqrt(dx * dx + dy * dy)


def agregar_arista(a, b, peso):
    # grafo no dirigido: se guarda en los dos sentidos
    grafo[a][b] = peso
    grafo[b][a] = peso


def contar_aristas():
    total = 0
    for a in grafo:
        total = total + len(grafo[a])
    return total // 2



# DIVIDE Y VENCERAS

def dividir(region):
    # CASO BASE: la region es pequena, se vuelve una zona
    # y se conectan todos sus nodos entre si
    if len(region) <= TAM_ZONA:
        for i in range(len(region)):
            for j in range(i + 1, len(region)):
                a = region[i]
                b = region[j]
                agregar_arista(a, b, distancia(a, b))
        zonas.append(region)
        return

    # DIVIDIR: se ve si la region es mas ancha o mas alta
    # y se ordena por ese lado para partirla por la mitad
    lista_x = []
    lista_y = []
    for i in region:
        lista_x.append(nodos[i]["x"])
        lista_y.append(nodos[i]["y"])
    ancho = max(lista_x) - min(lista_x)
    alto = max(lista_y) - min(lista_y)

    if ancho >= alto:
        ordenada = sorted(region, key=lambda i: nodos[i]["x"])
    else:
        ordenada = sorted(region, key=lambda i: nodos[i]["y"])

    mitad = len(ordenada) // 2
    izquierda = ordenada[:mitad]
    derecha = ordenada[mitad:]

    # VENCER: se resuelve cada mitad por separado
    dividir(izquierda)
    dividir(derecha)

    # se unen las dos mitades
    unir(izquierda, derecha)


def unir(izquierda, derecha):
    # como las listas estan ordenadas, los nodos mas cercanos al corte
    # son los ultimos de la izquierda y los primeros de la derecha
    cerca_izq = izquierda[-TAM_ZONA:]
    cerca_der = derecha[:TAM_ZONA]

    pares = []
    for a in cerca_izq:
        for b in cerca_der:
            pares.append((distancia(a, b), a, b))
    pares.sort()

    # se eligen los enlaces mas cortos sin repetir nodos
    usados = []
    cantidad = 0
    for peso, a, b in pares:
        if a not in usados and b not in usados:
            agregar_arista(a, b, peso)
            fronteras.append((a, b))
            usados.append(a)
            usados.append(b)
            cantidad = cantidad + 1
            if cantidad == NUM_ENLACES:
                break



# RESULTADOS

def mostrar_resumen():
    n = len(nodos)
    demanda_total = 0
    potencia_total = 0
    for nodo in nodos:
        demanda_total = demanda_total + nodo["demanda"]
        potencia_total = potencia_total + nodo["potencia"]

    print("Nodos (subestaciones):", n)
    print("Aristas del grafo:", contar_aristas())
    print("Aristas de frontera:", len(fronteras))
    print("Zonas:", len(zonas))
    print("Pares comparados:", comparaciones)
    print("Pares con fuerza bruta:", n * (n - 1) // 2)
    print("Demanda total:", round(demanda_total, 2))
    print("Potencia instalada total:", round(potencia_total, 2))

    # demanda y potencia de cada zona
    print()
    print("Zona", "Nodos", "Demanda", "Potencia")
    numero = 1
    for zona in zonas:
        demanda = 0
        potencia = 0
        for i in zona:
            demanda = demanda + nodos[i]["demanda"]
            potencia = potencia + nodos[i]["potencia"]
        print(numero, len(zona), round(demanda, 2), round(potencia, 2))
        numero = numero + 1


def dibujar_grafo():
    # aristas normales (dentro de cada zona)
    xs = []
    ys = []
    for a in grafo:
        for b in grafo[a]:
            if a < b:
                xs = xs + [nodos[a]["x"], nodos[b]["x"], None]
                ys = ys + [nodos[a]["y"], nodos[b]["y"], None]
    plt.plot(xs, ys, color="steelblue", linewidth=0.2)

    # aristas de frontera (unen regiones)
    xs = []
    ys = []
    for a, b in fronteras:
        xs = xs + [nodos[a]["x"], nodos[b]["x"], None]
        ys = ys + [nodos[a]["y"], nodos[b]["y"], None]
    plt.plot(xs, ys, color="red", linewidth=1.2)

    # nodos
    xs = []
    ys = []
    for nodo in nodos:
        xs.append(nodo["x"])
        ys.append(nodo["y"])
    plt.scatter(xs, ys, s=3, color="black")

    plt.title("Red electrica de Chimbote: " + str(len(nodos)) + " nodos")
    plt.xlabel("Este (m)")
    plt.ylabel("Norte (m)")
    plt.axis("equal")
    plt.savefig("grafo.png", dpi=150)
    plt.show()



# PROGRAMA PRINCIPAL

leer_datos()
todos = list(range(len(nodos)))
dividir(todos)
mostrar_resumen()
dibujar_grafo()
