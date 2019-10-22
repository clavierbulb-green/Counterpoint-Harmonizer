import music21

import random

CONSONANCES = [1, 3, 5, 6, 8]


def chooseRandomHarmonizingPitch(basePitch, key, intervalFilterList=None):
    ''' Return a pitch that harmonizes a given pitch'''

    if intervalFilterList:
        consonances = list(filter(
            lambda i: i in CONSONANCES, intervalFilterList)
            )
        if len(consonances) != 0:
            intervalNum = random.choice(consonances)
        else:
            return # TODO raise exception if no consonances in filter list?
    else:
        intervalNum = random.choice(CONSONANCES)

    # fifths should always be perfect (no diminished fifths allowed!)
    if intervalNum == 5:
        return basePitch.transpose('P5')

    gi = music21.interval.GenericInterval(intervalNum)
    harmonizingPitch = gi.transposePitchKeyAware(basePitch, key)

    return harmonizingPitch


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
    #counterpoint.id='Counterpoint'

    key = ground.analyze('key.krumhanslschmuckler')

    for n in ground.recurse().notes:
        # first note in counterpoint should be a perfect consonance 
        if len(list(counterpoint.recurse().notes)) == 0:
            nextCPoint = music21.note.Note()
            nextCPoint.quarterLength = n.quarterLength 
            nextCPoint.pitch = chooseRandomHarmonizingPitch(
                    n.pitch, key, intervalFilterList=[5, 8]
                    )

            counterpoint.measure(n.measureNumber).insert(
                    n.offset, nextCPoint
                    ) 
            continue


        # insert dummy note as next note in counterpoint
        nextCPoint = music21.note.Note()
        nextCPoint.quarterLength = n.quarterLength
        counterpoint.measure(n.measureNumber).insert(n.offset, nextCPoint) 

        prevGround = n.previous(className='Note')
        prevCPoint = nextCPoint.previous(className='Note')

        ambitus = music21.interval.Interval('P12')
        # get actual pitch of next counterpoint
        while ambitus.semitones >= 16: # ambitus should not exceed M10
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
