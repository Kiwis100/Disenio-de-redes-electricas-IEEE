# -*- coding: utf-8 -*-
"""
Created on Sun Oct  4 04:20:28 2026

@author: manue
"""

import matplotlib.pyplot as plt
import networkx as nx
import itertools

def graficar_arbol_fuerza_bruta_espaciado(N=3, k=3):
    """
    Grafica el árbol de decisión de Fuerza Bruta pura con mayor espaciado horizontal
    y vertical entre nodos, y etiquetas en texto negro legible.
    """
    G = nx.DiGraph()
    G.add_node("Inicio", level=0)
    
    opciones = list(range(k))
    
    # Construir el árbol de decisión nivel por nivel
    for nivel in range(1, N + 1):
        combinaciones_nivel = list(itertools.product(opciones, repeat=nivel))
        
        for config in combinaciones_nivel:
            nodo_actual = f"S{nivel}: {list(config)}"
            
            if nivel == 1:
                padre = "Inicio"
            else:
                padre = f"S{nivel-1}: {list(config[:-1])}"
                
            G.add_edge(padre, nodo_actual)

    # Posicionamiento con mayor espaciado
    pos = {}
    niveles = {i: [] for i in range(N + 1)}
    
    for nodo in G.nodes():
        if nodo == "Inicio":
            niveles[0].append(nodo)
        else:
            nivel_nodo = int(nodo.split(":")[0].replace("S", ""))
            niveles[nivel_nodo].append(nodo)

    # Ajuste de coordenadas (X, Y) con mayor holgura
    pos["Inicio"] = (0, 0)
    ancho_base = 26.0  # Espacio horizontal
    
    for lvl in range(1, N + 1):
        nodos_lvl = niveles[lvl]
        total_nodos = len(nodos_lvl)
        
        for i, nodo in enumerate(nodos_lvl):
            x = -ancho_base / 2 + (i + 0.5) * (ancho_base / total_nodos)
            y = -lvl * 2.8  # Espacio vertical entre niveles
            pos[nodo] = (x, y)

    # Lienzo amplio
    plt.figure(figsize=(18, 9))
    
    # Dibujar las ramas/aristas
    nx.draw_networkx_edges(G, pos, edge_color='#bdc3c7', arrows=True, arrowsize=12, width=1.2)
    
    # Clasificación de nodos
    hojas = [n for n in G.nodes() if G.out_degree(n) == 0]
    nodos_intermedios = [n for n in G.nodes() if n not in hojas and n != "Inicio"]
    
    # Dibujar los nodos (círculos)
    nx.draw_networkx_nodes(G, pos, nodelist=["Inicio"], node_color='#34495e', node_size=1100)
    nx.draw_networkx_nodes(G, pos, nodelist=nodos_intermedios, node_color='#3498db', node_size=750)
    nx.draw_networkx_nodes(G, pos, nodelist=hojas, node_color='#2ecc71', node_size=750)

    # ETIQUETAS EN TEXTO NEGRO LEGIBLE (font_color='black')
    labels = {n: n for n in G.nodes()}
    nx.draw_networkx_labels(
        G, 
        pos, 
        labels=labels, 
        font_size=7, 
        font_weight='bold', 
        font_color='black'  # Texto negro para máximo contraste
    )

    plt.title(f"Árbol de Espacio de Estados - Fuerza Bruta Pura (Vista Espaciada)\n"
              f"$N = {N}$ Subestaciones, $k = {k}$ Sectores ($k^N = {k**N}$ Hojas)", 
              fontsize=12, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    graficar_arbol_fuerza_bruta_espaciado(N=3, k=3)