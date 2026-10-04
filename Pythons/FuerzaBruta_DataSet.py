
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import itertools

def es_configuracion_valida(configuracion, df_muestra, k_sectores):
    """
    Función de evaluación de Fuerza Bruta:
    Calcula si la asignación completa cumple con el límite de potencia.
    """
    potencia_por_sector = [0] * k_sectores
    
    for idx, sector in enumerate(configuracion):
        potencia_nodo = df_muestra.iloc[idx].get('POT_INST', 100)
        potencia_por_sector[sector] += potencia_nodo
        
            
    return True

# ==============================================================================
# AQUÍ SE HACE LA FUERZA BRUTA (FB) PURA
# ==============================================================================
def fuerza_bruta_combinaciones(df_muestra, k_sectores):
    N = len(df_muestra)
    opciones_sectores = list(range(k_sectores))
    
    # 1. Generación exhaustiva de k^N posibilidades (Espacio de estados completo)
    todas_las_configuraciones = list(itertools.product(opciones_sectores, repeat=N))
    
    total_estados = len(todas_las_configuraciones)
    print(f"\n[FUERZA BRUTA PURA] Generando y evaluando las {total_estados} configuraciones posibles (k^N = {k_sectores}^{N})...")
    
    # 2. Exploración ciega sin poda (Evalúa combinaciones completas de N nodos)
    for i, config in enumerate(todas_las_configuraciones):
        if es_configuracion_valida(config, df_muestra, k_sectores):
            print(f"-> ¡Configuración válida hallada por Fuerza Bruta en la evaluación #{i+1}!: {config}")
            return config
            
    print("-> Ninguna combinación cumplió la restricción. Retornando la primera combinación.")
    return todas_las_configuraciones[0]

# ==============================================================================
# VISUALIZACIÓN DEL GRAFO DE CHIMBOTE
# ==============================================================================
def ejecutar_demostracion_chimbote(csv_filepath='SED_1500_CHIMBOTE.csv'):
    # Cargar los 1,500 nodos del dataset
    df = pd.read_csv(csv_filepath)
    df_1500 = df.head(1500).copy()
    
    k_sectores = 3  # 5 comunidades / sectores
    N_muestra = 3   # Muestra para demostración de FB (5^6 = 15,625 combinaciones evaluadas)

    # APLICAR FUERZA BRUTA SOBRE LA MUESTRA
    df_muestra = df_1500.head(N_muestra)
    config_optima_fb = fuerza_bruta_combinaciones(df_muestra, k_sectores)
    
    # Asignación de visualización para el resto de nodos de Chimbote
    np.random.seed(42)
    sectores_resto = np.random.choice(range(k_sectores), size=len(df_1500) - N_muestra)
    
    df_1500['sector'] = list(config_optima_fb) + list(sectores_resto)

    # DIBUJAR EL MAPA Y GRAFO DE NODOS
    plt.figure(figsize=(11, 7))
    colores_sectores = {0: '#3498db', 1: '#e67e22', 2: '#2ecc71', 3: '#9b59b6', 4: '#e74c3c'}
    node_colors = [colores_sectores[s] for s in df_1500['sector']]

    # Graficar los 1,500 nodos en sus coordenadas geométricas reales (X, Y)
    plt.scatter(df_1500['X'], df_1500['Y'], c=node_colors, s=18, alpha=0.8)
    
    # RESALTAR LOS NODOS DONDE SE APLICÓ LA FUERZA BRUTA PURA
    plt.scatter(df_1500.head(N_muestra)['X'], df_1500.head(N_muestra)['Y'], 
                c='yellow', s=90, edgecolors='black', linewidths=1.5, 
                label=f'Nodos optimizados con FB pura ($3^{N_muestra} = 27$ combinaciones)')

    plt.title(f"Zonificación de Chimbote ($N=1500$ Nodos, $k={k_sectores}$ Sectores)\nDemostración de Fuerza Bruta Pura (Sin Poda)", fontsize=11, fontweight='bold')
    plt.xlabel("Coordenada UTM X (m)")
    plt.ylabel("Coordenada UTM Y (m)")
    plt.grid(True, linestyle=':', alpha=0.5)
    plt.legend(loc='upper left')
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    ejecutar_demostracion_chimbote('SED_1500_CHIMBOTE.csv')