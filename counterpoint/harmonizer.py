import music21

import random

CONSONANTS = [1, 3, 5, 6, 8]


def chooseRandomHarmonizingPitch(basePitch, key):
    ''' Return a pitch that harmonizes a given pitch'''

    intervalNum = random.choice(CONSONANTS)
    gi = music21.interval.GenericInterval(intervalNum)
    newPitch = gi.transposePitchKeyAware(basePitch, key)

    return newPitch


def chooseNextCounterpoint(prevGround, currentGround, prevCPoint, key):

    # counterpoint should leap no more than an 8ve
    possibleNextPitches = key.getPitches(
                minPitch=prevCPoint.pitch.transpose('-P8'),
                maxPitch=prevCPoint.pitch.transpose('P8')
            )

    consonantLegalNextPitches = []

    for p in possibleNextPitches:
        nextCPoint = music21.note.Note(pitch=p)
        vlq = music21.voiceLeading.VoiceLeadingQuartet(
                v1n1=prevCPoint,
                v1n2=nextCPoint,
                v2n1=prevGround,
                v2n2=currentGround
              )
        if not vlq.vIntervals[1].isConsonant():
            continue

        if vlq.parallelUnisonOrOctave() or vlq.parallelFifth():
            continue

        if vlq.hiddenFifth() or vlq.hiddenOctave():
            continue

        if vlq.voiceCrossing():
            continue

        consonantLegalNextPitches.append(p)

    return random.choice(consonantLegalNextPitches)


def createCounterpoint(ground, upper=True):
    counterpoint = ground.template(fillWithRests=False)
    counterpoint.id='Counterpoint'
    key = ground.analyze('key.krumhanslschmuckler')

    for n in ground.recurse().notes:
        # first note
        if len(list(counterpoint.recurse().notes)) == 0:
            nextCPoint = music21.note.Note(quarterLength=n.quarterLength) 
            nextCPoint.pitch = chooseRandomHarmonizingPitch(n.pitch, key)
            counterpoint.measure(n.measureNumber).insert(n.offset, nextCPoint) 
            continue

        

        # insert dummy note as next counterpoint
        nextCPoint = music21.note.Note(quarterLength=n.quarterLength) 
        counterpoint.measure(n.measureNumber).insert(n.offset, nextCPoint) 

        prevGround = n.previous(className='Note')
        prevCPoint = nextCPoint.previous(className='Note')

        ambitus = music21.interval.Interval('P12')
        # get actual pitch of next counterpoint
        while ambitus.semitones >= 19:
            nextPitch = chooseNextCounterpoint(
                    prevGround, n, prevCPoint, key)
            nextCPoint.pitch = nextPitch
            ambitus = counterpoint.analyze('ambitus')

        #print(ambitus)


    # set clef so notes are centered on staff
    measure_1 = counterpoint.recurse().getElementsByClass('Measure')[0]
    measure_1.clef = music21.clef.bestClef(counterpoint.flat)

    return counterpoint


def main():
    ground = music21.converter.parse('tinynotation: 4/4 D1 F E D G F A G F E D')
    counterpoint = createCounterpoint(ground)

    display = music21.stream.Score(id='Display')
    display.insert(0, counterpoint)
    display.insert(0, ground)


    reduction = display.partsToVoices().chordify()
    for c in reduction.recurse().getElementsByClass('Chord'):
        c.annotateIntervals()

    display.insert(0, reduction)
    display.show()


if __name__ == "__main__":
    main()
