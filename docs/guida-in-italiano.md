# Guida in italiano: capire il progetto e il lavoro fatto

Questa guida spiega, con parole semplici, tutto quello che c'è nel repository e
cosa abbiamo fatto nelle ultime fasi. I documenti tecnici in inglese
(`benchmark/README.md`, `benchmark/EXPERIMENT_swing_detector.md`) contengono i
dettagli; qui trovi il "perché" e il "cosa significa".

## 1. Il progetto in una frase

Dato un video di una partita di tennis, il programma trova i giocatori, la palla
e le linee del campo, e produce un video annotato più un file CSV con
statistiche (numero di colpi, velocità stimate).

Il pezzo su cui abbiamo lavorato di più è: **riconoscere quando un giocatore
colpisce la palla** (un "evento" o "colpo"). Tutte le statistiche dipendono da
questo.

## 2. Come si misura se un riconoscitore funziona

Per dire "funziona bene" serve un confronto con la verità. Tu hai guardato i
video e annotato a mano i fotogrammi dove avviene ogni colpo: questa è la
**verità di riferimento** (in inglese *ground truth*), 54 colpi in totale.

Il programma produce la sua lista di colpi. Si confrontano le due liste: un colpo
del programma conta come giusto se cade entro **0,25 secondi** da uno vero
(la *tolleranza*). Ogni colpo vero può essere associato a una sola previsione.

Ne escono tre numeri:

- **Vero positivo (TP):** il programma ha detto "colpo" e c'era davvero.
- **Falso positivo (FP):** ha detto "colpo" ma non c'era (un allarme sbagliato).
- **Falso negativo (FN):** c'era un colpo ma il programma non l'ha visto.

Da questi si calcolano tre percentuali (da 0 a 1, più alto è meglio):

| Nome | In parole | Formula |
| --- | --- | --- |
| **Precision** (precisione) | Quando dice "colpo", quante volte ha ragione? | TP / (TP + FP) |
| **Recall** (richiamo) | Dei colpi veri, quanti ne trova? | TP / (TP + FN) |
| **F1** | Un voto unico che combina le due | 2·TP / (2·TP + FP + FN) |

**Esempio con i tuoi dati.** Sulla clip Australian Open il metodo `swing_v1`
ha TP = 35, FP = 7, FN = 4. Quindi precision = 35/42 = 0,83 (quando parla ha
ragione 8 volte su 10), recall = 35/39 = 0,90 (trova 9 colpi su 10), F1 = 0,86.

**Errore di timing:** per i colpi trovati si misura anche di quanti secondi
sbaglia l'istante. Un errore di 0,05 s è circa un fotogramma e mezzo.

## 3. Il problema dei "pochi dati" e come lo abbiamo trattato

Hai solo due clip e 54 colpi. Con così pochi dati, un risultato come "F1 =
0,79" può dipendere dalla fortuna. Per questo abbiamo aggiunto due strumenti.

### Intervallo di confidenza (bootstrap)

Idea: se rifacessi l'esperimento con altri dati simili, di quanto cambierebbe il
risultato? Lo si stima al computer: si prendono i dati che hai, si
**ricampionano a caso** (pescando pezzi con reinserimento) 10.000 volte e si
ricalcola il voto ogni volta. Si ottiene un intervallo, per esempio
**"F1 = 0,83, tra 0,71 e 0,92"**. Se l'intervallo è stretto, il risultato è
solido; se è largo, i dati sono pochi.

- Non si ricampionano i singoli colpi ma **blocchi di 10 secondi**, perché i colpi
  di uno stesso scambio non sono indipendenti tra loro.
- **Confronto "paired" (appaiato):** per sapere se un metodo batte un altro, si
  confrontano sugli stessi blocchi ricampionati. Se l'intervallo della
  *differenza* non contiene lo zero, il miglioramento è probabilmente vero e non
  fortuna. Se contiene lo zero, **non possiamo dirlo con questi dati**.

### Overfitting e dati "mai visti"

I metodi hanno parametri (manopole) da regolare. Se regoli le manopole su una
clip e poi misuri sulla stessa clip, il voto è gonfiato: il metodo ha
"imparato a memoria" quella clip (*overfitting*). Un voto onesto si ottiene su
dati **mai usati per regolare** (*held-out*).

Per questo:

- La clip Wimbledon, che era il tuo "test", l'abbiamo già usata una volta: ora
  la consideriamo dati di sviluppo. Un vero test futuro richiede **clip nuove**.
- Con due clip abbiamo usato la **leave-one-clip-out (LOCO)**: si regolano le
  manopole su una clip e si misura sull'altra, poi si scambia. Così ogni voto
  viene da una clip non usata per regolare.
- **Preregistrazione:** abbiamo scritto il protocollo (quali metodi, quali
  valori delle manopole, come scegliere, cosa conta come successo) e lo abbiamo
  committato **prima** di guardare i risultati. La storia di Git prova l'ordine.
  È un modo per non "ritoccare le regole" dopo aver visto i numeri.

## 4. I due metodi a confronto

### Il vecchio: `persistence` (regola della persistenza)

Guarda se la palla, nell'immagine, cambia direzione verticale (da salire a
scendere o viceversa) e se poi **continua nella nuova direzione per abbastanza
tempo** (0,72 s nella versione migliorata). È una regola con una sola manopola.
Difetto: è sensibile a quella manopola e non sfrutta come funziona il gioco.

### Il nuovo: `swing` (oscillazioni alternate)

Intuizione: in uno scambio ripreso da dietro, la palla va avanti e indietro tra i
due giocatori. Nell'immagine la sua altezza `y` oscilla come un'onda:

```
 y (verso il basso)
   ^        colpo del giocatore vicino
   |       /\            /\
   |      /  \          /  \
   |     /    \        /    \
   |    /      \      /      \
   |   /        \    /        \
   |  /          \  /          \
   | /  colpo     \/   colpo    \
   |    giocatore  lontano       ...
   +----------------------------------> tempo
```

- Ogni **colpo è un picco o una valle** dell'onda.
- I colpi **si alternano** (vicino, lontano, vicino...): quindi picchi e valli
  alternati.
- I **rimbalzi** fanno piccole oscillazioni in mezzo, che non sono colpi.

L'algoritmo (chiamato *ZigZag*) fa tre cose: leviga la traiettoria per togliere
il rumore, poi scorre il tempo e **accetta un'inversione solo se la palla si è
spostata di almeno una certa frazione** dell'altezza tipica (così ignora i
rimbalzi piccoli), e infine segna il colpo nel punto di picco/valle. Il
risultato alterna per costruzione.

Ha due manopole: quanto levigare (`smoothing`, in secondi) e quanto grande deve
essere l'oscillazione (`ratio`, frazione dell'altezza). La soglia è relativa,
quindi non dipende dalla risoluzione del video.

## 5. Cosa abbiamo scoperto (in parole)

1. **Il nuovo metodo sbaglia meno allarmi.** La precisione sale di circa
   **+0,07 / +0,10** e l'intervallo di confidenza esclude lo zero: questo è
   l'unico miglioramento che i dati permettono di affermare.
2. **Il voto F1 sale di circa +0,05, ma non è dimostrato.** L'intervallo include
   lo zero, quindi con due clip non possiamo escludere che sia fortuna.
   Secondo il criterio fissato in anticipo il risultato è **inconcludente**.
3. **È meno "capriccioso".** Con il nuovo metodo il 69% delle combinazioni di
   manopole dà un risultato quasi ottimo su entrambe le clip, contro il 43% del
   vecchio. Significa che funziona anche senza regolazioni delicate, e questo
   conta quando hai pochi dati per regolarlo.
4. **Lo smoothing è la manopola che conta.** Sotto 0,20 s i risultati peggiorano
   molto; da 0,28 s in su sono stabili (un "plateau").
5. **Contro: il timing peggiora.** L'errore sull'istante del colpo passa da circa
   0,05 s a circa 0,10 s, perché levigare "arrotonda" i picchi. Per il conteggio
   dei colpi non è un problema; lo è se servisse l'istante esatto.
6. **Gli errori che restano sono per lo più colpi "spostati".** Un colpo trovato
   0,4 s dopo quello vero conta come un falso positivo *e* un falso negativo.
   Succede dove la palla viene vista poco dal rilevatore (nella clip
   Australian Open solo il 46% dei fotogrammi): il collo di bottiglia ora è il
   **rilevatore della palla**, non la regola dei colpi.

### Una deviazione che abbiamo dichiarato

Nel run preregistrato, entrambe le volte la scelta migliore era sul **bordo**
della griglia di valori (il massimo disponibile). Non l'avevamo previsto. Abbiamo
quindi fatto un secondo run con una griglia più ampia, etichettato
**esplorativo**, e scritto quante configurazioni abbiamo provato (98 in
totale). Riportare le deviazioni è parte dell'onestà del metodo.

### Configurazione congelata: `swing_v1`

Per scegliere i valori finali senza "andare a occhio", abbiamo fissato una regola:
il centro della zona dove il F1 è entro 0,005 dal massimo. Risultato:
`ratio = 0,40`, `smoothing = 0,36 s`. Sono i valori di default nel codice e **non
vanno cambiati** prima del test sulle clip nuove.

## 6. Cosa puoi (e non puoi) dire nel CV

**Puoi dire, e dimostrare:**

- Hai costruito un benchmark annotato a mano e una pipeline di valutazione con
  matching uno-a-uno, intervalli di confidenza (block bootstrap) e confronto
  appaiato.
- Hai progettato un nuovo rilevatore e lo hai confrontato con il precedente con
  un protocollo preregistrato e validazione leave-one-clip-out.
- Il nuovo metodo ha **precisione più alta a parità di recall** ed è **meno
  sensibile ai parametri**, e hai misurato e dichiarato i suoi limiti.
- Il lavoro è riproducibile: rilevazioni salvate in CSV, test di regressione,
  CI.

**Non dire:**

- "Ho migliorato l'F1 del X%": con due clip non è dimostrato.
- "Funziona su qualsiasi partita": hai solo due clip a 25 FPS con lo stesso
  giocatore.
- "Ho sviluppato il sistema da zero": l'origine è un tutorial (è già dichiarato
  nel README, e va bene così).

**Frase d'esempio (italiano):** *"Ho esteso un progetto di analisi video del
tennis con un benchmark annotato a mano e un protocollo di valutazione
rigoroso (intervalli di confidenza bootstrap, validazione leave-one-clip-out,
protocollo preregistrato). Ho progettato un nuovo rilevatore di colpi che aumenta
la precisione di circa 7–10 punti a parità di recall ed è molto meno sensibile
ai parametri, documentando anche i limiti: timing meno accurato e risultati
validi solo su due clip."*

Una frase come questa, che dichiara anche i limiti, convince più di un numero
gonfiato: mostra che capisci cosa significano i risultati.

## 7. Dove si trova cosa

| Cosa | Dove |
| --- | --- |
| Il nuovo rilevatore (`swing`) | `utils/swing_shot_detection.py` |
| Il vecchio rilevatore (`persistence`) | `utils/shot_detection_utils.py` |
| Calcolo di precision/recall/F1 e matching | `benchmark/evaluate_events.py` |
| Intervalli di confidenza (bootstrap) | `benchmark/bootstrap.py` |
| Valutazione su tutte le clip | `benchmark/run_benchmark.py` |
| Esperimento leave-one-clip-out | `benchmark/loco_experiment.py` |
| Protocollo e risultati dettagliati (inglese) | `benchmark/EXPERIMENT_swing_detector.md` |
| Rilevazioni della palla in CSV | `benchmark/detections/` |
| Verità di riferimento (tue annotazioni) | `benchmark/annotations/` |
| Previsioni dei vari metodi | `benchmark/predictions/` |
| Risultati salvati dagli esperimenti | `benchmark/results/` |
| Come aggiungere nuove clip | `benchmark/CLIP_SELECTION.md`, `benchmark/sources.csv` |
| Test automatici | `tests/` |

## 8. Come rifare tutto

Serve Python con `pandas`, `numpy`, `opencv-python-headless`. Dalla cartella del
progetto:

```bash
# confronta i metodi su tutte le clip, con intervalli di confidenza
python -m benchmark.run_benchmark --methods persistence_18 swing_v1

# riesegue l'esperimento leave-one-clip-out preregistrato
python -m benchmark.loco_experiment

# versione esplorativa con griglia più ampia
python -m benchmark.loco_experiment --extended-grid

# test automatici
python -m unittest discover -s tests -v
```

## 9. Prossimi passi, in ordine di importanza

1. **Raccogliere 8–10 clip nuove** (superfici, tornei, giocatori e FPS diversi) e
   annotarle. Senza questo ogni risultato resta indicativo. Il protocollo è in
   `benchmark/CLIP_SELECTION.md`.
2. **Valutare `swing_v1` una sola volta sul nuovo test**, con parametri
   congelati: sarà la prova vera.
3. **Recuperare il timing**: spostare ogni colpo sul punto di inversione più
   netto in una versione poco levigata del segnale.
4. **Migliorare il rilevatore della palla** (oggi vede la palla nel 46–62% dei
   fotogrammi): è l'origine della maggior parte degli errori rimasti.
5. **Aggiungere la posizione dei giocatori** per scartare i colpi "spostati".

## 10. Glossario

| Termine | Significato |
| --- | --- |
| **Ground truth** | La verità di riferimento: i colpi annotati a mano. |
| **Tolleranza** | Quanto può sbagliare l'istante un colpo per contare come giusto (0,25 s). |
| **TP / FP / FN** | Vero positivo, falso positivo, falso negativo. |
| **Precision** | Quando il programma dice "colpo", quante volte ha ragione. |
| **Recall** | Quanti colpi veri il programma riesce a trovare. |
| **F1** | Voto unico che bilancia precision e recall. |
| **Bootstrap** | Ripetere la valutazione su dati ricampionati a caso per stimare l'incertezza. |
| **Intervallo di confidenza (IC)** | Fascia in cui cade probabilmente il valore vero (qui il 95%). |
| **Paired (appaiato)** | Confronto di due metodi sugli stessi dati ricampionati. |
| **Held-out** | Dati non usati per regolare il metodo. |
| **Overfitting** | Il metodo funziona bene solo sui dati su cui è stato regolato. |
| **LOCO** | *Leave-one-clip-out*: si regola su una clip e si misura sull'altra. |
| **Preregistrazione** | Fissare il protocollo prima di vedere i risultati. |
| **Plateau** | Zona ampia di manopole in cui il risultato resta buono. |
| **Smoothing** | Levigatura della traiettoria per togliere il rumore. |
| **In-sample** | Misurato sugli stessi dati usati per regolare: voto ottimistico. |
| **Baseline** | Il metodo di partenza con cui ci si confronta. |
