#!/usr/bin/env python3

"""
Informations
============

    * Auteur: Victor Baconnet
    * Date de dernière modification: 27 août 2021

Description
============

Reconstruit et affiche les spectres de densité de puissance à partir de mesures
de hauteur d'interface par des sondes, lues dans un fichier ``.csv``. 

Si le fichier ``jonswapDict`` est 
présent dans le dossier d'exécution, le programme tracera le spectre théorique 
à partir des paramètres du fichier, et calculera les hauteurs :math:`H_s` par intégration
numérique d'après la formule
    
.. math::
    H_s = 4 \sqrt{\int_{0}^{+\infty} S(\omega)d\omega}       
    
ou, sous forme discrétisée, par intégration selon la méthode des trapèzes

.. math:: 
    H_s = 4 \sqrt{ \\frac{\Delta \omega }{2}  \sum_{i=0}^{N-1}{ S_{i+1} - S_i }} 

où :math:`S_i` est la valeur du spectre de Jonswap reconstruit.

Entrées/sorties
================

* Les mesures des sondes doivent être données dans un fichier au format csv, par défaut
  ``RESAMPLED_line_probes.csv`` mais peut être modifié avec l'option ``--sondeFile``

* Si vous souhaitez comparer les spectres calculés avec un spectre théorique de JONSWAP,
  les paramètres Tp, Hs, Tmin, Tmax, gamma doivent être donnés dans un fichier par défaut 
  ``jonswapDict``, mais peut être modifié avec l'option ``--jonswapFile``
  

Utilisation
============

--savefigs                        Sauvegarder les graphiques générés
--sondeFile fichier               Chemin d'accès vers le répertoire d'écriture
                                  du fichier waveProperties    
--jonswapFile file                chemin d'accès vers le fichier contenant les 
                                  paramètres de spectre JONSWAP                                 
--Npoints n                       Nombre de points (longueur) de chaque segment 
                                  de calcul par la méthode de Welch (https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html#r34b375daf612-1)
--scaling scale                   Echelle avec laquelle multiplier les valeurs
                                  de hauteur d'interface lues par les sondes.
                                  Par exemple si les mesures sont en cm, utiliser
                                  ``--scaling 0.01``.
                                                                     
Dépendances
============

* ``numpy``, ``scipy``, ``matplotlib``, ``pandas``
* ``jonswap``, ``outilsLecture``, ``outilsDivers``

Code source
============

Lien vers le `code source <https://github.com/victor13165/Knu/blob/main/Scripts/Post-traitement/spectre.py>`_

"""

#------- ces modules sont indispensables -----
import pandas as pd
import outilsDivers as odiv
#---------------------------------------------


def getSondeData(sondeFile, tmin, tmax):
    """
    Lecture des mesures de sondes dans le fichier sondeFile (le plus souvent sondes.csv)
    
    :param sondeFile: Nom du fichier .csv où il y a le résultat des sondes
    :type sondeFile: str
    :param tmin: Temps minimal 
    :type tmin: float
    :param tmax: Temps maximal 
    :type tmax: float
    :returns: DataFrame avec les valeurs et les noms des sondes
    :rtype: pandas.DataFrame
    """
            
    sondeData = pd.read_csv(sondeFile) #ouvrir le fichier
    
    time = sondeData.columns[0] #Récupérer le nom de la colonne du temps. Par sécurité, on ne prend pas ['time[s]']
    
    #Récupérer les indices des temps min et max
    minIdx = odiv.find(sondeData[time], tmin, 0)
    maxIdx = odiv.find(sondeData[time], tmax, -1) 
    
    if maxIdx == -1 : #Valeur max par défaut
        return sondeData[minIdx:]    #on prend jusqu'à la fin, car sondeData[i:-1] ne prend pas le dernier élément
    else:
        return sondeData[minIdx:maxIdx+1] #Dans ce cas on peut aller jusqu'à l'élément que l'on souhaite
                                          #Rappel: tab[a,b] renvoie tab de l'indice a jusqu'à l'indice b-1



if __name__ == "__main__":

    import sys
    import numpy as np
    import jonswap as jswp 
    import genHouleIrreguliere as gwp
    import os
    import outilsLecture as olec
    from scipy import signal
    import matplotlib.pyplot as plt
    from datetime import datetime

    #==========================================================================
    #------------------- Lecture des options ----------------------------------
    #==========================================================================
    
    print("\nLecture des options")
    print("--------------------------")
    
    #Sauvegarde des figures?
    savefigs = olec.readOption(sys.argv, ['-savefigs','--savefigs'])
    
    #Fichier jonswapDict contenant les paramètres du spectre de jonswap
    jonswapFile = olec.readFileOption(sys.argv, ['-jonswapFile','--jonswapFile'],
                                      default = "jonswapDict")
    
    #Fichier .csv qui contient le résultat des mesures des sondes en fonction du temps
    sondeFile   = olec.readFileOption(sys.argv, ['-sondeFile','--sondeFile', 
                                                 '--sondesFile', '-sondesFile'],
                                      default = "RESAMPLED_line_probes.csv")
    
    #Nombre de points (longueur) de chaque segment de calcul par la méthode de Welch
    Npoints = olec.readValueOption(sys.argv, ["-Npoints", "--Npoints"],
                                   default = 1024,
                                   valueType = int)
    
    scaling = olec.readValueOption(sys.argv, ["-scaling", "--scaling"],
                                   default = 1.0,
                                   valueType = float)

    print("---------------------------")
    print("Fin de lecture des options")
    
    #==========================================================================
    #------------------- Lecture du fichier sondes ----------------------------
    #==========================================================================
    
    print("\nLecture du fichier {}".format(sondeFile))
    
    #Récupérer les données de mesure des sondes
    if os.path.exists(sondeFile):
        
        sondeData = pd.read_csv(sondeFile)
        sondeData.set_index(sondeData.columns[0], inplace = True) #Pour mettre le temps comme index

    else:
        raise NameError("\n{} n'existe pas\nVeuillez spécifier un fichier\
 de sondes avec l'option --sondeFile <fichier>".format(sondeFile))

    #Nombre de sondes
    Nsondes = len(sondeData.columns)

    print("\n{} sondes détectées".format(Nsondes))

    #On récupère le temps final
    #time = sondeData.index.values
    #tmax = time[-1]

    # Calcul du pas de temps supposé constant
    #timestep = time[1] - time[0]
    timestep = 1.0/50.0
    print("Pas de temps :  {}".format(timestep))

    #==========================================================================
    #--------------------------- Rééchantillonnage ----------------------------
    #==========================================================================

    #Fréquence d'échantillonnage
    samplingFreq = 1.0/timestep
    print("Fréquence d'échantillonnage : {}".format(samplingFreq))

    #Récupère les valeurs des sondes
    valeursSondes = sondeData.values*scaling

    #Calcul du premier spectre pour déterminer la taille de chaque spectre
    f, p0 = signal.welch(valeursSondes[:,0], samplingFreq, nperseg = Npoints)   
    
    #Va contenir les spectres de densité de puissance de chaque sonde
    spectresSondes = np.zeros((len(p0), Nsondes)) 
    
    print("\nCalcul des spectres de chaque sonde")
    
    #Calcul du spectre |X|² pour chaque sonde
    for i in range(Nsondes):
        print("Sonde {}/{}".format(i,Nsondes))
        f, spectresSondes[:,i] = signal.welch(valeursSondes[:,i], samplingFreq, nperseg = Npoints)
    
    #Conversion Hz en rad/s
    w = 2.0*np.pi*f
    spectresSondes /= 2.0*np.pi #Facteur 1/2pi pour passer en rad/s
    
    #==========================================================================
    #--------------------------------- Tracé ----------------------------------
    #==========================================================================

    # -------------- Tracé des spectres de sondes -----------------------------

    plt.figure(figsize=(8,7))
    
    for i in range(Nsondes-1):
        plt.plot(w, spectresSondes[:,i], label = "{}".format(sondeData.columns[i]))
    
    plt.xlabel(r"$\omega$ (rad $s^{-1}$)", fontsize = 17)
    plt.ylabel(r"$S(\omega)$ ($m^2$ s)"     , fontsize = 17)
    plt.title("Spectre reconstruit par chaque sonde", fontsize = 17)
    plt.tick_params(axis = 'both', which = "major", labelsize = 15)
    plt.grid()
    

    # ------------------ Tracé avec le spectre idéal --------------------------

    # Si on trouve le fichier contenant les paramètres Tp, Hs, etc, on peut tracer
    # le spectre idéal
    if os.path.exists(jonswapFile):
        
        print("\n{} trouvé".format(jonswapFile))
        
        #Lecture des paramètres donnés dans jonswapDict
        param_dict = gwp.readParams(jonswapFile)
        
        Tmin,Tmax,Tp = param_dict["Tmin"], param_dict["Tmax"], param_dict["Tp"]
        Hs,gamma = param_dict["Hs"],param_dict["gamma"]   
          
        wmin = 2.0*np.pi/Tmax   #Fréquence min
        wmax = 2.0*np.pi/Tmin   #Fréquence max
        plt.xlim((wmin,wmax))
        
        w_theo = np.linspace(wmin, wmax, 1000)
            
        #Calcul du spectre de JONSWAP
        spectre = jswp.jonswap(Hs, Tp, gamma, w_theo)
        Hs_theo = 4.0 * np.sqrt(jswp.integre(spectre,w_theo[1]-w_theo[0]))
        print("\nHs obtenu théoriquement :", Hs_theo)

        # Tracé du spectre de JONSWAP théorique
        plt.plot(w_theo, spectre, label = "Spectre théorique")
        plt.legend(fontsize = 16)
        plt.tight_layout()
        
        if savefigs:
            if os.path.exists("postProcessing"):
                dirname = "postProcessing"
            else:
                dirname = "."
             
            saveFilePath = os.path.join(dirname,
                                        "spectre_sondes_N{}_{}.png".format(
                                            Npoints, datetime.now().strftime("%d-%m_%H-%M-%S")))
            
            print("Sauvegarde du graphe dans {}".format(saveFilePath))
            plt.savefig(saveFilePath)  
            
        plt.show()

        # ------------------- Calcul de Hs --------------------------------------
        print("\n----------------- Calcul des Hs ---------------------------")
        moyenne = 0.0
        for i in range(Nsondes):
            new_Hs = 4.0 * np.sqrt(jswp.integre(spectresSondes[:,i], w[1]-w[0]))
            moyenne += new_Hs
            err_rel = abs(Hs_theo - new_Hs) / Hs_theo
            print("{} : {:.3} m ==> erreur {:.2f} %".format(
                sondeData.columns[i],
                new_Hs,
                err_rel*100
            ))
        moyenne /= Nsondes
        print("Moyenne : {:.3} m ==> erreur {:.2f} %".format(
            moyenne,
            abs(moyenne - Hs_theo) / Hs_theo * 100
        ))

        print("------------------------------------------------------------")
    
    # Si jonswapDict n'existe pas
    else:

        # ------------------- Calcul de Hs --------------------------------------
        print("\n ----------- Calcul des Hs --------------")
        for i in range(Nsondes):
            new_Hs = 4.0 * np.sqrt(jswp.integre(spectresSondes[:,i], w[1]-w[0]))
            print(f"{sondeData.columns[i]} : {new_Hs} m")
        print("-------------------------------------------")

        print("{} n'existe pas".format(jonswapFile))
        plt.legend(fontsize = 16)
        plt.tight_layout()
        if savefigs:
            if os.path.exists("postProcessing"):
                dirname = "postProcessing"
            else:
                dirname = "."
             
            saveFilePath = os.path.join(dirname,
                                        "spectre_sondes_N{}_{}.png".format(
                                            Npoints, datetime.now().strftime("%d-%m_%H-%M-%S")))
            
            print("Sauvegarde du graphe dans {}".format(saveFilePath))
            plt.savefig(saveFilePath)  
      
    
        plt.show()
      
    #-----------------------------------------------------------------------------------
