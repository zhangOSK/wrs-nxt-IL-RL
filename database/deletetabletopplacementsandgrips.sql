delete from tabletopgrips using tabletopgrips, tabletopplacements, freetabletopplacement
where tabletopgrips.idtabletopplacements = tabletopplacements.idtabletopplacements
and tabletopplacements.idfreetabletopplacement = freetabletopplacement.idfreetabletopplacement and freetabletopplacement.idobject = 5