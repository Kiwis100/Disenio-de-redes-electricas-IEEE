import math
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

# 1. CARGA DE MUESTRA REAL DESDE SED_1500_CHIMBOTE.csv
df = pd.read_csv('SED_1500_CHIMBOTE.csv')

# Subestaciones seleccionadas: E343490 (S1), E343496 (S2), E343515 (S3)
indices_elegidos = [0, 2, 6] 
sub = df.iloc[indices_elegidos].copy().reset_index(drop=True)

nodos_data = {}
for idx, row in sub.iterrows():
    clave = f"S{idx+1}"
    nodos_data[clave] = {
        'etiqueta': row['ETIQUETA'],
        'cod': int(row['COD']),
        'pos': (float(row['X']), float(row['Y'])),
        'demanda': float(row['MAX_DEM_SP']),
        'potencia': float(row['POT_INST'])
    }

# 2. LÍMITES DE RESTRICCIÓN (CRITERIOS DE PODA MULTICRITERIO)
DISTANCIA_MAX = 4000.0        # Criterio 1: Geográfico (Distancia máxima en metros)
POTENCIA_MAX_SECTOR = 350.0   # Criterio 2: Potencia Máxima por sector (kW)
DEMANDA_MAX_SECTOR = 70.0     # Criterio 3: Demanda Máxima de Servicio por sector (kW)

def dist_m(p1, p2):
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

# 3. FUNCIÓN DE VALIDACIÓN DE RESTRICCIONES
def es_valido_sector(asig_parcial):
    sectores = {0: [], 1: [], 2: []}
    for i, s in enumerate(asig_parcial):
        sectores[s].append(f'S{i+1}')
        
    for sec, lista_nodos in sectores.items():
        if not lista_nodos:
            continue
            
        p_tot = sum(nodos_data[n]['potencia'] for n in lista_nodos)
        q_tot = sum(nodos_data[n]['demanda'] for n in lista_nodos)
        
        # Criterio A: Poda por Demanda Máxima
        if q_tot > DEMANDA_MAX_SECTOR:
            return False, f"Poda Demanda\nSec {sec}: {q_tot:.1f}kW > {int(DEMANDA_MAX_SECTOR)}kW"
            
        # Criterio B: Poda por Potencia Máxima Instalada
        if p_tot > POTENCIA_MAX_SECTOR:
            return False, f"Poda Potencia\nSec {sec}: {p_tot:.1f}kW > {int(POTENCIA_MAX_SECTOR)}kW"

        # Criterio C: Poda por Dispersión Geográfica
        if len(lista_nodos) > 1:
            for a in range(len(lista_nodos)):
                for b in range(a + 1, len(lista_nodos)):
                    n1, n2 = lista_nodos[a], lista_nodos[b]
                    d = dist_m(nodos_data[n1]['pos'], nodos_data[n2]['pos'])
                    if d > DISTANCIA_MAX:
                        return False, f"Poda Geográfica\nDist({n1},{n2}): {d/1000:.1f}km > {DISTANCIA_MAX/1000:.1f}km"
                        
    return True, "VÁLIDO"

# 4. CONSTRUCCIÓN DEL ÁRBOL BACKTRACKING CON DISTRIBUCIÓN VERTICAL
G = nx.DiGraph()
pos_vert = {}
labels = {}
node_colors = {}

root = "Inicio"
G.add_node(root)
labels[root] = "Inicio"
node_colors[root] = "#2F4F4F"

def backtrack_arbol_vert(asig, nivel, parent_id, y_min, y_max):
    if nivel == 3:
        return
        
    paso_y = (y_max - y_min) / 3.0
    for s in range(3):
        nueva_asig = asig + [s]
        node_id = f"N{nivel+1}_" + "_".join(map(str, nueva_asig))
        
        valido, motivo = es_valido_sector(nueva_asig)
        
        x_pos = (nivel + 1) * 5.0
        y_pos = y_min + paso_y * s + paso_y / 2.0
        pos_vert[node_id] = (x_pos, y_pos)
        G.add_edge(parent_id, node_id)
        
        if not valido:
            labels[node_id] = f"S{nivel+1}: {nueva_asig}\n[{motivo}]"
            node_colors[node_id] = "#FF6B6B" # Rojo: Poda
        else:
            if nivel < 2:
                labels[node_id] = f"S{nivel+1}: {nueva_asig}"
                node_colors[node_id] = "#3399FF" # Azul: Estado Intermedio
                backtrack_arbol_vert(nueva_asig, nivel + 1, node_id, y_min + paso_y * s, y_min + paso_y * (s + 1))
            else:
                labels[node_id] = f"S{nivel+1}: {nueva_asig}\n[VÁLIDO]"
                node_colors[node_id] = "#2ECC71" # Verde: Configuración Válida

pos_vert[root] = (0, 15)
backtrack_arbol_vert([], 0, root, 0, 30)

# 5. DIBUJO DE LA GRÁFICA EN ALTA RESOLUCIÓN (300 DPI)
fig, ax = plt.subplots(figsize=(22, 26))
nx.draw_networkx_edges(G, pos_vert, ax=ax, edge_color='#555555', width=1.8, alpha=0.8)

for node in G.nodes():
    x, y = pos_vert[node]
    color = node_colors[node]
    text = labels[node]
    
    ax.text(x, y, text, fontsize=8.5, weight='bold', ha='center', va='center',
            color='white' if color in ["#2F4F4F", "#FF6B6B"] else '#000000',
            bbox=dict(boxstyle="round,pad=0.5", fc=color, ec="black", lw=1.2, alpha=0.98))

title_text = (
    "Árbol de Espacio de Estados - Backtracking con Datos Reales (Chimbote - SED 1500)\n"
    f"Subestaciones Evaluadas: S1 ({nodos_data['S1']['etiqueta']}), S2 ({nodos_data['S2']['etiqueta']}), S3 ({nodos_data['S3']['etiqueta']})\n"
    f"Criterios Evaluados: Poda Geográfica (Dist > {DISTANCIA_MAX/1000:.1f} km) | "
    f"Poda Potencia (P > {POTENCIA_MAX_SECTOR} kW) | Poda Demanda (D > {DEMANDA_MAX_SECTOR} kW)"
)

ax.set_title(title_text, fontsize=14, weight='bold', pad=25)
ax.axis('off')
plt.tight_layout()
plt.savefig('arbol_backtracking_chimbote_completo.png', dpi=300)
plt.show()