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


def chooseNextCounterpoint(prevCPoint, prevGround, currentGround, key):

    # counterpoint should leap no more than an 8ve
    possibleNextPitches = key.getPitches(
                minPitch=prevCPoint.pitch.transpose('-P8'),
                maxPitch=prevCPoint.pitch.transpose('P8')
            )

    consonantLegalNextPitches = []

    for p in possibleNextPitches:
        currentCPoint = music21.note.Note(pitch=p)
        vlq = music21.voiceLeading.VoiceLeadingQuartet(
                v1n1=prevCPoint,
                v1n2=currentCPoint,
                v2n1=prevGround,
                v2n2=currentGround
              )

        # counterpoint should move by a melodic consonance
        # TODO: currently assumes counterpoint is in the upper voice
        if vlq.hIntervals[0].name not in MELODIC_CONSONANCES:
            continue

        # minor 6ths only allowed ascending
        if vlq.hIntervals[0].directedName == 'm-6':
            continue

        if not vlq.vIntervals[1].isConsonant():
            continue

        # the unison(P1) is forbidden in first species counterpoint
        if vlq.vIntervals[1].name == 'P1':
            continue

        if vlq.parallelUnisonOrOctave() or vlq.parallelFifth():
            continue

        if vlq.hiddenFifth() or vlq.hiddenOctave():
            continue

        # both parts should not skip into a perfect consonance
        if all([i.isSkip for i in vlq.hIntervals]) and  \
                vlq.vIntervals[1].name in ('P8', 'P5'):
            continue

        consonantLegalNextPitches.append(p)

    try:
        currentCPointPitch = random.choice(consonantLegalNextPitches)
    except IndexError:
        print('No legal pitches to harmonize CF found!')
        print('previous note in CPoint:', prevCPoint.nameWithOctave)
        print('previous note in CF:', prevGround.nameWithOctave)
        print('current note in CF:', currentGround.nameWithOctave)
        sys.exit()

    return currentCPointPitch


def harmonize(ground):
    counterpoint = ground.template(fillWithRests=False)
    key = ground.analyze('key.krumhanslschmuckler')

    groundNotes = list(ground.recurse().notes)
    
    #groundNotes.reverse()
    for currentGround in groundNotes:
        # make a note to harmonize the current note in the cantus firmus
        # (currently only 1:1)
        currentCPoint = music21.note.Note()
        currentCPoint.quarterLength = currentGround.quarterLength 
        counterpoint.measure(currentGround.measureNumber).insert(
            currentGround.offset, currentCPoint) 


        # first note in counterpoint should be a P5 or P8
        if len(list(counterpoint.recurse().notes)) == 1:
            currentCPoint.pitch = chooseRandomHarmonizingPitch(
                    currentGround.pitch, key, intervalFilterList=[5, 8]
                    )

        # TODO leading tone should be approached either by step or by
        # descending third

        # penultimate note should be a M6 (leading tone)
        elif len(list(counterpoint.recurse().notes)) == len(groundNotes)-1:
            currentCPoint.pitch = chooseRandomHarmonizingPitch(
                    currentGround.pitch, key, intervalFilterList=[6]
                    )
            currentCPoint.pitch.transpose(1, inPlace=True)

        # last note in counterpoint should be a P8
        elif len(list(counterpoint.recurse().notes)) == len(groundNotes):
            currentCPoint.pitch = chooseRandomHarmonizingPitch(
                    currentGround.pitch, key, intervalFilterList=[8]
                    )
        # all other notes should be consonant with the cantus firmus
        else:
            prevGround = currentGround.previous(className='Note')
            prevCPoint = currentCPoint.previous(className='Note')
            
            ambitus = music21.interval.Interval('m13')

            while ambitus.semitones >= 20:
                currentCPoint.pitch = chooseNextCounterpoint(
                        prevCPoint, prevGround, currentGround, key)
                ambitus = counterpoint.analyze('ambitus')


    # set clef so notes are centered on staff
    measure_1 = counterpoint.recurse().getElementsByClass('Measure')[0]
    measure_1.clef = music21.clef.bestClef(counterpoint.flat)

    return counterpoint


def main():
    ground = music21.converter.parse('tinynotation: 4/4 D1 F E D G F A G F E D')
    counterpoint = harmonize(ground)
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
