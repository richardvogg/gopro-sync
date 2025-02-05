# Temporal synchronization of several GoPros

## Idea

Several GoPros are started around the same time. It is known which GoPro was started before the others. There is some distinctive audio signal audible in all cameras. With this script, we want to find the temporal offset of each camera to the main camera and pad the beginning with black frames, so that all videos are synchronized afterwards.


The script will output plots that help to verify visually that the correct offset was actually found.
![imgs/A_e13_c8.png]
![imgs/B_e11_c8.png]