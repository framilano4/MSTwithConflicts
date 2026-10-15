"""
FORMATO ISTANZA (testo):
    V E K
    s
    i j w          (E righe: edge {i,j} con costo w)
    i1 j1 i2 j2    (K righe: l'edge {i1,j1} e' in conflitto con l'edge {i2,j2})

I conflitti si specificano con le coppie di NODI degli archi coinvolti.

Uso:
inserire come input il nome del file contenente l'istanza (istanza.txt)
facendo attenzione a inserire file e modello py nella stessa cartella.
"""

from mip import Model, xsum, GUROBI, MINIMIZE, INTEGER, BINARY, OptimizationStatus
import os
import time


def leggi_istanza(path):
    with open(path) as f:
        righe = [r.strip() for r in f if r.strip() and not r.strip().startswith("#")]

    V, E, K = map(int, righe[0].split())
    s = int(righe[1])

    archi = []
    for r in righe[2:2 + E]:
        i, j, w = r.split()
        archi.append((int(i), int(j), float(w)))

    # dizionario per risalire all'indice di un edge a partire dai suoi nodi
    # (la coppia viene ordinata per non dipendere dal verso i-j oppure j-i)
    indice_edge = {tuple(sorted((i, j))): e for e, (i, j, w) in enumerate(archi)}

    # tutte le righe restanti dopo gli archi sono conflitti: non ci si basa sul
    # valore K dichiarato in testa al file (potrebbe essere soggetto a errori di distrazione),
    # ma in base al numero di righe di conflitti.
    righe_conflitti = righe[2 + E:]
    if len(righe_conflitti) != K:
        print(f"Attenzione: il file dichiara K={K} conflitti ma ne contiene {len(righe_conflitti)}; "
              f"vengono comunque letti tutti quelli presenti.")

    conflitti = []
    for r in righe_conflitti:
        i1, j1, i2, j2 = map(int, r.split())
        chiave1 = tuple(sorted((i1, j1)))
        chiave2 = tuple(sorted((i2, j2)))
        if chiave1 not in indice_edge:
            raise ValueError(f"L'edge {{{i1},{j1}}} indicato nei conflitti non esiste tra gli archi dell'istanza")
        if chiave2 not in indice_edge:
            raise ValueError(f"L'edge {{{i2},{j2}}} indicato nei conflitti non esiste tra gli archi dell'istanza")
        conflitti.append((indice_edge[chiave1], indice_edge[chiave2]))

    return V, s, archi, conflitti


def main():
    nome_file = input("Nome del file di istanza (deve trovarsi nella stessa cartella dello script): ")

    cartella_script = os.path.dirname(os.path.abspath(__file__))
    percorso_file = os.path.join(cartella_script, nome_file)

    V, s, archi, conflitti = leggi_istanza(percorso_file)
    E = len(archi)

    m = Model(sense=MINIMIZE, solver_name= GUROBI)

    # variabili y_ij: binarie, valgono 1 se l'edge e' nello spanning tree, altrimenti 0(vincolo 7)
    y = [m.add_var(var_type=BINARY, name=f"y_{i}_{j}") for i, j, w in archi]

    # variabili x_ij, x_ji per ciascun arco orientato (vincolo 6: x >= 0, dato da lb=0 default)
    x_ij = [m.add_var(var_type=INTEGER, lb=0, name=f"x_{i}_{j}") for i, j, w in archi]
    x_ji = [m.add_var(var_type=INTEGER, lb=0, name=f"x_{j}_{i}") for i, j, w in archi]

    # funzione obiettivo (1)
    m.objective = xsum(archi[e][2] * y[e] for e in range(E))

    # vincoli di conservazione del flusso (2)
    for nodo in range(V):
        entra = xsum(x_ji[e] for e, (i, j, w) in enumerate(archi) if i == nodo) + \
                xsum(x_ij[e] for e, (i, j, w) in enumerate(archi) if j == nodo)
        esce = xsum(x_ij[e] for e, (i, j, w) in enumerate(archi) if i == nodo) + \
               xsum(x_ji[e] for e, (i, j, w) in enumerate(archi) if j == nodo)
        rhs = -(V - 1) if nodo == s else 1
        m += entra - esce == rhs

    # vincoli di capacita' (3) e (4)
    for e in range(E):
        m += x_ij[e] <= (V - 1) * y[e]
        m += x_ji[e] <= (V - 1) * y[e]

    # vincoli di conflitto (5)
    for e1, e2 in conflitti:
        m += y[e1] + y[e2] <= 1

    inizio = time.time()
    status = m.optimize(max_seconds=300)
    tempo_calcolo = time.time() - inizio

    if status == OptimizationStatus.OPTIMAL:
        stato_soluzione = "ottima"
    elif status == OptimizationStatus.FEASIBLE:
        stato_soluzione = "ammissibile"
    else:
        stato_soluzione = str(status)

    valore_obiettivo = m.objective_value
    best_bound = m.objective_bound

    nome_istanza = os.path.splitext(nome_file)[0]
    nome_output = os.path.join(cartella_script, f"risultato_{nome_istanza}.txt")

    with open(nome_output, "w") as f:
        f.write(f"nome_istanza: {nome_istanza}\n")
        f.write(f"valore_funzione_obiettivo: {valore_obiettivo}\n")
        f.write(f"stato_soluzione: {stato_soluzione}\n")
        f.write(f"tempo_di_calcolo: {tempo_calcolo:.4f} s\n")
        f.write(f"best_bound: {best_bound}\n")

    print(f"Risultati scritti in: {nome_output}")


if __name__ == "__main__":
    main()