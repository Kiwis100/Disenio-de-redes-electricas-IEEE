# ANALISIS DE LA RED ELECTRICA DE CHIMBOTE
#   - BFS/DFS: analisis de conectividad
#   - Ordenamiento topologico: distribucion de energia
#   - SCC: detectar redundancias
#   - Programacion dinamica: refuerzo de la red con un presupuesto (mochila 0/1)
#   - DP en grafos: rutas eficientes (Bellman-Ford y Floyd-Warshall)
#
# Usa el grafo que construye red_electrica_chimbote.py (divide y venceras).
# Todos los algoritmos estan programados a mano (sin networkx).
#
# Para simular fallos, todas las funciones reciben:
#   quitar_nodos:   conjunto de nodos que fallan
#   quitar_aristas: conjunto de aristas que fallan, guardadas como clave(a, b)

import math

import matplotlib.pyplot as plt
import red_electrica_chimbote as red


# AUXILIARES

def clave(a, b):
    # una arista no dirigida se identifica siempre con (menor, mayor)
    if a < b:
        return (a, b)
    return (b, a)


def vecinos(grafo, u, quitar_nodos, quitar_aristas):
    # vecinos de u que siguen funcionando
    lista = []
    for v in grafo[u]:
        if v in quitar_nodos:
            continue
        if clave(u, v) in quitar_aristas:
            continue
        lista.append(v)
    return lista


def aristas_activas(grafo, quitar_nodos, quitar_aristas):
    lista = []
    for a in grafo:
        if a in quitar_nodos:
            continue
        for b in grafo[a]:
            if a < b and b not in quitar_nodos and clave(a, b) not in quitar_aristas:
                lista.append((a, b))
    return lista


# BFS / DFS: ANALISIS DE CONECTIVIDAD

def bfs(grafo, inicio, quitar_nodos=(), quitar_aristas=()):
    # devuelve el nivel de cada nodo alcanzado, su padre y el orden de visita
    nivel = {inicio: 0}
    padre = {inicio: None}
    cola = [inicio]
    i = 0
    while i < len(cola):
        u = cola[i]
        i = i + 1
        for v in vecinos(grafo, u, quitar_nodos, quitar_aristas):
            if v not in nivel:
                nivel[v] = nivel[u] + 1
                padre[v] = u
                cola.append(v)
    return nivel, padre, cola


def dfs(grafo, inicio, quitar_nodos=(), quitar_aristas=()):
    # DFS con pila propia (con 1500 nodos la recursion se pasaria del limite)
    # devuelve el orden en que se visitan los nodos
    visitado = {inicio}
    orden = [inicio]
    pila = [[inicio, vecinos(grafo, inicio, quitar_nodos, quitar_aristas), 0]]
    while pila:
        tope = pila[-1]
        u = tope[0]
        lista = tope[1]
        if tope[2] == len(lista):
            pila.pop()
            continue
        v = lista[tope[2]]
        tope[2] = tope[2] + 1
        if v not in visitado:
            visitado.add(v)
            orden.append(v)
            pila.append([v, vecinos(grafo, v, quitar_nodos, quitar_aristas), 0])
    return orden


def componentes_conexas(grafo, quitar_nodos=(), quitar_aristas=(), usar="bfs"):
    # cada componente es una lista de nodos que se alcanzan entre si
    visitado = set()
    componentes = []
    for inicio in grafo:
        if inicio in quitar_nodos or inicio in visitado:
            continue
        if usar == "bfs":
            _, _, orden = bfs(grafo, inicio, quitar_nodos, quitar_aristas)
        else:
            orden = dfs(grafo, inicio, quitar_nodos, quitar_aristas)
        for v in orden:
            visitado.add(v)
        componentes.append(orden)
    return componentes


# ORDENAMIENTO TOPOLOGICO: DISTRIBUCION DE ENERGIA

def distribucion(grafo, fuente, quitar_nodos=(), quitar_aristas=()):
    # 1) BFS desde la fuente: da el nivel de cada subestacion
    nivel, padre, _ = bfs(grafo, fuente, quitar_nodos, quitar_aristas)

    # 2) se orienta cada arista del nodo de menor (nivel, indice) al de mayor.
    #    Como (nivel, indice) es un orden total, el grafo dirigido no tiene ciclos
    dag = {}
    entradas = {}
    for u in nivel:
        dag[u] = []
        entradas[u] = 0
    for a in nivel:
        for b in vecinos(grafo, a, quitar_nodos, quitar_aristas):
            if a < b:
                if (nivel[a], a) < (nivel[b], b):
                    dag[a].append(b)
                    entradas[b] = entradas[b] + 1
                else:
                    dag[b].append(a)
                    entradas[a] = entradas[a] + 1

    # 3) ordenamiento topologico (Kahn): se saca siempre un nodo sin entradas
    cola = []
    for u in nivel:
        if entradas[u] == 0:
            cola.append(u)
    orden = []
    i = 0
    while i < len(cola):
        u = cola[i]
        i = i + 1
        orden.append(u)
        for v in dag[u]:
            entradas[v] = entradas[v] - 1
            if entradas[v] == 0:
                cola.append(v)

    # si quedaron nodos sin ordenar habria un ciclo (no deberia pasar)
    hay_ciclo = len(orden) != len(nivel)

    # 4) demanda acumulada: se recorre el orden al reves y cada nodo entrega
    #    su demanda acumulada a su padre del BFS (asi no se cuenta dos veces)
    acumulada = {}
    for u in nivel:
        acumulada[u] = red.nodos[u]["demanda"]
    for u in reversed(orden):
        if padre[u] is not None:
            acumulada[padre[u]] = acumulada[padre[u]] + acumulada[u]

    return nivel, orden, acumulada, hay_ciclo


def orden_valido(grafo, orden, nivel, quitar_nodos=(), quitar_aristas=()):
    # comprueba que toda arista dirigida va de un nodo anterior a uno posterior
    posicion = {}
    for k in range(len(orden)):
        posicion[orden[k]] = k
    for a, b in aristas_activas(grafo, quitar_nodos, quitar_aristas):
        if a in nivel and b in nivel:
            if (nivel[a], a) < (nivel[b], b):
                desde, hasta = a, b
            else:
                desde, hasta = b, a
            if posicion[desde] > posicion[hasta]:
                return False
    return True


# SCC: DETECTAR REDUNDANCIAS

def orientar_dfs(grafo, quitar_nodos=(), quitar_aristas=()):
    # Se recorre el grafo con DFS: la arista que descubre un nodo nuevo va hacia
    # abajo (u -> v) y las demas aristas van hacia el ancestro (retroceso).
    # Una red conexa sin aristas puente queda fuertemente conexa (Robbins, 1939).
    dirigido = {}
    for u in grafo:
        if u not in quitar_nodos:
            dirigido[u] = []
    visitado = set()
    orientada = set()
    for raiz in dirigido:
        if raiz in visitado:
            continue
        visitado.add(raiz)
        pila = [[raiz, vecinos(grafo, raiz, quitar_nodos, quitar_aristas), 0]]
        while pila:
            tope = pila[-1]
            u = tope[0]
            lista = tope[1]
            if tope[2] == len(lista):
                pila.pop()
                continue
            v = lista[tope[2]]
            tope[2] = tope[2] + 1
            if clave(u, v) in orientada:
                continue
            orientada.add(clave(u, v))
            dirigido[u].append(v)
            if v not in visitado:
                visitado.add(v)
                pila.append([v, vecinos(grafo, v, quitar_nodos, quitar_aristas), 0])
    return dirigido


def kosaraju_detallado(dirigido):
    # componentes fuertemente conexas con el algoritmo de Kosaraju (con pilas propias):
    #   1) DFS sobre el grafo anotando el orden en que TERMINA cada nodo
    #   2) se invierte el sentido de todas las aristas (grafo transpuesto)
    #   3) DFS sobre el transpuesto empezando por el nodo que termino ultimo:
    #      cada arbol que se recorre es una componente fuertemente conexa

    # paso 1: orden de termino
    visitado = set()
    terminado = []
    for raiz in dirigido:
        if raiz in visitado:
            continue
        visitado.add(raiz)
        pila = [[raiz, 0]]
        while pila:
            tope = pila[-1]
            u = tope[0]
            if tope[1] < len(dirigido[u]):
                v = dirigido[u][tope[1]]
                tope[1] = tope[1] + 1
                if v not in visitado:
                    visitado.add(v)
                    pila.append([v, 0])
            else:
                pila.pop()
                terminado.append(u)

    # paso 2: grafo transpuesto
    transpuesto = {}
    for u in dirigido:
        transpuesto[u] = []
    for u in dirigido:
        for v in dirigido[u]:
            transpuesto[v].append(u)

    # paso 3: DFS en el transpuesto, en orden inverso de termino
    visitado = set()
    componentes = []
    for raiz in reversed(terminado):
        if raiz in visitado:
            continue
        visitado.add(raiz)
        componente = [raiz]
        pila = [raiz]
        while pila:
            u = pila.pop()
            for v in transpuesto[u]:
                if v not in visitado:
                    visitado.add(v)
                    componente.append(v)
                    pila.append(v)
        componentes.append(componente)
    return terminado, transpuesto, componentes


def scc_kosaraju(dirigido):
    # devuelve solo las componentes (los pasos internos los usa el ejemplo de la interfaz)
    return kosaraju_detallado(dirigido)[2]


def redundancia(grafo, quitar_nodos=(), quitar_aristas=()):
    # devuelve las SCC y las aristas sin respaldo (puentes):
    # son las aristas que unen dos SCC distintas
    dirigido = orientar_dfs(grafo, quitar_nodos, quitar_aristas)
    componentes = scc_kosaraju(dirigido)
    numero = {}
    for k in range(len(componentes)):
        for u in componentes[k]:
            numero[u] = k
    puentes = []
    for a, b in aristas_activas(grafo, quitar_nodos, quitar_aristas):
        if numero[a] != numero[b]:
            puentes.append((a, b))
    return componentes, numero, puentes


# PROGRAMACION DINAMICA: REFUERZO DE LA RED CON PRESUPUESTO
#
# Despues de unas fallas, algunos enlaces quedan sin respaldo (puentes, ver SCC).
# Cada puente tiene una CRITICIDAD: los kW que dejarian de recibir energia si ese enlace fallara.
# Un puente se refuerza reconstruyendo uno de los enlaces caidos que cruzan el mismo corte, y su
# costo es la longitud del enlace en metros. Con un presupuesto de cableado limitado hay que elegir
# que puentes reforzar para cubrir la mayor criticidad: es el problema de la mochila 0/1.

UNIDAD_M = 10    # para la tabla, los costos se redondean hacia arriba a multiplos de 10 m


def diseno_minimo():
    # Diseno de menor costo: de los 3 enlaces que unen cada par de regiones se deja solo el mas
    # corto. Devuelve los enlaces que se quitan. La red sigue conexa, pero sin respaldo.
    quitar = set()
    for k in range(0, len(red.fronteras), red.NUM_ENLACES):
        grupo = red.fronteras[k:k + red.NUM_ENLACES]
        grupo = sorted(grupo, key=lambda e: red.grafo[e[0]][e[1]])
        for a, b in grupo[1:]:
            quitar.add(clave(a, b))
    return quitar


def demanda_alcanzada(nivel):
    # suma de la demanda de los nodos que llegaron a ser alcanzados por un BFS
    total = 0.0
    for u in nivel:
        total = total + red.nodos[u]["demanda"]
    return total


def riesgo_de_puente(grafo, fuente, puente, quitar_nodos, quitar_aristas, alcanzada_antes):
    # kW que dejan de alcanzarse desde la fuente si falla este puente
    sin_puente = set(quitar_aristas)
    sin_puente.add(clave(puente[0], puente[1]))
    nivel, _, _ = bfs(grafo, fuente, quitar_nodos, sin_puente)
    return alcanzada_antes - demanda_alcanzada(nivel)


def candidatos_refuerzo(grafo, fuente, quitar_nodos=(), quitar_aristas=()):
    # Un candidato por cada puente que se puede reforzar. Devuelve (candidatos, puentes):
    #   puente:   la arista sin respaldo
    #   refuerzo: el enlace caido mas corto que cruza el corte de ese puente (el que se reconstruiria)
    #   costo:    longitud del refuerzo en metros
    #   riesgo:   criticidad del puente en kW
    # Para que cada enlace proteja un solo puente (y asi la mochila sea exacta, sin cobrar dos veces
    # el mismo cable), solo se consideran enlaces caidos que cruzan el corte de UN unico puente.
    candidatos = []
    if fuente in quitar_nodos:
        return candidatos, []
    _, _, puentes = redundancia(grafo, quitar_nodos, quitar_aristas)
    nivel0, _, _ = bfs(grafo, fuente, quitar_nodos, quitar_aristas)
    antes = demanda_alcanzada(nivel0)

    # a cuantos puentes cruza cada enlace caido
    caidos = []
    for c, d in quitar_aristas:
        if c not in quitar_nodos and d not in quitar_nodos:
            caidos.append((c, d))
    cruza = {}
    for e in caidos:
        cruza[e] = []
    for k in range(len(puentes)):
        a, b = puentes[k]
        sin_puente = set(quitar_aristas)
        sin_puente.add(clave(a, b))
        lado, _, _ = bfs(grafo, a, quitar_nodos, sin_puente)      # nodos del lado de "a"
        for c, d in caidos:
            if (c in lado) != (d in lado):                         # el enlace cruza el corte
                cruza[(c, d)].append(k)

    for k in range(len(puentes)):
        mejor = None
        for e in caidos:
            if cruza[e] == [k]:
                if mejor is None or grafo[e[0]][e[1]] < grafo[mejor[0]][mejor[1]]:
                    mejor = e
        if mejor is None:
            continue
        candidatos.append({"puente": puentes[k], "refuerzo": mejor, "costo": grafo[mejor[0]][mejor[1]],
                           "riesgo": riesgo_de_puente(grafo, fuente, puentes[k], quitar_nodos,
                                                      quitar_aristas, antes)})
    return candidatos, puentes


def mochila_tabla(costos, valores, unidad=UNIDAD_M):
    # Mochila 0/1 con programacion dinamica.
    #   tabla[i][j] = mayor criticidad que se cubre usando solo los primeros i candidatos
    #                 con un presupuesto de j unidades de cable
    #   tabla[i][j] = max( tabla[i-1][j],  tabla[i-1][j - peso_i] + valor_i )
    # La tabla se arma hasta el costo total de todos los candidatos, asi sirve para cualquier presupuesto.
    pesos = []
    for c in costos:
        pesos.append(int(math.ceil(c / unidad)))
    capacidad = sum(pesos)
    tabla = [[0.0] * (capacidad + 1)]
    for i in range(1, len(costos) + 1):
        fila = tabla[i - 1][:]
        peso = pesos[i - 1]
        valor = valores[i - 1]
        for j in range(peso, capacidad + 1):
            con_este = tabla[i - 1][j - peso] + valor
            if con_este > fila[j]:
                fila[j] = con_este
        tabla.append(fila)
    return tabla, pesos


def mochila_elegidos(tabla, pesos, presupuesto, unidad=UNIDAD_M):
    # Recorre la tabla de atras hacia adelante para saber que candidatos se eligieron
    j = min(int(presupuesto // unidad), len(tabla[0]) - 1)
    elegidos = []
    for i in range(len(pesos), 0, -1):
        if tabla[i][j] != tabla[i - 1][j]:        # el candidato i hizo subir el valor: se eligio
            elegidos.append(i - 1)
            j = j - pesos[i - 1]
    elegidos.reverse()
    return elegidos


def mochila_fuerza_bruta(costos, valores, presupuesto, unidad=UNIDAD_M):
    # Solo para comprobar el resultado: prueba los 2^n subconjuntos (sirve con n pequeno)
    n = len(costos)
    pesos = []
    for c in costos:
        pesos.append(int(math.ceil(c / unidad)))
    cap = int(presupuesto // unidad)
    mejor = 0.0
    for mascara in range(1 << n):
        peso = 0
        valor = 0.0
        for i in range(n):
            if mascara & (1 << i):
                peso = peso + pesos[i]
                valor = valor + valores[i]
        if peso <= cap and valor > mejor:
            mejor = valor
    return mejor


def refuerzo_dp(grafo, fuente, presupuesto, quitar_nodos=(), quitar_aristas=()):
    candidatos, puentes = candidatos_refuerzo(grafo, fuente, quitar_nodos, quitar_aristas)
    costos = [c["costo"] for c in candidatos]
    valores = [c["riesgo"] for c in candidatos]
    tabla, pesos = mochila_tabla(costos, valores)
    elegidos = mochila_elegidos(tabla, pesos, presupuesto)

    # verificacion: se reconstruyen de verdad los enlaces elegidos y se vuelve a buscar puentes
    nuevos = set(quitar_aristas)
    for i in elegidos:
        nuevos.discard(clave(candidatos[i]["refuerzo"][0], candidatos[i]["refuerzo"][1]))
    _, _, puentes_despues = redundancia(grafo, quitar_nodos, nuevos)

    return {"candidatos": candidatos, "puentes": puentes, "tabla": tabla, "pesos": pesos,
            "elegidos": elegidos, "enlaces": [candidatos[i]["refuerzo"] for i in elegidos],
            "costo": sum(costos[i] for i in elegidos), "protegido": sum(valores[i] for i in elegidos),
            "riesgo_total": sum(valores), "puentes_despues": len(puentes_despues)}


# DP EN GRAFOS: RUTAS EFICIENTES

def bellman_ford(grafo, fuente, quitar_nodos=(), quitar_aristas=(), historial=None):
    # Menor distancia (en metros de cable) desde la fuente hasta cada subestacion.
    # Programacion dinamica: dist_k[v] = menor distancia usando a lo sumo k aristas
    #   dist_k[v] = min( dist_{k-1}[v],  dist_{k-1}[u] + peso(u, v) )   para cada arista (u, v)
    # Se repite hasta que una ronda ya no mejora nada. Devuelve (dist, padre, rondas).
    # Si se pasa una lista en "historial", se guarda la distancia de cada nodo despues de cada ronda.
    infinito = float("inf")
    dist = {}
    padre = {}
    for u in grafo:
        if u not in quitar_nodos:
            dist[u] = infinito
            padre[u] = None
    dist[fuente] = 0.0
    arcos = []
    for a in dist:
        for b in vecinos(grafo, a, quitar_nodos, quitar_aristas):
            arcos.append((a, b, grafo[a][b]))
    if historial is not None:
        historial.append(dict(dist))
    rondas = 0
    for _ in range(len(dist) - 1):
        nuevo = dict(dist)                 # la ronda k usa solo lo calculado en la ronda k-1
        hubo_cambio = False
        for u, v, w in arcos:
            if dist[u] + w < nuevo[v]:
                nuevo[v] = dist[u] + w
                padre[v] = u
                hubo_cambio = True
        dist = nuevo
        if historial is not None:
            historial.append(dict(dist))
        if not hubo_cambio:
            break
        rondas = rondas + 1
    return dist, padre, rondas


def camino_minimo(padre, dist, destino):
    # reconstruye la ruta fuente -> destino siguiendo los padres (vacia si no hay ruta)
    if dist[destino] == float("inf"):
        return []
    ruta = []
    u = destino
    while u is not None:
        ruta.append(u)
        u = padre[u]
    ruta.reverse()
    return ruta


def largo_camino(grafo, ruta):
    total = 0.0
    for k in range(len(ruta) - 1):
        total = total + grafo[ruta[k]][ruta[k + 1]]
    return total


def grafo_de_zonas(quitar_aristas=()):
    # Grafo reducido: cada zona es un nodo y dos zonas se unen si tienen un enlace de frontera activo.
    # El peso es la distancia entre los centros de las dos zonas (aproximacion de cuanto cable hay
    # que recorrer para pasar de una a otra). Devuelve (matriz de distancias, centros, zona de cada nodo).
    zona_de = {}
    centros = []
    for k in range(len(red.zonas)):
        sx = 0.0
        sy = 0.0
        for u in red.zonas[k]:
            zona_de[u] = k
            sx = sx + red.nodos[u]["x"]
            sy = sy + red.nodos[u]["y"]
        centros.append((sx / len(red.zonas[k]), sy / len(red.zonas[k])))
    n = len(red.zonas)
    d = []
    for i in range(n):
        d.append([float("inf")] * n)
        d[i][i] = 0.0
    for a, b in red.fronteras:
        if clave(a, b) in quitar_aristas:
            continue
        i = zona_de[a]
        j = zona_de[b]
        if i != j:
            dx = centros[i][0] - centros[j][0]
            dy = centros[i][1] - centros[j][1]
            w = math.sqrt(dx * dx + dy * dy)
            if w < d[i][j]:
                d[i][j] = w
                d[j][i] = w
    return d, centros, zona_de


def floyd_warshall(d):
    # Distancias entre todos los pares de zonas. Programacion dinamica:
    #   dist_k[i][j] = menor distancia de i a j pasando solo por las zonas 0..k como intermedias
    #   dist_k[i][j] = min( dist_{k-1}[i][j],  dist_{k-1}[i][k] + dist_{k-1}[k][j] )
    # "siguiente[i][j]" guarda la primera zona de la ruta de i a j, para poder reconstruirla.
    n = len(d)
    infinito = float("inf")
    dist = []
    for fila in d:
        dist.append(fila[:])
    siguiente = []
    for i in range(n):
        siguiente.append([None] * n)
        for j in range(n):
            if i != j and dist[i][j] < infinito:
                siguiente[i][j] = j
    for k in range(n):
        for i in range(n):
            dik = dist[i][k]
            if dik == infinito:
                continue
            for j in range(n):
                nuevo = dik + dist[k][j]
                if nuevo < dist[i][j]:
                    dist[i][j] = nuevo
                    siguiente[i][j] = siguiente[i][k]
    return dist, siguiente


def ruta_entre_zonas(siguiente, i, j):
    if i == j:
        return [i]
    if siguiente[i][j] is None:
        return []
    ruta = [i]
    while i != j:
        i = siguiente[i][j]
        ruta.append(i)
    return ruta


def resumen_zonas(dist):
    # Excentricidad de una zona = su ruta mas larga hacia cualquier otra zona alcanzable.
    # La zona central es la de menor excentricidad. El diametro es la mayor distancia entre dos zonas.
    n = len(dist)
    excentricidad = []
    diametro = (0, 0, 0.0)
    inalcanzables = 0
    for i in range(n):
        mayor = 0.0
        for j in range(n):
            if dist[i][j] == float("inf"):
                inalcanzables = inalcanzables + 1
                continue
            if dist[i][j] > mayor:
                mayor = dist[i][j]
            if dist[i][j] > diametro[2]:
                diametro = (i, j, dist[i][j])
        excentricidad.append(mayor)
    central = 0
    for i in range(n):
        if excentricidad[i] < excentricidad[central]:
            central = i
    return central, excentricidad, diametro, inalcanzables


# FIGURAS

def figura(archivo, titulo, valores, cmap, resaltadas=(), quitar_nodos=(), quitar_aristas=()):
    xs = []
    ys = []
    for a, b in aristas_activas(red.grafo, quitar_nodos, quitar_aristas):
        xs = xs + [red.nodos[a]["x"], red.nodos[b]["x"], None]
        ys = ys + [red.nodos[a]["y"], red.nodos[b]["y"], None]
    plt.figure(figsize=(9, 8))
    plt.plot(xs, ys, color="lightgray", linewidth=0.2)

    xs = []
    ys = []
    for a, b in resaltadas:
        xs = xs + [red.nodos[a]["x"], red.nodos[b]["x"], None]
        ys = ys + [red.nodos[a]["y"], red.nodos[b]["y"], None]
    plt.plot(xs, ys, color="red", linewidth=1.5)

    px = []
    py = []
    pc = []
    for i in range(len(red.nodos)):
        if i in quitar_nodos:
            continue
        px.append(red.nodos[i]["x"])
        py.append(red.nodos[i]["y"])
        pc.append(valores[i])
    plt.scatter(px, py, s=4, c=pc, cmap=cmap)
    for i in quitar_nodos:
        plt.scatter([red.nodos[i]["x"]], [red.nodos[i]["y"]], s=60, color="red", marker="x")

    plt.title(titulo)
    plt.xlabel("Este (m)")
    plt.ylabel("Norte (m)")
    plt.axis("equal")
    plt.savefig(archivo, dpi=150)
    plt.close()
    print("Figura guardada:", archivo)


# PROGRAMA PRINCIPAL

def nombre(i):
    return red.nodos[i]["etiqueta"]


def main():
    red.leer_datos()
    red.dividir(list(range(len(red.nodos))))
    grafo = red.grafo
    n = len(red.nodos)
    demanda_total = sum(nodo["demanda"] for nodo in red.nodos)

    print("=== 1. BFS/DFS: CONECTIVIDAD ===")
    comp_bfs = componentes_conexas(grafo, usar="bfs")
    comp_dfs = componentes_conexas(grafo, usar="dfs")
    print("Componentes con BFS:", len(comp_bfs), "| con DFS:", len(comp_dfs))
    print("El grafo es conexo:", len(comp_bfs) == 1 and len(comp_bfs[0]) == n)

    # la fuente es la subestacion de mayor potencia instalada
    fuente = 0
    for i in range(n):
        if red.nodos[i]["potencia"] > red.nodos[fuente]["potencia"]:
            fuente = i
    print("Fuente:", nombre(fuente), "| potencia:", red.nodos[fuente]["potencia"])

    print()
    print("=== 2. ORDENAMIENTO TOPOLOGICO: DISTRIBUCION ===")
    nivel, orden, acumulada, hay_ciclo = distribucion(grafo, fuente)
    print("Nodos ordenados:", len(orden), "de", n, "| hay ciclo:", hay_ciclo)
    print("Orden valido:", orden_valido(grafo, orden, nivel))
    print("Niveles de distribucion:", max(nivel.values()) + 1)
    print("Demanda acumulada en la fuente:", round(acumulada[fuente], 2))
    print("Demanda total de la red:      ", round(demanda_total, 2))
    print("Primeras 5 subestaciones del orden:", [nombre(u) for u in orden[:5]])

    print()
    print("=== 3. SCC: REDUNDANCIAS (red completa) ===")
    comps, numero, puentes = redundancia(grafo)
    print("SCC:", len(comps), "| aristas sin respaldo (puentes):", len(puentes))

    # los 3 ultimos enlaces de frontera son los que unen las dos mitades principales
    principales = red.fronteras[-3:]
    cl_principales = [clave(a, b) for a, b in principales]

    print()
    print("=== ESCENARIO A: fallan 2 de los 3 enlaces principales ===")
    quitar_a = {cl_principales[0], cl_principales[1]}
    comps_a = componentes_conexas(grafo, quitar_aristas=quitar_a)
    scc_a, numero_a, puentes_a = redundancia(grafo, quitar_aristas=quitar_a)
    print("Componentes conexas:", len(comps_a))
    print("SCC:", len(scc_a), "| puentes:", len(puentes_a))
    for a, b in puentes_a:
        print("  Sin respaldo:", nombre(a), "-", nombre(b))
    print("Estos puentes son el unico enlace entre las dos mitades: si falla, se parte la red.")

    print()
    print("=== ESCENARIO B: fallan los 3 enlaces principales ===")
    quitar_b = set(cl_principales)
    comps_b = componentes_conexas(grafo, quitar_aristas=quitar_b)
    print("Componentes conexas:", len(comps_b), "| tamanos:", [len(c) for c in comps_b])
    nivel_b, orden_b, acum_b, _ = distribucion(grafo, fuente, quitar_aristas=quitar_b)
    sin_servicio = demanda_total - acum_b[fuente]
    print("Subestaciones sin energia:", n - len(nivel_b))
    print("Demanda sin servicio:", round(sin_servicio, 2),
          "(" + str(round(100 * sin_servicio / demanda_total, 1)) + "%)")

    print()
    print("=== ESCENARIO C: falla la subestacion de mayor demanda ===")
    mayor = 0
    for i in range(n):
        if i != fuente and red.nodos[i]["demanda"] > red.nodos[mayor]["demanda"]:
            mayor = i
    quitar_c = {mayor}
    comps_c = componentes_conexas(grafo, quitar_nodos=quitar_c)
    scc_c, _, puentes_c = redundancia(grafo, quitar_nodos=quitar_c)
    print("Falla:", nombre(mayor), "| demanda:", red.nodos[mayor]["demanda"])
    print("Componentes conexas:", len(comps_c), "| puentes:", len(puentes_c))

    print()
    print("=== 4. PROGRAMACION DINAMICA: REFUERZO CON PRESUPUESTO ===")
    quitar_d = diseno_minimo()
    print("Diseno minimo: se quitan", len(quitar_d), "enlaces (queda el mas corto de cada union)")
    presupuesto = 1500
    res = refuerzo_dp(grafo, fuente, presupuesto, quitar_aristas=quitar_d)
    print("Puentes sin respaldo:", len(res["puentes"]), "| con refuerzo posible:", len(res["candidatos"]))
    print("Presupuesto:", presupuesto, "m | enlaces a reconstruir:", len(res["elegidos"]),
          "| costo:", round(res["costo"]), "m")
    print("Criticidad cubierta:", round(res["protegido"]), "de", round(res["riesgo_total"]), "kW (" +
          str(round(100 * res["protegido"] / res["riesgo_total"], 1)) + "%)")
    print("Puentes que quedan al reconstruirlos:", res["puentes_despues"], "de", len(res["puentes"]))
    # comprobacion con fuerza bruta sobre los 12 candidatos de mayor criticidad
    mejores = sorted(res["candidatos"], key=lambda c: c["riesgo"], reverse=True)[:12]
    cs = [c["costo"] for c in mejores]
    vs = [c["riesgo"] for c in mejores]
    tabla12, pesos12 = mochila_tabla(cs, vs)
    dp12 = tabla12[-1][min(presupuesto // UNIDAD_M, len(tabla12[0]) - 1)]
    fb12 = mochila_fuerza_bruta(cs, vs, presupuesto)
    print("Comprobacion con fuerza bruta (12 candidatos, 2^12 subconjuntos): DP =", round(dp12, 1),
          "| fuerza bruta =", round(fb12, 1), "| coinciden:", abs(dp12 - fb12) < 1e-6)

    print()
    print("=== 5. DP EN GRAFOS: RUTAS EFICIENTES ===")
    dist_bf, padre_bf, rondas = bellman_ford(grafo, fuente)
    lejano = max(dist_bf, key=lambda u: dist_bf[u])
    ruta = camino_minimo(padre_bf, dist_bf, lejano)
    print("Bellman-Ford desde", nombre(fuente), ":", rondas, "rondas")
    print("Subestacion mas lejana:", nombre(lejano), "| ruta minima:", round(dist_bf[lejano]), "m en",
          len(ruta) - 1, "saltos")
    nivel_bfs, padre_bfs, _ = bfs(grafo, fuente)
    ruta_bfs = camino_minimo(padre_bfs, {u: 0 for u in padre_bfs}, lejano)
    print("Ruta con menos saltos (BFS):", len(ruta_bfs) - 1, "saltos,", round(largo_camino(grafo, ruta_bfs)),
          "m de cable")
    d_zonas, centros, zona_de = grafo_de_zonas()
    dist_z, sig_z = floyd_warshall(d_zonas)
    central, excentricidad, diametro, inalc = resumen_zonas(dist_z)
    print("Floyd-Warshall entre", len(d_zonas), "zonas | zona central:", central + 1, "(ruta mas larga:",
          round(excentricidad[central]), "m) | diametro:", round(diametro[2]), "m entre las zonas",
          diametro[0] + 1, "y", diametro[1] + 1)

    print()
    print("=== FIGURAS ===")
    colores_b = [0] * n
    for k in range(len(comps_b)):
        for u in comps_b[k]:
            colores_b[u] = k
    figura("fig5_conectividad.png", "Conectividad tras fallar los 3 enlaces principales (BFS)",
           colores_b, "coolwarm", principales, quitar_aristas=quitar_b)

    colores_nivel = [0] * n
    for u in nivel:
        colores_nivel[u] = nivel[u]
    figura("fig6_distribucion.png", "Nivel de distribucion desde " + nombre(fuente),
           colores_nivel, "viridis")

    colores_scc = [0] * n
    for k in range(len(scc_a)):
        for u in scc_a[k]:
            colores_scc[u] = k
    figura("fig7_scc.png", "SCC tras fallar 2 enlaces (en rojo: sin respaldo)",
           colores_scc, "coolwarm", puentes_a, quitar_aristas=quitar_a)


if __name__ == "__main__":
    main()