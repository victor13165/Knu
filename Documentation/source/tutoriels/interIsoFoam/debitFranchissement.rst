Mesure de débit de franchissement
==================================

Il vous suffit de reprendre le :doc:`tutoriel de mesure de débit de franchissement <../interFoam/debitFranchissement>`, en
remplaçant la ligne::

    application     interFoam;

par la ligne::

    application     interIsoFoam;

dans le fichier ``system/controlDict``.
