"""
Module d'analyse des données de ponctualité SNCF.

Ce module regroupe des fonctions utilitaires pour le nettoyage, le calcul
d'indicateurs (taux de retard, poids du retard, classements) et la
visualisation des performances des lignes TGV, ainsi que des tests
statistiques (Kruskal-Wallis, post-hoc de Dunn) permettant de comparer
la ponctualité entre lignes.

Fonctions principales :
    - sncf_ligne : construit le libellé d'une ligne (gare départ - gare arrivée).
    - sncf_reel : calcule le nombre réel de trains en circulation.
    - sncf_percent : calcule le pourcentage de trains en retard.
    - sncf_timing : calcule le poids du retard moyen par rapport à la durée du trajet.
    - plt_classement : affiche un classement horizontal (Seaborn).
    - sncf_classement : établit un classement des lignes TGV par médiane.
    - k_w : teste l'égalité des distributions entre lignes TGV (Kruskal-Wallis + Dunn).

Dépendances :
    - pandas
    - seaborn
    - matplotlib
    - scipy.stats
    - scikit_posthocs

Auteur : Alexis LE CALVEZ
Date : 04/09/2026
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import scikit_posthocs as sp

def sncf_ligne(df: pd.Series) -> str:
    """Construit le libellé de la ligne ferroviaire à partir d'une ligne du DataFrame.

    Réuni les noms de la gare de départ et de la gare d'arrivée
    (nettoyés des espaces superflus et mis en majuscules) au format
    "GARE_DEPART - GARE_ARRIVEE".

    Args:
        df (pd.Series): Ligne du DataFrame (issue d'un `.apply(axis=1)`)
            contenant au minimum les clés suivantes :
                - "gare_depart" (str) : nom de la gare de départ.
                - "gare_arrivee" (str) : nom de la gare d'arrivée.

    Returns:
        str: Libellé de la ligne au format "GARE_DEPART - GARE_ARRIVEE".

    Raises:
        KeyError: Si "gare_depart" ou "gare_arrivee" est absent de `df`.
        AttributeError: Si l'une des deux valeurs n'est pas une chaîne
            de caractères (absence de méthode `.strip()`).

    Example:
        >>> import pandas as pd
        >>> row = pd.Series({"gare_depart": " paris ", "gare_arrivee": "lyon"})
        >>> sncf_ligne(row)
        'PARIS - LYON'
    """
    ligne = df["gare_depart"].strip().upper() + " - " + df["gare_arrivee"].strip().upper()  # création de la ligne
    return ligne  # return de la ligne dans le df

def sncf_reel(df: pd.Series) -> int:
    """Calcule le nombre réel de trains ayant circulé.

    Soustrait le nombre de trains annulés au nombre de trains prévus
    pour obtenir le nombre de trains en circulation.

    Args:
        df (pd.Series): Ligne du DataFrame (issue d'un `.apply(axis=1)`)
            contenant au minimum les clés suivantes :
                - "nb_train_prevu" (int) : nombre de trains prévus au programme.
                - "nb_annulation" (int) : nombre de trains annulés.

    Returns:
        int: Nombre réel de trains en circulation
            (nb_train_prevu - nb_annulation).

    Raises:
        KeyError: Si "nb_train_prevu" ou "nb_annulation" est absent de `df`.
        TypeError: Si l'une des deux valeurs n'est pas numérique.

    Example:
        >>> import pandas as pd
        >>> row = pd.Series({"nb_train_prevu": 120, "nb_annulation": 5})
        >>> sncf_reel(row)
        115
    """
    n_train_reel = df["nb_train_prevu"] - df["nb_annulation"]
    return n_train_reel

def sncf_percent(df: pd.Series) -> float:
    """Calcule le pourcentage de trains en retard.

    Rapporte le nombre de trains en retard au nombre total de trains,
    exprimé en pourcentage.

    Args:
        df (pd.Series): Ligne du DataFrame (issue d'un `.apply(axis=1)`)
            contenant au minimum les clés suivantes :
                - "train_retard" (int) : nombre de trains en retard.
                - "train_total" (int) : nombre total de trains.

    Returns:
        float: Pourcentage de trains en retard, compris entre 0 et 100
            (sauf valeurs incohérentes en amont).

    Raises:
        KeyError: Si "train_retard" ou "train_total" est absent de `df`.
        ZeroDivisionError: Si "train_total" vaut 0.
        TypeError: Si l'une des deux valeurs n'est pas numérique.

    Example:
        >>> import pandas as pd
        >>> row = pd.Series({"train_retard": 15, "train_total": 100})
        >>> sncf_percent(row)
        15.0
    """
    percent_retard = (df["train_retard"] / df["train_total"]) * 100
    return percent_retard

def sncf_timing(df: pd.Series) -> float:
    """Calcule le poids relatif du retard moyen par rapport à la durée moyenne du trajet.

    Exprime le retard moyen à l'arrivée en pourcentage de la durée
    moyenne du trajet, en valeur absolue. Renvoie 0 si le retard moyen
    ou la durée moyenne est nul, afin d'éviter une division par zéro.

    Args:
        df (pd.Series): Ligne du DataFrame (issue d'un `.apply(axis=1)`)
            contenant au minimum les clés suivantes :
                - "retard_moyen_arrivee" (float) : retard moyen à l'arrivée
                    (en minutes).
                - "duree_moyenne" (float) : durée moyenne du trajet
                    (en minutes).

    Returns:
        float: Pourcentage du retard moyen par rapport à la durée moyenne
            du trajet (valeur absolue), ou 0 si l'un des deux termes est nul.

    Raises:
        KeyError: Si "retard_moyen_arrivee" ou "duree_moyenne" est absent
            de `df`.
        TypeError: Si l'une des deux valeurs n'est pas numérique.

    Example:
        >>> import pandas as pd
        >>> row = pd.Series({"retard_moyen_arrivee": 6, "duree_moyenne": 120})
        >>> sncf_timing(row)
        5.0
        >>> row_nulle = pd.Series({"retard_moyen_arrivee": 0, "duree_moyenne": 120})
        >>> sncf_timing(row_nulle)
        0
    """
    if df["retard_moyen_arrivee"] == 0 or df["duree_moyenne"] == 0:
        return 0
    else:
        percent = (abs(df["retard_moyen_arrivee"]) / abs(df["duree_moyenne"])) * 100
        return percent

def plt_classement(df: pd.DataFrame, n: int, xv: str, yv: str, c: str) -> None:
    """Affiche un classement horizontal sous forme de diagramme en barres.

    Sélectionne les `n` premières lignes du DataFrame (dans leur ordre
    actuel, supposé déjà trié) et les représente sous forme de barres
    horizontales via Seaborn, avec un thème pastel et fond quadrillé.

    Args:
        df (pd.DataFrame): DataFrame source contenant les données à tracer.
            Doit être trié au préalable selon le critère de classement
            souhaité.
        n (int): Nombre de lignes à afficher (les `n` premières de `df`).
        xv (str): Nom de la colonne à utiliser pour l'axe des x
            (valeurs numériques).
        yv (str): Nom de la colonne à utiliser pour l'axe des y
            (catégories, ex. noms des lignes/gares).
        c (str): Couleur des barres (nom Matplotlib ou code couleur).

    Returns:
        None: La fonction affiche le graphique via Seaborn/Matplotlib
            mais ne retourne aucune valeur. Le graphique doit être
            explicitement affiché avec `plt.show()` après l'appel.

    Raises:
        KeyError: Si `xv` ou `yv` n'existe pas dans les colonnes de `df`.
        ValueError: Si `n` est négatif ou si `df` est vide.

    Example:
        >>> import pandas as pd
        >>> import matplotlib.pyplot as plt
        >>> df = pd.DataFrame({
        ...     "ligne": ["PARIS - LYON", "LYON - MARSEILLE"],
        ...     "retards": [45, 30]
        ... })
        >>> plt_classement(df, n=2, xv="retards", yv="ligne", c="skyblue")
        >>> plt.show()

    Note:
        Le paramètre `orient="h"` combiné à `x=xv, y=yv` suppose que `xv`
        est la variable numérique et `yv` la variable catégorielle. Vérifie
        que l'ordre des arguments correspond bien à ce que Seaborn attend
        pour ta version de la librairie (ce comportement a évolué entre
        les versions de Seaborn).
    """
    sns.set_theme(style="whitegrid", palette="pastel")
    sns.barplot(data=df.head(n), x=xv, y=yv, orient="h", color=c, edgecolor="black", width=0.2, gap=0)

def sncf_classement(df: pd.DataFrame, val: str, size: int) -> pd.DataFrame:
    """Établit un classement des lignes TGV selon la médiane d'une variable donnée.

    Regroupe les données par ligne TGV, calcule la médiane de la colonne
    `val` pour chaque ligne, arrondit le résultat à une décimale, trie
    les lignes par ordre décroissant, puis renvoie les `size` premières.

    Args:
        df (pd.DataFrame): DataFrame source contenant au minimum les
            colonnes "ligne_TGV" et `val`.
        val (str): Nom de la colonne numérique sur laquelle calculer
            la médiane (ex. "retard_moyen_arrivee").
        size (int): Nombre de lignes TGV à conserver dans le classement
            (les `size` premières après tri décroissant).

    Returns:
        pd.DataFrame: DataFrame indexé par "ligne_TGV", contenant une
            colonne `val` avec la médiane arrondie, trié par ordre
            décroissant et limité aux `size` premières lignes.

    Raises:
        KeyError: Si "ligne_TGV" ou `val` n'existe pas dans les colonnes
            de `df`.
        TypeError: Si la colonne `val` n'est pas numérique.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "ligne_TGV": ["A", "A", "B", "B"],
        ...     "retard": [10, 20, 5, 7]
        ... })
        >>> sncf_classement(df, val="retard", size=1)
                   retard
        ligne_TGV
        A            15.0
    """
    classement = df.groupby("ligne_TGV")[val].median().round(1).sort_values(ascending=False)
    classement = pd.DataFrame(classement)
    return classement.head(size)

#calcul du kruskal : 

def k_w(df: pd.DataFrame, vl: str, alpha: float) -> pd.Series | None:
    """Teste l'égalité des distributions entre lignes TGV (Kruskal-Wallis) et identifie les groupes significativement différents.

    Applique un test de Kruskal-Wallis pour comparer la distribution de
    la variable `vl` entre les différentes lignes TGV. Si le résultat
    est statistiquement significatif (p-value <= `alpha`), effectue un
    test post-hoc de Dunn (avec correction de Bonferroni pour tests
    multiples) afin d'identifier, pour chaque ligne TGV, le nombre
    d'autres lignes dont elle se distingue significativement.

    Args:
        df (pd.DataFrame): DataFrame source contenant au minimum les
            colonnes "ligne_TGV" (groupes à comparer) et `vl`.
        vl (str): Nom de la colonne numérique dont on compare la
            distribution entre les groupes (ex. "retard_moyen_arrivee").
        alpha (float): Seuil de significativité du test (typiquement 0.05).

    Returns:
        pd.Series | None:
            - Si le test de Kruskal-Wallis est significatif (p-value <= alpha) :
              une Series indexée par "ligne_TGV", donnant pour chaque ligne
              le nombre d'autres lignes dont elle diffère significativement
              (test de Dunn), triée par ordre décroissant.
            - Si le test n'est pas significatif : `None` (un message est
              affiché via `print` indiquant que le résultat n'est pas
              significatif).

    Raises:
        KeyError: Si "ligne_TGV" ou `vl` est absent de `df`.
        ValueError: Si `df` contient moins de deux groupes distincts
            dans "ligne_TGV".

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     "ligne_TGV": ["A", "A", "B", "B", "C", "C"],
        ...     "retard": [5, 6, 20, 22, 4, 5]
        ... })
        >>> k_w(df, vl="retard", alpha=0.05)
        ligne_TGV
        B    2
        A    0
        C    0
        dtype: int64

    Note:
        Nécessite les modules `scipy.stats` (aliasé `stats`) et
        `scikit_posthocs` (aliasé `sp`) importés en amont.
    """
    kstat, pval = stats.kruskal(*[group[vl].values for name, group in df.groupby('ligne_TGV')])  # calcul du Pvalue
    if pval <= alpha:
        dunn = sp.posthoc_dunn(
            df,
            val_col=vl,
            group_col="ligne_TGV",
            p_adjust="bonferroni"  # correction multiplication de tests
        )

        significatif = dunn < alpha
        nb_diff = significatif.sum(axis=1) - 1
        resultat = nb_diff.sort_values(ascending=False)
        return resultat
    else:
        print(f"Le test statistique n'est pas significatif {pval} est supérieur à {alpha} pour la variable {vl}")

    


