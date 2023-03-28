# Space War - Magtag
I origionally wrote a version of this in BASIC to run on a GE265 Timer Sharing
computer (approximately 8K core memory), over 50 years ago. It was completely text based, 
designed to run a teletype for input and output.

Unfortunately, my comments in the code did not give credit to the origional author.
I suspect that the original was on a Dartmouth tape that came with the GE265.

I make no claims that this is a 'port', or 'conversion' of that BASIC program.  
That program was a convoluted mess of GOTOs and GOSUBs.  About all I actually
saved were the instructions and the program flow.

The Magtag is actually much more powerful than that GE265 so I wasn't worried about
the program size.  There are two issues that I had to spend most of my time on.

1) There is no keyboard on the Magtag.  Just 4 buttons.  So "typing in" a command
was out of the question.  And if one button is used for "Next" and one for "Cancel"
that meant only two left for commands.

2) The second issue was the eInk display.  More specifically, the refresh rate is
approximately 3 seconds between changes.  So you really can't give feedback when
a button is pressed.  This was a real challenge when the commander needed to enter
a four digit coordinate to warp to.

There are addon's that could easily attach to the Magtag to address these.  But 
I wanted to be able to play it on a "stock" Magtag with no additional components.
I think it turned out pretty good.


