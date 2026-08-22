# Generated enclosure exports

Generate STL files from `../source/enclosure.scad` with the commands in the
enclosure README. Generated meshes are revision artifacts; the OpenSCAD source
and its parameters remain authoritative.

`SHA256SUMS` covers the four printable meshes, window-cut profile, and generated
assembly preview. Run
`python3 ../../tools/validate_enclosure.py --require-openscad` to verify dimensions,
mesh validity, and agreement with freshly rendered source. `assembly.png` remains
an orientation preview and is not dimensional evidence.
