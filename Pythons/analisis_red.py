# ANALISIS DE LA RED ELECTRICA DE CHIMBOTE
#   - BFS/DFS: analisis de conectividad
#   - Ordenamiento topologico: distribucion de energia
#   - SCC: detectar redundancias
#
#
# Para simular fallos, todas las funciones reciben:
#   quitar_nodos:   conjunto de nodos que fallan
#   quitar_aristas: conjunto de aristas que fallan, guardadas como clave(a, b)

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


def scc_kosaraju(dirigido):
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
    return componentes


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