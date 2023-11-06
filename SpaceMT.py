# An adaption of SpaceTrek done ages ago for ACTS Computing
# Version 1.0 - November 2021
# This version is planned to run on the AdaFruit MagTag.
# I have tried to keep all the "I/O" isolated, so it should be able to be moved
# to a different platform

# ToDo:
# *) Refactor to put collect 'utilities' in one section commands in another
# *) 'optimize' display refresh (make sure we only call it when needed)
# *) Start at a starbase
# *) Calculate rating/efficiency
# *) Game startup (get Sir/Madam, ship type)
# *) Game ending
# *) Invasion (swarm)
# *) Enemy moving
# **) After shooting at enemy.. if the enemy fires back it doesn't say so
# **) Redo doMove so it isn't re-entrant
# **) Buttons don't always work? (probably GC - need to figure out more of how to force GC)
# **) Why didn't docking bring power back up to 100%
# **) Efficiency is always negative?
# **) Cycle LEDS when waiting for a button (only if can figure out asyncio)
# 16) Cycle LEDS when waiting for the screen refresh
# **) SOS needs to be 'longer' (sleep between each tone)
# **) "victory" celebration!
# **) Setting shields.. when lowering.. Power ends up negative
# **) Efficency is way too small
# **) When launching trackers only show "around" that have an enemy in 'knowns'
# 22) Efficency needs more work
# **) Need to 'scroll' otherText.  Create function to take a line
#     and add it to an array.. if there are more than 9 lines, put 9 up
#     and wait.  waitForDisplay will need to collect the lines and put them
#     into the correct area.
# **) Ask if they want to see instructions at the beginning (read from file)
# 25) Find/Destroy startbase (do we define shields, or just use 4/5 enemy in quadrant)
# 26) Damage/Fix/Repair stuff.
# **) Button width in getMove needs to be adjusted.


import time
import random
import board
import terminalio
import displayio
from adafruit_display_text import label
from adafruit_magtag.magtag import MagTag
import gc
import supervisor

# Setup Magtag "stuff"
magtag = MagTag(default_bg=0x0)

magtag.display.show(None) 

import Globals
galaxy=Globals.Galaxy
status=Globals.Status

MAXENEMY=26
MAXSTARBASES=3

# galaxy.sectors will be filled with one of these
SECTOREMPTY=" "
SECTORSTAR="*"
SECTORBH="?"
SECTORSB="O"
SECTORENEMY="#"
SECTORME="+"
SECTORDOCKED="@"
# We need to be able to tell if a tracker is available or destroyed when we destroyed the enemy it was tracking
TRACKERAVAIL=-1
TRACKERDONE=-2
#Length of the buttons - this is a 'generic' left format string (do BUTTONLEN % "word")
BUTTONLEN="%-7s"

# The screen is divided into 3 areas
# 0) - The command display area at the bottom
# 1) - The status display area on the right
# 2) - The 'other' area for short/long scans, tracking info, etc.
mainGroup=displayio.Group()
commandGroup=displayio.Group()
cmdLabel=label.Label(terminalio.FONT, line_spacing=0.9,anchor_point=(0.0,0.0),anchored_position=(0,115),save_text=False)
commandGroup.append(cmdLabel)
mainGroup.append(commandGroup)
cgIdx=0
statusGroup=displayio.Group()
statusLabel=label.Label(terminalio.FONT, line_spacing=0.9, anchor_point = (0.0, 0.0), anchored_position = (211, 0),save_text=False)
statusGroup.append(statusLabel)
mainGroup.append(statusGroup)
sgIdx=1
otherGroup=displayio.Group()
otherLabel=label.Label(terminalio.FONT, line_spacing=0.9,anchor_point = (0.0, 0.0), anchored_position = (0, 0),save_text=False)
otherGroup.append(otherLabel)
mainGroup.append(otherGroup)
ogIdx=2
board.DISPLAY.show(mainGroup)

# A 'generic' function to space pad the commands
def spacePad(theWord):
  return "%-7s" & theWord
# Update the status rows/information
def updateStatus():
  # How many I should have shot = (starDate-origDate)/daysPerEnemy
  # Actual/should have = efficiency
  if status.origDate<status.starDate:
    efficiency=100.0*status.enemyDown/((status.starDate-status.origDate)/status.daysPerEnemy)
    if efficiency>200.0:
      efficiency=200.0
  else:
    efficiency=0.0
  print("daysPerEnemy,starDate,origDate",status.daysPerEnemy,status.starDate,status.origDate)
  theText="Status :"
  if galaxy.quadrants[galaxy.currentQ]&0o700 == 0:
    theText+=" Green"
  else:
    theText+="   Red"
  theText+="\nDate   :{:6.1f}\n\
QQ:SS  : {:02o}:{:02o}\n\
Power  :{:6.1f}\n\
Shields:{:6.1f}\n\
Photons:{:6}\n\
Enemy  :{:6}\n\
Killed :{:6}\n\
Rating :{:6.1f}\n\
Swarm  :{:6.1f}".format(status.starDate,galaxy.currentQ,galaxy.currentS,status.energy,status.shields,status.photons,status.enemyCnt,status.enemyDown,efficiency,status.estInvasion)
  statusLabel.text=theText

# Fill in the details of the current quadrant
# withPlayer=True will insert the player marker too
def fillSectors(withPlayer):
  print("Fill Quadrant: {:02o}:{:02o} -> {:5o}".format(galaxy.currentQ,galaxy.currentS,galaxy.quadrants[galaxy.currentQ]))
  galaxy.sectors=[SECTOREMPTY]*64
  # Always start with the same seed so stars, black holes and base don't move
  random.seed(galaxy.seeds[galaxy.currentQ])
  for i in range(galaxy.quadrants[galaxy.currentQ]&0o7):
    s=random.randint(0,0o77)
    # Don't put it in a sector that already has a star
    while galaxy.sectors[s]!=SECTOREMPTY:
      s=random.randint(0,0o77)
    galaxy.sectors[s]=SECTORSTAR
  # Now we need to put in any black holes (because they never move)
  if galaxy.quadrants[galaxy.currentQ]&0o20!=0:
    s=random.randint(0,0o77)
    while galaxy.sectors[s]!=SECTOREMPTY:
      s=random.randint(0,0o77)
    galaxy.sectors[s]=SECTORBH
  # Finally a starbase (because they might get destroyed)
  if galaxy.quadrants[galaxy.currentQ]&0o10!=0:
    s=random.randint(0,0o77)
    while galaxy.sectors[s]!=SECTOREMPTY:
      s=random.randint(0,0o77)
    galaxy.sectors[s]=SECTORSB
  # Now for some enemys.
  q=galaxy.currentQ<<6
  for enemy in galaxy.enemys:
    if enemy&0o7700 == q:
        s=enemy&0o77      # Peal off the sector partition
        galaxy.sectors[s]=SECTORENEMY
  if withPlayer:
    if galaxy.sectors[galaxy.currentS]==SECTOREMPTY:
      galaxy.sectors[galaxy.currentS]=SECTORME
      # Check to see if they docked with the starbase
    elif galaxy.sectors[galaxy.currentS]==SECTORSB:
        galaxy.sectors[galaxy.currentS]=SECTORDOCKED
    else:
      print("Ship sector already occupied: {:o}:{:o}".format(galaxy.currentQ,galaxy.currentS))
      assert False
      
# Returns the points along a line from A to B
def trackShot(theFrom, theTo):
  fy=theFrom>>3
  fx=theFrom&0o07
  ty=theTo>>3
  tx=theTo&0o07
  thePoints=[]
  # Code adapted from https://github.com/encukou/bresenham
  # Implementation of Bresenham's line drawing algorithm
  #See en.wikipedia.org/wiki/Bresenham's_line_algorithm
  dx = fx - tx
  dy = fy - ty
  xsign = 1 if dx > 0 else -1
  ysign = 1 if dy > 0 else -1
  dx = abs(dx)
  dy = abs(dy)
  if dx > dy:
    xx, xy, yx, yy = xsign, 0, 0, ysign
  else:
    dx, dy = dy, dx
    xx, xy, yx, yy = 0, ysign, xsign, 0
  D = 2*dy - dx
  y = 0
  for x in range(dx + 1):
    # yield tx + x*xx + y*yx, ty + x*xy + y*yy
    thePoints.append((tx + x*xx + y*yx)+((ty + x*xy + y*yy)<<3))
    print("{:02o} {:02o} {:02o}".format(((tx + x*xx + y*yx)+((ty + x*xy + y*yy)<<3)),(tx + x*xx + y*yx),(ty + x*xy + y*yy)))
    if D >= 0:
      y += 1
      D -= 2*dx
    D += 2*dy
  return thePoints

# Display/wait for the next command choice
# This is really the main processing 'loop'
# NOTE: we don't clear the display before this.. the command processing should decide
def getCommand():
  # 3 buttons = 3 commands at a time
  # 1 button = 'More'
  # Wait for them to press a button to pick a command
  while True:
    theAns=getButtonCommand(["Short","Long","Move","Photon","Phaser","Shields","Tracker","Clear"]
,"","More..")
    cmd=theAns[1]
    if cmd=="Short":
      showShortScan()
    if cmd=="Long":
      showLongScan()
    if cmd=="Move":
      getMove()
    if cmd=="Photon":
      doFire("photon")
    if cmd=="Phaser":
      doFire("phaser")
    if cmd=="Shields":
      setShields()
    if cmd=="Tracker":
      doTrackers()
    if cmd=="Clear":
      clearKnowns()
      
# Let them clear out all the 'knowns' so they know what was scanned
def clearKnowns():
  addOtherLine("Clear all known scans? "+status.theirTitle)
  ans=getButtonCommand(["Yes"],"Cancel","")
  if ans[1]=="Cancel":
    addOtherLine("Scans retained. "+status.theirTitle)
  else:
    status.knowns=["   "]*64
    addOtherLine("Scans cleared. "+status.theirTitle)

# Display the current trackers attached to enemy
# Left them launch one if they want
def doTrackers():
  # First we display all the trackers currently deployed
  addOtherLine("Current tracker reports:")
  trackersFree=0
  for aTracker in status.trackers:
    if aTracker==TRACKERAVAIL:
      # Count those available
      trackersFree+=1
    elif aTracker != TRACKERDONE:
      # Not available, and not done - points to an enemy
      addOtherLine("Enemy at: {:02o}:{:02o}\n".format(galaxy.enemys[aTracker]>>6,galaxy.enemys[aTracker]&0o77))
  if trackersFree==0:
    getButtonCommand([],"OK","")
    return
  # Create a list.. one as a string, and one with the numeric value
  aList=[]
  qList=[]
  for qq in around(galaxy.currentQ):
    if qq >= 0:
      # We will only show quadrants where they saw enemy last time they did a long scan
      if galaxy.knowns[qq][0]!=" " and galaxy.knowns[qq][0]!="0":
        aList.append("{:02o}".format(qq))
        qList.append(qq)
  # They should be able to launch a tracker into the current quadrant
  if galaxy.knowns[galaxy.currentQ][0]!=" " and galaxy.knowns[galaxy.currentQ][0]!="0":
    aList.append("{:02o}".format(galaxy.currentQ))
    qList.append(galaxy.currentQ)
  if len(aList)==0:
    addOtherLine("No known enemy to direct tracker to. {:}".format(status.theirTitle))
    return
  ans=getButtonCommand(aList,"Cancel","More..")
  print("From Trackers",ans)
  if ans[1]=="Cancel":
    addOtherLine("No Trackers Launched! "+status.theirTitle)
    return
  # Get the quadrant that they launched into
  qq=qList[ans[0]]<<6
  # Pick a tracker we are launching
  tidx=status.trackers.index(TRACKERAVAIL)
  # Now find the first enemy in that quadrant
  for idx in range(len(galaxy.enemys)):
    if (galaxy.enemys[idx]&0o7700) == qq:
      # Found one - make sure it isn't already being tracked 
      if not (idx in status.trackers):
        # OK.. this one is not being tracker - find an available tracker
        ############### doesn't pick the right one #############
        status.trackers[tidx]=idx
        break       # No need to look further
  # If there aren't any enemy in that quadrant, the tracker self destructs
  if status.trackers[tidx]==TRACKERAVAIL:
    # Did not find any enemy to track
    addOtherLine("No enemy in {} to track".format(aList[ans[0]]))
    addOtherLine("Tracker self destructed")
    status.trackers[tidx]=TRACKERDONE
  else:
    # Let them know the tracker is working
    addOtherLine("Tracker reporting enemy at: {:02o}:{:02o}\n".format(galaxy.enemys[status.trackers[tidx]]>>6,galaxy.enemys[status.trackers[tidx]]&0o77))

# Set the shields
def setShields():
  power=status.energy+status.shields
  # Need to find out how much power they want to use
  # Too complicated to do 3 or 4 digits via the buttons
  # So we will give them 6 choices (2 at a time)
  addOtherLine("Power available {:6.1f}".format(power))
  addOtherLine("Set power to shields? {:}".format(status.theirTitle))
  if power<60:
    # One last shot?
    increment=int(power/6.0)
  elif power<600:
    increment=int(power/60.0)*10
  else:
    increment=int(power/600.0)*100
  eList=[]
  for i in range(1,7):
    eList.append(str(increment*i))
  eAns=getButtonCommand(eList,"Cancel","More..")
  print(eAns)
  if eAns[1]=="Cancel":
    addOtherLine("Shield change canceled! "+status.theirTitle)
    return
  status.shields=int(eList[eAns[0]])
  status.energy=power-status.shields
  print("Shields,Energy",status.shields,status.energy)
  addOtherLine("Shields set to {:} {:}".format(status.shields,status.theirTitle))
  updateStatus()

# Take care of firing a photon torpedo or a phaser bolt
def doFire (fireWhat):
  if galaxy.quadrants[galaxy.currentQ]&0o700==0:
    # Nobody to shoot at
    addOtherLine("No enemy in this quadrant! "+status.theirTitle)
    return
  # For photons, we need to make sure we have one
  if fireWhat=="photon":
    if status.photons==0:
      # No photons to fire
      addOtherLine("No photon torpedos available! "+status.theirTitle)
      return
  else:
    # Need to find out how much power they want to use
    # Too complicated to do 3 or 4 digits via the buttons
    # So we will give them 6 choices (2 at a time)
    if status.energy<60:
      # One last shot?
      increment=int(status.energy/6.0)
    elif status.energy<600:
      increment=int(status.energy/60.0)*10
    else:
      increment=int(status.energy/600.0)*100
    eList=[]
    for i in range(1,7):
      eList.append(str(increment*i))
    addOtherLine("Specify power to phaser {:}".format(status.theirTitle))
    eAns=getButtonCommand(eList,"Cancel","More..")
    if eAns[1]=="Cancel":
      addOtherLine("Firing orders canceled! "+status.theirTitle)
      return
  # Find all the enemy locations
  # Rather than make them button in a sector via +-
  # We will present them with a list of enemy in the quadrant
  addOtherLine("Select fire coordinates. {:}".format(status.theirTitle))
  guysHere=[]
  pickList=[]
  q=galaxy.currentQ<<6
  for enemy in galaxy.enemys:
    if enemy&0o7700 == q:
      guysHere.append(enemy&0o77)    
      pickList.append("{:02o}    ".format(enemy&0o77))
  theAns=getButtonCommand(pickList,"Cancel","More..")
  print("Enemy pick",theAns)
  if theAns[1]=="Cancel":
    addOtherLine("Firing orders canceled! "+status.theirTitle)
    return
  fy=galaxy.currentS>>3
  fx=galaxy.currentS&0o07
  ty=guysHere[theAns[0]]>>3
  tx=guysHere[theAns[0]]&0o07
  shotPoints=trackShot(galaxy.currentS,guysHere[theAns[0]])
  fillSectors(True)
  # Might need to reverse the list to get 'from' at 0
  if shotPoints[0]==guysHere[theAns[0]]:
    shotPoints.reverse()
  print(shotPoints)
  # We have fired.. even if we never hit anything
  if fireWhat=="phaser":
    # Even if it misses, we have used the power
    status.power-=float(eList[eAns[0]])
  else:
    status.photons-=1
  addOtherLine("Tracking shot."+status.theirTitle)
  shotTracks=[]
  for aPoint in shotPoints:
    print("{:02o}->{}".format(aPoint,galaxy.sectors[aPoint]))
    shotTracks.append("{:02o} ".format(aPoint))
    # See if there is anything in the way
    if galaxy.sectors[aPoint]==SECTORSTAR:
      addOtherLine(" ".join(shotTracks))
      addOtherLine("Shot impacted a star.")
      # Any enemy left in the quadrant will definately fire back
      enemyFire(True)
      updateStatus()
      break
    elif galaxy.sectors[aPoint]==SECTORBH:
      addOtherLine(" ".join(shotTracks))
      addOtherLine("Shot swallowed by a black hole.")
      # Any enemy left in the quadrant will definately fire back
      enemyFire(True)
      updateStatus()
      break
    elif galaxy.sectors[aPoint]==SECTORSB:
      addOtherLine(" ".join(shotTracks))
      addOtherLine("You just hit your starbase.")
      # Any enemy left in the quadrant will definately fire back
      enemyFire(True)
      updateStatus()
      break
    elif galaxy.sectors[aPoint]==SECTORENEMY:
      addOtherLine(" ".join(shotTracks))
      #NOTE: we might end up 'accidentally' hitting an enemy
      #      or this is the last point (which is ok either way)
      eidx=galaxy.enemys.index((galaxy.currentQ<<6)+aPoint)
      if fireWhat=="phaser":
        # Need to calculate hit power, and check the enemy shields
        dist=calcDistance(galaxy.currentQ,galaxy.currentS,galaxy.currentQ,aPoint)
        power=float(eList[eAns[0]])
        power=power-0.5*(power-power/dist)
        addOtherLine("{:6.1f} hit on enemy at {:02o}".format(power,aPoint))
        if power<galaxy.enemyShields[eidx]:
          galaxy.enemyShields[eidx]-=power
          enemyFire(True)
          updateStatus()
          return
      addOtherLine("Enemy destroyed")
      # Now we need to find the enemy that was just destroyed.
      # Also remove it from contents (update knowns too)
      galaxy.quadrants[galaxy.currentQ]-=0o100
      galaxy.knowns[galaxy.currentQ]=galaxy.quadrants[galaxy.currentQ]
      for i in range(len(status.trackers)):
        if status.trackers[i]>eidx:
          # Backup one for all those past the one we will be removing
          status.trackers[i]-=1
        elif status.trackers[i]==eidx:
          # The one pointing to this one is 'destroyed'
          status.trackers[i]=TRACKERDONE
        # Don't need to do anything for those less than the one we remove
      status.enemyCnt-=1
      status.enemyDown+=1
      if status.enemyCnt==0:
        addOtherLine("VICTORY!!!!")
        addOtherLine("You defeated all the enemy!"+status.theirTitle)
        updateStatus()
        getButtonCommand(["Restart"],"","")
        supervisor.reload()
        # 'technically' this return will never get executed
        return
      galaxy.enemys.pop(eidx)
      galaxy.enemyShields.pop(eidx)
      # Any enemy left in the quadrant will definately fire back
      enemyFire(True)
      updateStatus()
      break
  return
  
# Display the short range scan
def showShortScan():
  fillSectors(True)
  # NOTE: This looks like a strange way of building up a string
  #       but Python doesn't like lots of string concationation
  theRows=[" :0:1:2:3:4:5:6:7:\n"]
  for i in range(8):
    j=i*8
    theRows.append("{}:{}:{}:{}:{}:{}:{}:{}:{}:{}\n".format(i,
    galaxy.sectors[j],
    galaxy.sectors[j+1],
    galaxy.sectors[j+2],
    galaxy.sectors[j+3],
    galaxy.sectors[j+4],
    galaxy.sectors[j+5],
    galaxy.sectors[j+6],
    galaxy.sectors[j+7],
    i))
  addOtherLine("".join(theRows))

# Generalized getting a command button
# theList = the complete list of buttons
# always = an optional command that will show on every set of 4 buttons
# page = the command that advances to the next set of items in theList
#        (optional, and will always be 4th button)
def getButtonCommand(theList,always,page):
  activeCnt=3       # We start with this zero based
  blankEntry=BUTTONLEN % " "
  cmdList=[blankEntry,blankEntry,blankEntry,blankEntry]
  if page!="":
    pageIdx=activeCnt
    cmdList[activeCnt]=BUTTONLEN % page
    activeCnt-=1
  else:
    # So no button ever 'finds' page
    pageIdx=-100
  if always!="":
    cmdList[activeCnt]=BUTTONLEN % always
    activeCnt-=1
  # Make activeCnt= length of the available 'theList' locations
  activeCnt+=1
  beg=0
  cnt=len(theList)
  for i in range(activeCnt):
    if i+beg<cnt:
      cmdList[i]=BUTTONLEN % theList[i+beg]
    else:
      cmdList[i]=blankEntry
  cmdLabel.text=" ".join(cmdList)
  # Display the commands and loop for a button press
  wait2refresh()
  picked=-1
  # Turn off all the LEDs
  whichLED=0
  magtag.peripherals.neopixels.fill((0,0,0))
  # And loop until we gt a button press
  while picked<0:
    #magtag.peripherals.neopixels[whichLED]=(0,0,0)
    #whichLED=(whichLED+1)&3
    #magtag.peripherals.neopixels[whichLED]=(0,255,0)
    if magtag.peripherals.button_a_pressed:
      if cmdList[0]!=blankEntry:
        picked=0
        while magtag.peripherals.button_a_pressed: time.sleep(0.01)
    if magtag.peripherals.button_b_pressed:
      if cmdList[1]!=blankEntry:
        picked=1
        while magtag.peripherals.button_b_pressed: time.sleep(0.01)
    if magtag.peripherals.button_c_pressed:
      if cmdList[2]!=blankEntry:
        picked=2
        while magtag.peripherals.button_c_pressed: time.sleep(0.01)
    if magtag.peripherals.button_d_pressed:
      if cmdList[3]!=blankEntry:
        picked=3
        while magtag.peripherals.button_d_pressed: time.sleep(0.01)
    if picked==pageIdx:
      picked=-1           #So the while loop continues
      beg+=activeCnt
      if beg>=cnt:
        beg=0
      for i in range(activeCnt):
        if i+beg<cnt:
          cmdList[i]=BUTTONLEN % theList[i+beg]
        else:
          cmdList[i]=blankEntry
      print(cmdList)
      cmdLabel.text=" ".join(cmdList)
      wait2refresh()
  #magtag.peripherals.neopixels.fill((0,0,0))
  return (picked+beg,cmdList[picked].rstrip())        
	
# doMove - This is easier than actually getting the value
def doMove(newQ,newS):
  print("Moving to: {:o}:{:o}".format(newQ,newS))
  # We always can move to the new quadrant - need to see if we hit anything
  galaxy.currentQ=newQ
  fillSectors(False)
  if galaxy.sectors[newS]==SECTORSB:
    # Landed on the starbase - replenish energy, photons
    # We add in the moveEnergy, because it will get taken out when we update
    status.energy=status.theShip[2]+status.moveEnergy
    status.photons=status.theShip[3]
    # Reload any destroyed trackers
    for i in range(len(status.trackers)):
      if status.trackers[i]==TRACKERDONE:
        status.trackers[i]=TRACKERAVAIL
    status.shields=0
    addOtherLine("Docked at Starbase:{:02o}:{:02o}".format(newQ,newS))
    addOtherLine("Shields lowered.")
  if galaxy.sectors[newS]==SECTORBH:
    # Landed on a black hole - send them to a random quadrant
    newQ=random.randint(0,0o77)
    galaxy.currentQ=newQ
    # Now find them an empty spot to land in
    fillSectors(False)
    newS=random.randint(0,0o77)
    while galaxy.sectors[newS]!=SECTOREMPTY:
      newS=random.randint(0,0o77)
    addOtherLine("Black Hole bounce to:{:02o}:{:02o}".format(newQ,newS))
    # And let the normal 'Empty sector' logic handle the rest
  # We may be 'diverting' - so pick an available sector
  keepers=[]
  for x in around(newS):
    if x>=0:
      keepers.append(x)
  x=random.randint(0,len(keepers)-1)
  while galaxy.sectors[keepers[x]]!=SECTOREMPTY:
    x=random.randint(0,len(keepers)-1)
    print ("New x",x)
  # This is an empty sector if we need to bounce
  bounceTo=keepers[x]
  if galaxy.sectors[newS]==SECTORSTAR:
    # Landed on a star - Avoid that
    newS=bounceTo
    addOtherLine("Star bounce to:{:02o}:{:02o}".format(newQ,newS))
  if galaxy.sectors[newS]==SECTORENEMY:
    # Landed on an enemy - That's not good
    newS=bounceTo
    addOtherLine("Enemy bounce to:{:02o}:{:02o}".format(newQ,newS))   
  if galaxy.sectors[newS]==SECTOREMPTY:
    # Simple - nothing there.. so just move them in
    addOtherLine("Move to {:02o}:{:02o} complete.".format(newQ,newS))
  galaxy.currentS=newS
  status.energy-=status.moveEnergy
  status.starDate+=status.moveDays
  addOtherLine("Used:{:5.1f} Days {:4.1f} Power".format(status.moveDays,status.moveEnergy))
  # Note.. enemy might still fire.. but SB shields will need to protect them
  enemyMove(status.moveDays)
  enemyFire(False)
  updateStatus()      #update the status based on the new location
  return

# Move - pretty complicated
# Screen refresh isn't fast enough to use the buttons to change the coordinates
# So we do each digit separerately - put the value in binary in the neopixels
# And use the buttons to up/down forward/back and update the display when ever 
# they 'advance' and accept the value
def getMove():
  digits=[galaxy.currentQ>>3,galaxy.currentQ&0o07,galaxy.currentS>>3,galaxy.currentS&0o07]
  digitIdx=0
  cmdLabel.text=BUTTONLEN % "Warp"+BUTTONLEN % "+1"+BUTTONLEN % "-1"+BUTTONLEN % "Accept"
  while True:
    addOtherLine("{:} Current move to location is:\n{:1}{:1}:{:1}{:1}".format(status.theirTitle,digits[0],digits[1],digits[2],digits[3]))
    blinkIndex(digitIdx)
    thisOne=digits[digitIdx]
    theAns=getValue(thisOne,0,7)
    if theAns[0]==0:
      # GO! - take care of moving them to the new location
      addOtherLine("Requesting warp factor.")
      addOtherLine("To location :{:1}{:1}:{:1}{:1}. {:}?".format(digits[0],digits[1],digits[2],digits[3],status.theirTitle))
      cmdLabel.text=BUTTONLEN % "DoIt!"+BUTTONLEN % "+1"+BUTTONLEN % "-1"+BUTTONLEN % "Cancel"
      theAns=getValue(status.theShip[1],0,status.theShip[1])
      if theAns[0]==3:
        addOtherLine("Move Canceled.")
        wait2refresh()
        return
      newQ=(digits[0]<<3)+digits[1]
      newS=(digits[2]<<3)+digits[3]
      # Calculate energy and days here
      # Any bounces will not be far enough to make a difference
      dist=calcDistance(galaxy.currentQ, galaxy.currentS, newQ, newS)
      warp=theAns[1]
      status.moveEnergy=dist*(status.theShip[5]**warp)
      status.moveDays=daysOrDistance("days",dist,warp)
      # status.moveDays=dist*2.0/warp
      print ("Move-> Dist: {:} Energy: {:} Days: {:}".format (dist,status.moveEnergy,status.moveDays))
      if status.moveEnergy < status.energy:
        # NOTE: We start the 'other' comments here, since doMove might bounce to new coordinates
        addOtherLine("Move to: {:02o}:{:02o} At Warp:{:}\nEngaging! {:}".format(newQ,newS,warp,status.theirTitle))
        doMove(newQ,newS)
      else:
        addOtherLine("Insufficient power to move that far.")
        addOtherLine("Move Canceled. "+status.theirTitle)
        status.moveEnergy=0
        status.moveDays=0
      # wait2refresh()
      return
    else:
      # Next digit
      digits[digitIdx]=theAns[1]
      digitIdx+=1
      if digitIdx>3:
        digitIdx=0
      wait2refresh()

# Display the long range scan and also the status
def showLongScan():
  # First scan around our current quadrant
  # The &00717 blanks four any black hole
  for i in around(galaxy.currentQ):
    if i>=0:
      galaxy.knowns[i]="{0:03o}".format(galaxy.quadrants[i]&0o717)
  # Make sure to update the current quadrant too
  galaxy.knowns[galaxy.currentQ]="{0:03o}".format(galaxy.quadrants[galaxy.currentQ]&0o717)
  addOtherLine(" :*0*:*1*:*2*:*3*:*4*:*5*:*6*:*7*:")
  for i in range(8):
    j=i*8
    addOtherLine("{:}:{:}:".format(i,":".join(galaxy.knowns[j:j+8])))
 
# Move the enemy after their move.
# Enemy gets to move the same number of days at warp 4
# Enemy has 'infinate' energy - so always can move
def enemyMove(theDays):
  # Check to see if the invastion starts (but we only want to do this once :)
  if status.starDate>status.actualInvasion and status.actualInvasion>0.0:
    status.actualInvasion=0.0
    addOtherLine("{:}! The invasion has begun!".format(status.theirTitle))
    addOtherLine("The enemy swarm has arrived.")
    # We will need to use the current Q when we add enemy.  So we need to be able to restore it
    saveQ=galaxy.currentQ
    print ("Invasion Started")
    while len(galaxy.enemys)<MAXENEMY:
      # Get a quadrant - Note use of currentQ so we can fill the sector and make sure they aren't on a star
      galaxy.currentQ=random.randint(0,0o77)
      # Make sure that there is room (will most likely be true)
      # They CAN start in a SB now
      while galaxy.quadrants[galaxy.currentQ]>0o500:
        galaxy.currentQ=random.randint(0,0o77)
      galaxy.quadrants[galaxy.currentQ]+=0o100
      # Then find a free sector to put them in
      fillSectors(False)
      newS=random.randint(0,0o77)
      while galaxy.sectors[newS]!=SECTOREMPTY:
        newS=random.randint(0,0o77)
      galaxy.enemys.append((galaxy.currentQ<<6)+newS)
      # Enemy shields start at 200
      galaxy.enemyShields.append(200)
      i=len(galaxy.enemys)
      print("Enemy(%2i) at %4o" % (i,galaxy.enemys[i-1]))
    # Restore current Q
    galaxy.currentQ=saveQ
    status.enemyCnt=len(galaxy.enemys)
  # So we can check to see if we are in their quadrant already
  q=galaxy.currentQ<<6
  for idx in range(len(galaxy.enemys)):
    anEnemy=galaxy.enemys[idx]
    if anEnemy&0o7700 != q:
      # We only move if we are NOT in the current quadrant
      if status.enemyType>1:
        # Random move this time
        toq=random.randint(0,63)
      else:
        # Otherwise, we move towards the player
        toq=galaxy.currentQ
      # Ignore sectors for now (we will try to keep the sector the same)
      wantDist=calcDistance(anEnemy>>6,0,toq,0)
      # Enemy always moves at warp 4 (and we assume they always have enough power)
      canDist=daysOrDistance("Distance",theDays,4.0)
      tx=toq>>3
      ty=toq&0o7
      if wantDist>canDist:
        ratio=canDist/wantDist  # We need to adjust the x/y distance by this amount
        fx=anEnemy>>9
        fy=(anEnemy&0o0700)>>6
        qx=fx+round((tx-fx)*ratio)
        qy=fy+round((ty-fy)*ratio)
        toq=(qx<<3)+qy
      # If we actually changed quadrants we need to make sure they move to an empty sector
      if (anEnemy>>6) != toq:
        # Only do the move if there is room in the 'toq'
        # Max of 6 in any one quadrant (we could go 7, but 6 will be 'plenty'
        if galaxy.quadrants[toq]&0o700 < 0o500:
          # Need to save this so we can check for a free sector
          saveQ=galaxy.currentQ
          galaxy.currentQ=toq
          fillSectors(False)
          tos=anEnemy&0o77
          while galaxy.sectors[tos]!=SECTOREMPTY:
            tos=random.randint(0,63)
          galaxy.quadrants[toq]+=0o100
          galaxy.quadrants[anEnemy>>6]-=0o100
          galaxy.enemys[idx]=tos+(toq<<6)
          print("Ended: C:{:04o} F:{:04o} T:{:04o} W:{:}:{:}".format(q,anEnemy,galaxy.enemys[idx],tx,ty))
          # Restore current quadrant
          galaxy.currentQ=saveQ
  return

# Called when ever we want to give the enemy a chance to fire
# poked=true when the ship lands on an enemy or they fire on an ememy
# 0=They attack, least likely to shoot
# 1=They attack, more likely to shoot
# 2=They move random, least likely to shoot
# 3=They move random, most likely to shoot
def enemyFire(poked):
  if galaxy.quadrants[galaxy.currentQ]&0o700 ==0 :
    # Nobody enemy here.. so we are done
    return
  # Otherwise.. find the one/ones here
  q=galaxy.currentQ<<6
  fillSectors(True)
  for anEnemy in galaxy.enemys:
    if anEnemy&0o7700 == q:
      # Found one in this quadrant
      print("{:04o} {:04o}".format(anEnemy,q))
      odds=random.randint(0,100)
      # Everybody will fire if odds <25 or they got poked
      # The trigger happy enemy fire if the odds are <75
      # print("P/O/T",poked,odds,status.enemyType)
      if poked or odds<25 or ((status.enemyType==1 or status.enemyType==3) and odds<75):
        shotPoints=trackShot(anEnemy&0o77,galaxy.currentS)
        # Might need to reverse the list to get 'from' at 0
        if shotPoints[0]!=anEnemy&0o77:
          shotPoints.reverse()
        print(shotPoints)
        for aPoint in shotPoints:
          print("{:02o} {:}".format(aPoint,galaxy.sectors[aPoint]))
          if galaxy.sectors[aPoint]!=SECTOREMPTY:
            if galaxy.sectors[aPoint]==SECTORDOCKED:
              print("They hit a starbase")
              # Starbase shields protect from all enemy fire (at least for now)
              addOtherLine("Starbase deflected shot from {:02o}".format(shotPoints[0]))
              continue
            elif galaxy.sectors[aPoint]==SECTORME:
              print("They hit the ship")
              fy=galaxy.currentS>>3
              fx=galaxy.currentS&0o07
              ty=shotPoints[0]>>3
              tx=shotPoints[0]&0o07
              dist=(((fx-tx)**2)+((fy-ty)**2))**0.5
              power=galaxy.enemyPhaser
              power=power-0.5*(power-power/dist)
              addOtherLine("{:6.1f} hit from enemy at {:02o}".format(power,shotPoints[0]))
              if power>=status.shields:
                addOtherLine("SHIP DESTROYED!")
                addOtherLine("ALL HANDS ABANDON SHIP!")
                magtag.peripherals.play_tone(2093, 0.10)  # SOS
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.10)
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.10)
                time.sleep(0.2)
                magtag.peripherals.play_tone(2093, 0.20)
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.20)
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.20)
                time.sleep(0.2)
                magtag.peripherals.play_tone(2093, 0.10)
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.10)
                time.sleep(0.1)
                magtag.peripherals.play_tone(2093, 0.10)
                updateStatus()
                getButtonCommand(["Restart"],"","")
                supervisor.reload()
                # 'technically' this return will never get executed
                return
              status.shields-=power
              addOtherLine("Shields down to {:6.1f}".format(status.shields))
              continue
            elif aPoint==anEnemy&0o77:
              # Skip 'me'
              continue
            else:
              # Must have been a star, blackhole, or another enemy
              break
  return
  
###############################################
# Various 'helper' functions
###############################################

# value to lights
def value2lights(digit):
  magtag.peripherals.neopixels.fill((0,0,0))
  if digit&1==1:
    magtag.peripherals.neopixels[0]=(255,255,255)
  if digit&2==2:
    magtag.peripherals.neopixels[1]=(255,255,255)
  if digit&4==4:
    magtag.peripherals.neopixels[2]=(255,255,255)
  if digit&8==8:
    magtag.peripherals.neopixels[3]=(255,255,255)
    
# Blink the position they are changing red for a second
# [0] is the right most neopixel
def blinkIndex(x):
  magtag.peripherals.neopixel_disable = False
  magtag.peripherals.neopixels.fill((0,0,0))
  for i in range(5):
    magtag.peripherals.neopixels[3-x]=(128,0,0)
    time.sleep(0.1)
    magtag.peripherals.neopixels[3-x]=(0,0,0)
    time.sleep(0.1)
  
# getValue - generic get a value via the buttons
# The current value is displayed in the top LEDs, and the buttons change the value
# 'B' adds 1
# 'C' subtracts 1
# 'A' and 'D' return a tuple (button(0,4), value)
def getValue (value,min,max):
  wait2refresh()
  thisOne=value
  value2lights(thisOne)
  while True:
    if magtag.peripherals.button_a_pressed:
      while magtag.peripherals.button_a_pressed: time.sleep(0.01)
      magtag.peripherals.neopixels.fill((0,0,0))
      return (0,thisOne)
    if magtag.peripherals.button_b_pressed:
      # +1
      thisOne+=1
      # magtag.peripherals.play_tone(2093, 0.10)
      if thisOne>max:
        thisOne=max
      value2lights(thisOne)
      while magtag.peripherals.button_b_pressed: time.sleep(0.01)
    if magtag.peripherals.button_c_pressed:
      # -1
      thisOne-=1
      # magtag.peripherals.play_tone(1047, 0.10)
      if thisOne<min:
        thisOne=min
      value2lights(thisOne)
      while magtag.peripherals.button_c_pressed: time.sleep(0.01)
    if magtag.peripherals.button_d_pressed:
      while magtag.peripherals.button_d_pressed: time.sleep(0.01)
      magtag.peripherals.neopixels.fill((0,0,0))
      return (3,thisOne)

# Calculate either the days traveled for a distance
# Or the distance traveled for a number of days
# This really didn't need to be a function, but it keeps the formula in one place
def daysOrDistance(dod, theValue, warp):
  if dod=="days":
    # return theValue/(warp*5.0)
    return theValue/(warp)
  else:
    # return theValue*5.0*warp
    return theValue*warp
  # days=((dist*2.0)/warp)/10.0
  # days*10=(dist*2.0)/warp
  # days*10*warp=dist*2.0
  # days*10*warp/2.0=dist
  # dist=days*10.0*warp/2.0
  # dist/days=10.0*warp/2.0
  # 1/days=(5.0*warp)/dist
  # days = dist/(warp*5.0)
  
# The e-Ink needs to wait before a refresh
def wait2refresh():
  if len(status.otherLines)>0:
    # Collect all the 'other' lines we have been given
    otherLabel.text="\n".join(status.otherLines)
    # We have shown all these
    status.otherLines=[]
  # Otherwise, we leave what ever was there in
  whichLED=0
  counter=0
  #magtag.peripherals.neopixels.fill((0,0,0))
  #magtag.peripherals.neopixels[whichLED]=(255,0,0)
  while board.DISPLAY.time_to_refresh>0.0:
    counter+=1
    if counter>1000:
      #magtag.peripherals.neopixels[whichLED]=(0,0,0)
      whichLED=(whichLED+1)&3
      #magtag.peripherals.neopixels[whichLED]=(255,0,0)
      counter=0
  #magtag.peripherals.neopixels[whichLED]=(0,0,0)
  board.DISPLAY.refresh()
  
# Calculate distance (in sectors) between two points
def calcDistance(tq,ts,fq,fs):
  # We do the calculations in sectors
  x=(((fq&0o07)-(tq&0o07))<<3)+(fs&0o7)-(ts&0o7)
  y=((fq&0o70)-(tq&0o70))+(((fs&0o70)-(ts&0o70))>>3)
  dist=((x**2)+(y**2))**0.5
  # print("Distance: {:} From: {:02o}:{:02o} To: {:02o}:{:02o}".format(dist,fq,fs,tq,ts))
  return dist
  
# Pick the player's title (Sir/Madam) from the list - returns the index
def getTitle():
  addOtherLine("How should I address you?")
  ans=getButtonCommand(["Sir","Madam"],"","")
  return ans[1]

# Pick the player's ship from the list
def getShip():
  theShips=(("Scout",15,2000,7,6,1.18),("Cruiser",8,3000,10,4,1.40),("Battleship",4,6000,20,5,1.96))
  ans=(0,"")
  while ans[1] != "Select":
    addOtherLine("Which Ship would you like? {:}".format(status.theirTitle))
    ans=getButtonCommand(["Scout","Cruiser","Battleship"],"","")
    thisShip=ans[0]
    addOtherLine("Select this ship? {:}".format(status.theirTitle))
    addOtherLine("\
Type    : {:>10}\n\
Warp    : {:10}\n\
Power   : {:10}\n\
Torpedos: {:10}\n\
Trackers: {:10}".format(theShips[thisShip][0],theShips[thisShip][1],theShips[thisShip][2],theShips[thisShip][3],theShips[thisShip][4]))
    ans=getButtonCommand(["Select","Go back"],"","")    
  return theShips[thisShip]
  
# Around - returns a list with the coordinates 'around' a give coordinate
# -1 if that coordinate is not valid (off the edge) 
def around(X):
  # 0 1 2
  # 3 x 4
  # 5 6 7
  # Frist assume everything ok
  ans=[0]*8
  ans[0]=X-9    # -0o11
  ans[1]=X-8    # -0o10
  ans[2]=X-7    # -0o10+0o01
  ans[3]=X-1    # -0o01
  ans[4]=X+1    # +0o01
  ans[5]=X+7    # +0o10-0o01
  ans[6]=X+8    # +0o10
  ans[7]=X+9    # +0o11
  r=X>>3
  if r==0:
    ans[0]=ans[1]=ans[2]=-1
  if r==7:
    ans[5]=ans[6]=ans[7]=-1
  c=X&0O7
  if c==0:
    ans[0]=ans[3]=ans[5]=-1
  if c==7:
    ans[2]=ans[4]=ans[7]=-1
  return ans

def addOtherLine(aLine):
  # Make sure there is room for this line
  if len(status.otherLines)>8:
    # Nope-display what we have
    # NOTE: wait2refresh will join all the current stuff in otherLines
    getButtonCommand(["OK"],"","")
  status.otherLines.append(aLine)
    
###############################################################
# Initial setup
###############################################################
# Enemy type
#0=They attack, least likely to shoot
#1=They attack, more likely to shoot
#2=They move random, least likely to shoot
#3=They move random, most likely to shoot
status.enemyType=random.randint(0,4)

# Let's see how many bad guys we have (>9 less than 26)
status.origEnemy=random.randint(9,MAXENEMY)
status.enemyCnt=status.origEnemy
status.starDate=2000.0+100.0*random.random()
status.origDate=status.starDate
status.actualInvasion=status.starDate+(1.0+float(MAXENEMY-status.enemyCnt)/MAXENEMY)*status.enemyCnt+(15.0*random.random())
i=random.randint(0,100) & 1
if i==0:
  i=-1
status.estInvasion=status.actualInvasion+float(i*random.randint(0,10))
print("Stardate,Actual,Estimated",status.starDate,status.actualInvasion,status.estInvasion)

# We save the randum number galaxy.seeds for each quadrant, so the sector looks the same (stars and bases)
for i in range(64):
  # create a random seed to be used when we fill the quadrant
  galaxy.seeds[i]=random.randint(0,2000)
  # then decide how many stars in this quadrant (at least 1, max of 7)
  galaxy.quadrants[i]=random.randint(1,7)

# Now pick a few black holes
# We don't need to worry about which sector, since that will be done
# when the sector is filled, and black holes never 'move'
origHoles=random.randint(0,5)
for i in range(origHoles):
  q=random.randint(0,0o77)
  # Pick a quadrant that doesn't have any blackholes already
  while (galaxy.quadrants[q]&0o20)!=0:
    q=random.randint(0,0o77)
  galaxy.quadrants[q]+=0o20

# Place the bases into quadrants
status.origBases=random.randint(1,MAXSTARBASES+1)
status.basesCnt=status.origBases
for i in range(status.origBases):
  q=random.randint(0,0o77)
  # Make sure not another starbase in that quadrant
  while galaxy.quadrants[q] & 0o710 != 0:
    q=random.randint(0,0o77)
  # Nothing but stars here sir - good place for a base
  # We will compute the 'exact' location in fillSector since these don't move
  galaxy.quadrants[q]+=0o10
  print("Base(%2i) at %2o with %3o" % (i,q,galaxy.quadrants[q]))

# Now populate the enemy locations
# Need to use a while loop because we need to generate unique locations for each enemy
while i<status.origEnemy:
  # Get a quadrant - Note use of currentQ so we can fill the sector and make sure they aren't on a star
  galaxy.currentQ=random.randint(0,0o77)
  # Make sure that there is room (will most likely be true)
  # Also, don't start them in with a starbase.
  while galaxy.quadrants[galaxy.currentQ]>0o500 or (galaxy.quadrants[galaxy.currentQ]&0o10)>0:
    galaxy.currentQ=random.randint(0,0o77)
  galaxy.quadrants[galaxy.currentQ]+=0o100
  # Then find a free sector to put them in
  fillSectors(False)
  galaxy.currentS=random.randint(0,0o77)
  while galaxy.sectors[galaxy.currentS]!=SECTOREMPTY:
    galaxy.currentS=random.randint(0,0o77)
  galaxy.enemys.append((galaxy.currentQ<<6)+galaxy.currentS)
  # Enemy shields start at 200
  galaxy.enemyShields.append(200)
  i=len(galaxy.enemys)
  print("Enemy(%2i) at %4o" % (i,galaxy.enemys[i-1]))
status.daysPerEnemy=(status.actualInvasion-status.origDate-1)/status.origEnemy
status.enemyCnt=len(galaxy.enemys)

# Now we need to start them off at a Starbase
galaxy.currentQ=random.randint(0,0o77)
while (galaxy.quadrants[galaxy.currentQ]&0o10)!=0o10:
  galaxy.currentQ=random.randint(0,0o77)
print ("Initial at Starbase",galaxy.currentQ)
# OR - make sure the don't start with enemy or starbase (make them work)
# galaxy.currentQ=random.randint(0,0o77)
# while (galaxy.quadrants[galaxy.currentQ]&0710)!=0:
#   galaxy.currentQ=random.randint(0,0o77)
# print ("Random Starbase",galaxy.currentQ)

# Fill the galaxy.sectors so that we can dock them with the starbase
# NOTE: We already know there aren't any status.enemy there...
# Just need to avoid stars and blackholes
# NOTE: If we are doing the random starting location, 
# we just won't find the SB
fillSectors(False)
for idx in range(len(galaxy.sectors)):
  if galaxy.sectors[idx]==SECTORSB:
    galaxy.currentS=idx
    break
# TESTING - find us a quadrant with enemy so we can test firing
for q in range(64):
  if galaxy.quadrants[q]&0o700 > 0o100:
    galaxy.currentQ=q
    print ("More than 1",galaxy.currentQ,galaxy.quadrants[q]&0o700)
    break
  elif galaxy.quadrants[q]&0o700 > 0:
    galaxy.currentQ=q
    print ("At least 1",galaxy.currentQ)
# Find an empty sector to start off in (since we are going to be docked)
fillSectors(False)
galaxy.currentS=random.randint(0,0O77)
while galaxy.sectors[galaxy.currentS]!=SECTOREMPTY:
  galaxy.currentS=random.randint(0,0O77)
# So we can test the invasion code
status.actualInvasion=status.origDate+6.0
# TESTING end
  
# They always 'know' the quadrant where they start
galaxy.knowns=["   "]*64
galaxy.knowns[galaxy.currentQ]="{0:03o}".format(galaxy.quadrants[galaxy.currentQ]&0o717)

gc.collect()

# https://mkennedy.codes/posts/python-gc-settings-change-this-and-make-your-app-go-20pc-faster/
# Will try various less drastic setting initially

# Clean up what might be garbage so far.
# gc.collect(2)
# Exclude current items from future GC.
# gc.freeze()

# allocs, gen1, gen2 = gc.get_threshold()
# allocs = 50_000  # Start the GC sequence every 50K not 700 allocations.
# allocs = 10000  # not 700 allocations.
# gen1 = gen1 * 2
# gen2 = gen2 * 2
# gc.set_threshold(allocs, gen1, gen2)
print("Free memory:{}".format(gc.mem_free()))
addOtherLine("Would you like to see instructions?")
ans=getButtonCommand(["Yes","No"],"","")
print(ans)
if ans[1]=="Yes":
  fp=open("/Instructions.txt", "r")
  while True:
    aLine = fp.readline()
    # if line is empty - end of file (because it returns the /n for a blank line
    if not aLine:
      if len(status.otherLines)>0:
        getButtonCommand(["Done"],"","")
      break
    # Make sure there is room for this line
    if len(status.otherLines)>8:
      # Nope-display what we have
      # NOTE: wait2refresh will join all the current stuff in otherLines
      getButtonCommand(["More","Cancel"],"","")
    status.otherLines.append(aLine.strip())
  fp.close()

status.theirTitle=getTitle()
print(status.theirTitle)
# Ship type, speed (1/speed = starDates per quadrant), max energy, photons, trackers, energy/stardate
status.theShip=getShip()
print(status.theShip)
# Initialize the 'current' values (maxs will remain with theShip)
status.energy=status.theShip[2]
status.photons=status.theShip[3]
status.trackers=[-1]*status.theShip[4]
# Start them out with a short scan
showShortScan()
updateStatus()

getCommand()
