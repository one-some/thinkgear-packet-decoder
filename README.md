## thinkgear packet decoder
Questionable script for decoding packets over UART from NeuroSky TGAM1 EEG chips, which I found in a toy and wanted to mess around with.
Graphs some different values as well

### how 2?
1. find eeg toy (mindflex duel in my case)
2. blow it open and find the eeg board's documentation online
3. ducttape wires to ground and serial TX (carefully)
4. (lazy serial monitor, if you have one use it!) plug into arduino, tie reset to ground, and connect eeg UART to the arduino's serial pins
5. works? (edit the port in the script tho)

### screenshot
![Screenshot of various graphs](https://github.com/one-some/thinkgear-packet-decoder/assets/69319754/c03d8dfb-b612-4699-a78b-272fc9be33f4)
hopefully the one electrode this thing has isnt high enough fidelity for this screenshot to screw me over when eeg data leaking attacks happen in 20 years

in all seriousness, this thing sux a lot for anything more practical than "sometimes it changes in response to stimuli" which is nifty enough i guess
