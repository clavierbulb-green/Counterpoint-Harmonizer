import music21

import random
import sys

CONSONANCES = [1, 3, 5, 6, 8]

MELODIC_CONSONANCES = ['P1', 'm2', 'M2', 'm3', 'M3', 'P4', 'P5', 'm6', 'P8']


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


def chooseNextCounterpoint(currentGround, nextGround, nextCPoint, key):

    # counterpoint should leap no more than an 8ve
    possibleNextPitches = key.getPitches(
                minPitch=nextCPoint.pitch.transpose('-P8'),
                maxPitch=nextCPoint.pitch.transpose('P8')
            )

    consonantLegalNextPitches = []

    for p in possibleNextPitches:
        currentCPoint = music21.note.Note(pitch=p)
        vlq = music21.voiceLeading.VoiceLeadingQuartet(
                v1n1=currentCPoint,
                v1n2=nextCPoint,
                v2n1=currentGround,
                v2n2=nextGround
              )
        if vlq.hIntervals[0].name not in MELODIC_CONSONANCES:
            continue

        # minor 6ths only allowed ascending
        if vlq.hIntervals[0].directedName == 'm-6':
            continue

        if not vlq.vIntervals[0].isConsonant():
            continue

        if vlq.vIntervals[0].name == 'P1':
            continue

        if vlq.parallelUnisonOrOctave() or vlq.parallelFifth():
            continue

        if vlq.hiddenFifth() or vlq.hiddenOctave():
            continue

        # allow occassional voice crossing

        #if vlq.voiceCrossing():
            #continue

        consonantLegalNextPitches.append(p)

    try:
        currentCPointPitch = random.choice(consonantLegalNextPitches)
    except IndexError:
        print('No legal pitches to harmonize CF found!')
        print('currentG:', currentGround.nameWithOctave)
        print('nextG:', nextGround.nameWithOctave)
        print('nextCP:', nextCPoint.nameWithOctave)
        sys.exit()

    return currentCPointPitch


def harmonizeReverse(ground):
    counterpoint = ground.template(fillWithRests=False)
    key = ground.analyze('key.krumhanslschmuckler')

    groundNotes = list(ground.recurse().notes)
    groundNotes.reverse()
    for currentGround in groundNotes:
        currentCPoint = music21.note.Note()
        currentCPoint.quarterLength = currentGround.quarterLength 
        counterpoint.measure(currentGround.measureNumber).insert(
            currentGround.offset, currentCPoint) 

        # last note in counterpoint should be a P8
        if len(list(counterpoint.recurse().notes)) == 1:
            currentCPoint.pitch = chooseRandomHarmonizingPitch(
                    currentGround.pitch, key, intervalFilterList=[8]
                    )

        # penultimate note should be a M6
        elif len(list(counterpoint.recurse().notes)) == 2:
            currentCPoint.pitch = chooseRandomHarmonizingPitch(
                    currentGround.pitch, key, intervalFilterList=[6]
                    )
            currentCPoint.pitch.transpose(1, inPlace=True)

        else:
            nextGround = currentGround.next(className='Note')
            nextCPoint = currentCPoint.next(className='Note')
            
            ambitus = music21.interval.Interval('m13')

            while ambitus.semitones >= 20:
                currentCPoint.pitch = chooseNextCounterpoint(
                        currentGround, nextGround, nextCPoint, key)
                ambitus = counterpoint.analyze('ambitus')


    # set clef so notes are centered on staff
    measure_1 = counterpoint.recurse().getElementsByClass('Measure')[0]
    measure_1.clef = music21.clef.bestClef(counterpoint.flat)

    return counterpoint


def main():
    ground = music21.converter.parse('tinynotation: 4/4 D1 F E D G F A G F E D')
    counterpoint = harmonizeReverse(ground)
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
