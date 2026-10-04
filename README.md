# Diseño de redes eléctricas (IEEE) - Caso 8

Proyecto de Complejidad Algorítmica. Modela las subestaciones de distribución de Chimbote como un grafo y analiza su conectividad, la distribución de energía y sus redundancias, con una interfaz gráfica para simular fallas.

## Dataset
`Pythons/SED_1500_CHIMBOTE.csv`: 1500 subestaciones del sistema SE0119 (Chimbote) con coordenadas UTM, tensión, demanda y potencia instalada. Fuente: [completar con la fuente y la fecha de corte].

## Técnicas implementadas

| Técnica | Archivo | Uso |
|---|---|---|
| Grafos | `red_electrica_chimbote.py` | Subestación = nodo, arista = distancia en metros |
| Divide y vencerás | `red_electrica_chimbote.py` | Divide la región geográfica en zonas y las une con enlaces de frontera |
| BFS/DFS | `analisis_red.py` | Conectividad y componentes, también simulando fallas |
| Ordenamiento topológico (Kahn) | `analisis_red.py` | Orden de distribución de energía desde una subestación fuente |
| SCC (Kosaraju) | `analisis_red.py` | Detecta conexiones sin respaldo (redundancia) |
| Fuerza bruta y backtracking | *en desarrollo* | |

## Archivos
- `Pythons/red_electrica_chimbote.py`: lee el CSV y construye el grafo.
- `Pythons/analisis_red.py`: BFS/DFS, orden topológico y SCC. Al ejecutarlo imprime resultados y genera las figuras
- `Pythons/interfaz_red.py`: interfaz gráfica (Tkinter).

## Cómo ejecutar
Requiere Python 3 y matplotlib:

```
pip install matplotlib
cd Pythons
python interfaz_red.py
```

Otros comandos: `python analisis_red.py` (resultados y figuras) y `python red_electrica_chimbote.py` (grafo completo).

## Uso de la interfaz
1. Elegir una vista: grafo completo, regiones, conectividad, distribución o redundancia.
2. Probar los escenarios rápidos (A, B, C) o hacer fallar enlaces y subestaciones manualmente.
3. Los resultados aparecen debajo del gráfico. Con **Guardar imagen** se exporta la vista actual.

## Integrantes
- Sheila Jasmin Angeles Rojas - U20231d400
- Sebastián William Ruiz Cruz - U20221A486
- Mathias Augusto Aréchaga Saavedra - U202320699

