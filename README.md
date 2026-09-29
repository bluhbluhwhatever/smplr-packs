# SMPLR packs

The sample packs for the SMPLR app. The app reads `index.json` from this repo's GitHub Pages site (bluhbluhwhatever.github.io/smplr-packs), downloads the packs it needs and keeps them on the phone, so they still work offline.

## How it's laid out

```
index.json              the pack list the app reads
packs/<pack id>/*.m4a   each pack's sounds
tools/                  the script that made the test packs
```

## index.json

```json
{
 "v": 1,
 "artist": "test-pressing",
 "weekly": "challenge-2",
 "packs": [
  {
   "id": "test-pressing",
   "title": "TEST PRESSING",
   "by": "SMPLR TEST PACK",
   "brief": "ONE OR TWO SHORT LINES ABOUT THE PACK.",
   "date": "OCT 2026",
   "sounds": [
    { "file": "kick-round.m4a", "name": "ROUND", "tag": "KICK" },
    { "file": "loop-drums-86.m4a", "name": "DUST DRUMS", "tag": "LOOP", "bpm": 86, "bars": 2 },
    { "pack": "dusty-loops", "file": "vox-ah.m4a", "name": "AH", "tag": "VOX" }
   ]
  }
 ]
}
```

- `artist` and `weekly` name the packs shown in the ARTIST and WEEKLY crates. Every other pack shows in PAST, in the order listed here, so put the newest first.
- A pack holds 16 sounds (up to 32 are read), in pad order: LOAD KIT puts them on pads 1 to 16 as listed. Following the starting kit's order (KICK, SNARE, HAT, SNARE, BASS, KEYS, PERC, HAT, HAT, PERC, SNARE, BASS, KEYS, KEYS, KEYS, FX) keeps the app's templates working with the kit.
- `tag` is one of KICK, SNARE, HAT, PERC, BASS, KEYS, FX, VOX or LOOP. Loops can carry `bpm` and `bars`, so FIT knows their length.
- A sound with `"pack"` reuses a file from another pack. That's how a weekly challenge can use archive samples with a twist without new files.
- Ids and file names use only letters, numbers, `-`, `_` and `.` (no spaces). Names show in capitals, up to 14 characters.
- Sounds are mono or stereo `.m4a` (AAC, 128k) or `.wav`. Anything iOS can read works, but m4a keeps packs small: a pack of 16 is usually under 1 MB.
- Never rename or delete a file that's been published: people may have it saved in their crates.

## Adding a pack

1. Make a folder `packs/<new id>/` and upload the sounds into it.
2. Add the pack to the top of `packs` in `index.json`.
3. To feature it, point `artist` or `weekly` at its id. The old one moves to PAST by itself.

GitHub Pages takes a minute or two to update, and the app checks for new packs when the CRATE page opens (at most every 20 minutes) or when you tap REFRESH.
