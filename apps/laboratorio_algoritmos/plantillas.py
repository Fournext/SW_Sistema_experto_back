"""
Plantillas canónicas de algoritmos de inferencia (Sistemas Expertos - FWC / BWC).
Basadas exactamente en el material de clases (Sistemas Expertos.pdf) y los ejercicios del Práctico 1.
"""

PLANTILLAS_ALGORITMOS = [
    {
        "id": "fwc-secuencial-clasico",
        "titulo": "1. FWC Secuencial Clásico (Sin Metas)",
        "descripcion": "Algoritmo canónico enseñado en clase: dividido en FWCPasada y FWC. La condición de parada comprueba si la Base de Hechos creció en cada ciclo.",
        "codigo": """// Procedimiento para una pasada de inferencia sobre el conjunto de reglas R
void FWCPasada(Regla[] R, BaseHechos BH) {
    for (int i = 0; i < R.length; i++) {
        if (!marcada(R[i])) {
            Hecho C = Disparar(R[i], BH);
            if (C != null) {
                BH.add(C);
                Marcar(R[i]);
            }
        }
    }
}

// Algoritmo principal de Encadenamiento hacia Adelante (FWC)
void FWC(Regla[] R, BaseHechos BH) {
    DesmarcarReglas(R);
    int pasada = 0;
    while (true) {
        pasada++;
        RegistrarPasada(pasada);
        int cantidadAntes = BH.length();
        FWCPasada(R, BH);
        // Condición de parada canónica: si BH no creció en esta pasada, termina
        if (cantidadAntes == BH.length()) {
            break;
        }
    }
    MostrarLosHechosDisparados(BH);
}
"""
    },
    {
        "id": "fwc-una-meta",
        "titulo": "2. FWC con 1 Meta Específica",
        "descripcion": "Encadenamiento hacia adelante con condición de parada anticipada: se detiene apenas la Meta ingresa a BH o no se generen nuevos hechos.",
        "codigo": """void FWCPasada(Regla[] R, BaseHechos BH) {
    for (int i = 0; i < R.length; i++) {
        if (!marcada(R[i])) {
            Hecho C = Disparar(R[i], BH);
            if (C != null) {
                BH.add(C);
                Marcar(R[i]);
            }
        }
    }
}

// FWC con condición de parada anticipada al alcanzar la Meta
void FWC(Regla[] R, BaseHechos BH, Variable meta) {
    DesmarcarReglas(R);
    int pasada = 0;
    while (!BH.contains(meta)) {
        pasada++;
        RegistrarPasada(pasada);
        int cantidadAntes = BH.length();
        FWCPasada(R, BH);
        if (cantidadAntes == BH.length()) {
            break;
        }
    }
    if (BH.contains(meta)) {
        MostrarMeta(meta, BH);
    } else {
        Mostrar("La meta no pudo ser alcanzada.");
    }
}
"""
    },
    {
        "id": "fwc-k-metas",
        "titulo": "3. FWC con Lista de K Metas",
        "descripcion": "Encadenamiento hacia adelante con un conjunto de metas a satisfacer. Se detiene cuando TodasUnificadas sea verdadero o no haya más disparos.",
        "codigo": """void FWCPasada(Regla[] R, BaseHechos BH) {
    for (int i = 0; i < R.length; i++) {
        if (!marcada(R[i])) {
            Hecho C = Disparar(R[i], BH);
            if (C != null) {
                BH.add(C);
                Marcar(R[i]);
            }
        }
    }
}

// FWC con conjunto de metas a satisfacer
void FWC(Regla[] R, BaseHechos BH, Lista<Variable> metas) {
    DesmarcarReglas(R);
    int pasada = 0;
    while (!TodasUnificadas(BH, metas)) {
        pasada++;
        RegistrarPasada(pasada);
        int cantidadAntes = BH.length();
        FWCPasada(R, BH);
        if (cantidadAntes == BH.length()) {
            break;
        }
    }
    MostrarLosHechosDisparados(BH);
}
"""
    },
    {
        "id": "ejercicio-7-consulta-previa",
        "titulo": "4. Ejercicio 7: Consulta Previa a Primera Regla No Marcada",
        "descripcion": "Antes de la pasada, toma la primera regla libre y consulta la variable nativa de su premisa sin repetir consultas.",
        "codigo": """void FWCPasada(Regla[] R, BaseHechos BH) {
    for (int i = 0; i < R.length; i++) {
        if (!marcada(R[i])) {
            Hecho C = Disparar(R[i], BH);
            if (C != null) {
                BH.add(C);
                Marcar(R[i]);
            }
        }
    }
}

// Ejercicio 7: Consulta previa a la primera regla no marcada
void FWC(Regla[] R, BaseHechos BH) {
    DesmarcarReglas(R);
    int pasada = 0;
    while (true) {
        pasada++;
        RegistrarPasada(pasada);
        
        // Buscar la primera regla no marcada para consultar su premisa
        for (int k = 0; k < R.length; k++) {
            if (!marcada(R[k])) {
                Variable[] varsPremisa = VariablesPremisa(R[k]);
                if (varsPremisa.length > 0) {
                    Variable v = varsPremisa[0];
                    if (!Consultada(v) && !BH.contains(v)) {
                        Hecho resp = Preguntar("¿Cuál es el valor de " + v.nombre + "?", v);
                        if (resp != null) {
                            BH.add(resp);
                        }
                    }
                }
                break;
            }
        }
        
        int cantidadAntes = BH.length();
        FWCPasada(R, BH);
        if (cantidadAntes == BH.length()) {
            break;
        }
    }
    MostrarLosHechosDisparados(BH);
}
"""
    },
    {
        "id": "ejercicio-8-pila-hn",
        "titulo": "5. Ejercicio 8: Extracción de Hechos Nativos desde Pila HN",
        "descripcion": "En cada ciclo, extrae un Hecho Nativo de la pila HN, lo consulta al usuario y luego ejecuta la pasada de inferencia.",
        "codigo": """void FWCPasada(Regla[] R, BaseHechos BH) {
    for (int i = 0; i < R.length; i++) {
        if (!marcada(R[i])) {
            Hecho C = Disparar(R[i], BH);
            if (C != null) {
                BH.add(C);
                Marcar(R[i]);
            }
        }
    }
}

// Ejercicio 8: Extracción de Hecho Nativo de la pila HN antes de cada pasada
void FWC(Regla[] R, BaseHechos BH, Pila<Variable> HN) {
    DesmarcarReglas(R);
    int pasada = 0;
    while (true) {
        pasada++;
        RegistrarPasada(pasada);
        
        // Antes de la pasada, extraer un hecho nativo y consultar al usuario
        if (!HN.vacia()) {
            Variable v = HN.pop();
            if (!Consultada(v)) {
                Hecho resp = Preguntar("¿Cuál es el valor de " + v.nombre + "?", v);
                if (resp != null) {
                    BH.add(resp);
                }
            }
        }
        
        int cantidadAntes = BH.length();
        FWCPasada(R, BH);
        if (cantidadAntes == BH.length() && HN.vacia()) {
            break;
        }
    }
    MostrarLosHechosDisparados(BH);
}
"""
    },
    {
        "id": "ejercicio-13-cola-q",
        "titulo": "6. Ejercicio 13: Recorrido con Cola FIFO de Reglas (Q)",
        "descripcion": "Control de inferencia con Cola FIFO Q. Las reglas que no disparan se vuelven a encolar al final si pueden disparar más adelante.",
        "codigo": """// Ejercicio 13: Algoritmo FWC con Cola FIFO Q de Reglas
void FWC(Cola<Regla> Q, BaseHechos BH) {
    int reglasSinDisparo = 0;
    int pasada = 1;
    RegistrarPasada(pasada);
    
    while (!Q.vacia() && reglasSinDisparo < Q.length()) {
        Regla r = Q.pop();
        if (!marcada(r)) {
            Hecho C = Disparar(r, BH);
            if (C != null) {
                BH.add(C);
                Marcar(r);
                reglasSinDisparo = 0;
            } else {
                // Si la regla no disparó, se reencola al final de Q
                Q.meter(r);
                reglasSinDisparo++;
            }
        }
    }
    MostrarLosHechosDisparados(BH);
}
"""
    }
]
