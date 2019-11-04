import music21

import random
import sys

from enum import Enum

# ========== CONSTANTS ========== #

CONSONANCES = [1, 3, 5, 6, 8]

MELODIC_CONSONANCES = ['P1', 'm2', 'M2', 'm3', 'M3', 'P4', 'P5', 'm6', 'P8']

class Mode(Enum):
    D = 'DORIAN'
    E = 'PHRYGIAN'
    F = 'LYDIAN'
    G = 'MIXOLYDIAN'
    A = 'AEOLIAN'
    C = 'IONIAN'
    
    def as_key(self):
        return music21.key.Key(self.name, self.value)


class VoiceRange(Enum):
    SOPRANO = ('C4', 'E5')
    ALTO = ('F3', 'A4')
    TENOR = ('C3', 'E4')
    BASS = ('F2', 'A3')

    def as_pitches(self):
        '''Realize the lower/upper bounds of the voice range as pitches'''

        return tuple([music21.pitch.Pitch(p) for p in self.value])


# ========== CLASSES========== #

class Melody():

    def __init__(self, voice_type, final):

        self.voice_range = VoiceRange[voice_type.upper()]
        self.voice_type = self.voice_range.name

        self.pitch_range = self.voice_range.as_pitches()
        self.range_min = self.pitch_range[0]
        self.range_max = self.pitch_range[1]
        
        self.mode = Mode[final.upper()]

        self.intervals = []
        self.notes = []

    def pitch_in_voice_range(self, pitch):
        '''Return whether a given pitch is within the voice range of
        this Melody'''

        return pitch >= self.range_min and pitch <= self.range_max

    def append_note(self, note):
        '''Adds a Note to the Melody, and records the Interval the
        Melody moves to reach the new Note'''

        if not self.pitch_in_voice_range(note.pitch):
            raise ValueError('Attempt to add note with pitch out of bounds of voice range')

        if self.notes:
            prev_note = self.notes[len(self.notes) - 1]
            melodic_interval = music21.interval.Interval(prev_note, note)
            self.intervals.append(melodic_interval)

        self.notes.append(note)

    def realize(self):
        '''Returns a music21.stream.Part realization of this Melody'''
        
        part = music21.stream.Part()
        for n in self.notes:
            part.append(n)

        part.makeNotation(bestClef=True)
        return part


class CantusFirmus(Melody):

    def __init__(self, voice_type, mode):
        super().__init__(voice_type, mode)

    def generate(self):
        pass


class Counterpoint(Melody):
    pass


def choose_random_harmonizing_pitch(base_pitch, 
                                    key, 
                                    interval_filter_list=None
                                    ):
    ''' Return a pitch that harmonizes a given pitch'''

    if interval_filter_list:
        consonances = list(filter(
            lambda i: i in CONSONANCES, interval_filter_list)
            )
        if len(consonances) != 0:
            interval_num = random.choice(consonances)
        else:
            return # TODO raise exception if no consonances in filter list?
    else:
        interval_num = random.choice(CONSONANCES)

    # fifths should always be perfect (no diminished fifths allowed!)
    if interval_num == 5:
        return base_pitch.transpose('P5')

    gi = music21.interval.GenericInterval(interval_num)
    harmonizing_pitch = gi.transposePitchKeyAware(base_pitch, key)

    return harmonizing_pitch


def choose_next_counterpoint(prev_cpoint, prev_cf, current_cf, key):

    # cpoint should leap no more than an 8ve
    possible_next_pitches = key.getPitches(
                minPitch=prev_cpoint.pitch.transpose('-P8'),
                maxPitch=prev_cpoint.pitch.transpose('P8')
            )

    consonant_legal_next_pitches = []

    for p in possible_next_pitches:
        current_cpoint = music21.note.Note(pitch=p)
        vlq = music21.voiceLeading.VoiceLeadingQuartet(
                v1n1=prev_cpoint,
                v1n2=current_cpoint,
                v2n1=prev_cf,
                v2n2=current_cf
              )

        # cpoint should move by a melodic consonance
        # TODO: currently assumes cpoint is in the upper voice
        if vlq.hIntervals[0].name not in MELODIC_CONSONANCES:
            continue

        # minor 6ths only allowed ascending
        if vlq.hIntervals[0].directedName == 'm-6':
            continue

        if not vlq.vIntervals[1].isConsonant():
            continue

        # the unison(P1) is forbidden in first species cpoint
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

        consonant_legal_next_pitches.append(p)

    try:
        current_cpointPitch = random.choice(consonant_legal_next_pitches)
    except IndexError:
        print('No legal pitches to harmonize CF found!')
        print('previous note in CPoint:', prev_cpoint.nameWithOctave)
        print('previous note in CF:', prev_cf.nameWithOctave)
        print('current note in CF:', current_cf.nameWithOctave)
        sys.exit()

    return current_cpointPitch


def harmonize(cf, modal=True):
    cpoint = cf.template(fillWithRests=False)
    cf_notes = list(cf.recurse().notes)
    
    if modal:
        # assume the last note of a cantus firmus is the final of the mode
        final = cf_notes[len(cf_notes)-1].name
        key = Mode[final].as_key()
    else:
        key = cf.analyze('key.krumhanslschmuckler')

    for current_cf in cf_notes:

        # make a note to harmonize the current note in the cantus firmus
        # (currently only 1:1)
        current_cpoint = music21.note.Note()
        current_cpoint.quarterLength = current_cf.quarterLength 
        cpoint.measure(current_cf.measureNumber).insert(
            current_cf.offset, current_cpoint) 

        # first note in cpoint should be a P5 or P8
        if len(list(cpoint.recurse().notes)) == 1:
            current_cpoint.pitch = choose_random_harmonizing_pitch(
                    current_cf.pitch, key, interval_filter_list=[5, 8]
                    )

        # TODO leading tone should be approached either by step or by
        # descending third

        # penultimate note should be a M6 (leading tone)
        elif len(list(cpoint.recurse().notes)) == len(cf_notes)-1:
            current_cpoint.pitch = choose_random_harmonizing_pitch(
                    current_cf.pitch, key, interval_filter_list=[6]
                    )
            current_cpoint.pitch.transpose(1, inPlace=True)

        # last note in cpoint should be a P8
        elif len(list(cpoint.recurse().notes)) == len(cf_notes):
            current_cpoint.pitch = choose_random_harmonizing_pitch(
                    current_cf.pitch, key, interval_filter_list=[8]
                    )
        # all other notes should be consonant with the cantus firmus
        else:
            prev_cf = current_cf.previous(className='Note')
            prev_cpoint = current_cpoint.previous(className='Note')
            
            ambitus = music21.interval.Interval('m13')

            while ambitus.semitones >= 20:
                current_cpoint.pitch = choose_next_counterpoint(
                        prev_cpoint, prev_cf, current_cf, key)
                ambitus = cpoint.analyze('ambitus')

    # set clef so notes are centered on staff
    measure_1 = cpoint.recurse().getElementsByClass('Measure')[0]
    measure_1.clef = music21.clef.bestClef(cpoint.flat)

    return cpoint


def main():
    cf = music21.converter.parse('tinynotation: 4/4 D1 F E D G F A G F E D')
    cpoint = harmonize(cf)
    display = music21.stream.Score(id='Display')
    display.insert(0, cpoint)
    display.insert(0, cf)

    reduction = display.partsToVoices().chordify()
    for c in reduction.recurse().getElementsByClass('Chord'):
        c.annotateIntervals()

    display.insert(0, reduction)
    #display.show()


if __name__ == "__main__":
    main()
