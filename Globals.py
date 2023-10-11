class Galaxy:
  currentQ=0
  currentS=0
  # quadrants - the 64 quadrants
  # contents are octal so I can mask things out easily
  # ebs
  # s=stars
  # b=bases+blackholes (black holes don't show up on long scans)
  # e=enemy
  quadrants=[0]*64
  seeds=[0]*64
  # sectors - the 64 sectors a character for the contents
  # *=star (1)
  # .=blackhole (2)
  # O=starbase (3)
  # ^=enemy (4)
  # !=ship (5)
  # @=docked (6)
  sectors=[0]*64
  # knowns is a copy of 'quadrants' at the time the long scan was done
  # so there might not be as many enemy/starbase in 'actual' because
  # these can move/be destroyed
  knowns=[0]*64
  enemys=[]
  enemyShields=[]
  enemyPhaser=200

class Status:
  # Ship type, speed (1/speed = starDates per quadrant), max energy, photons, trackers, energy/stardate
  theShip=[]
  theirTitle=""
  energy=0
  photons=0
  shields=0
  trackers=[]
  starDate=0.0
  origDate=0.0
  rating=0.0
  badPoints=0.0
  actualInvasion=0.0
  estInvasion=0.0
  enemy=[]
  enemyDown=0
  enemyCnt=0
  origEnemy=0
  origBases=0
  # Days to destroy each enemy to avoid invasion
  # Efficiency = 100 means they are on track to avoid invasion
  daysPerEnemy=0
  basesCnt=0
  moveEnergy=0
  moveDays=0
  otherLines=[]

