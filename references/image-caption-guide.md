# V2 image caption and index contract

## Original-media boundary

Original media is immutable: never rename, overwrite, delete, recompress, or
otherwise modify the original file. The index creates a display identifier only.

## Index records

Each image index item contains an `id`, `original_file`, `caption`, `evidence`,
and `used_in`. IDs are unique, contiguous, three-digit decimal strings starting
at `001` (`001`, `002`, `003`, ...). `used_in` lists the draft heading or
module where the image appears.

`evidence` is either `visible` for what can be seen in the original or
`source-pack` for a separately cited source fact. A caption may describe only
the evidence recorded for that item.

## Draft links and claim limit

Write image placeholders as `![[사진 001: caption]]`, using the same ID and a
matching indexed caption. A visual caption must not assert an unsupported menu
name, taste, feeling, price, service, person identity, or event. Source-pack
facts still need their claim provenance; a photograph does not upgrade them to
personal experience.
