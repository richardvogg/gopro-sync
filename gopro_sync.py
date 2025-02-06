from random import sample
import subprocess

import os
import re
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
import subprocess
from pathlib import Path
from audio_clicker_helper import *

path_to_files = ".../NewBoxesHalfOpen/"
cameras = 'all' #'all' # #'all' or list of cameras [4,7] (always mention camera 7) 
tStart = 0
tEnd2 = 200 # first 60 seconds of second video 200
tEnd = 300 # up to second 100 of main video 280

cam2list = {1: 0, 2: 1, 3: 2, 4: 3, 6: 4, 7: 5, 8: 6, 9: 7}
rootdir = Path(path_to_files)
list_dirs = []


print(os.listdir(rootdir))
for path in os.listdir(rootdir):
    if not path.startswith(".") and not path.startswith("Converted"):
        for subpath in os.listdir(rootdir / path):
            if not subpath.startswith("."):
                list_dirs.append(rootdir / path / subpath)
 
list_dirs.sort()


experiment_number = 0

for input_path in list_dirs:

    experiment_number += 1
    experiment_number = experiment_number % 3

    try:

        group = input_path.parent.name
        print(group)
        group_letter = group[:1].upper()
        print(group_letter)

        output_path = rootdir / "Converted" / group
        output_path.mkdir(parents=True, exist_ok=True)

        # from https://github.com/scuc/GoPro-Concat-Automation/blob/master/gopro_concat.py


        gopr_source_list = []
        gopr_key_list = []
        gopr_dict = {}

        file_list = sorted(os.listdir(input_path))
        file_list = [f for f in file_list if f.endswith(".MP4") and not f.startswith(".") and (not "extra" in f)]

        # Which GoPro files belong together
        # file: GX010046_cam6.MP4 has to be stiched with GX020046_cam6.MP4---file: B_e_1_220918_c1_p1_2.MP4
        for file in file_list:
            print("FILE: " + file)
            regex = r"(GX01)" #GX01 always exists, we use it as a key
            gp = re.search(regex, file)
            # print(gp)
            if gp is not None:
                gopr_key_list.append(file)
            else:
                pass


        for file in gopr_key_list:
            filenum = file[4:]
            fstring = f"(GX0\\d{{1}}{filenum})"
            r = re.compile(fstring)
            gplist = list(filter(r.match, file_list))
            gopr_dict.update({file:gplist})


        if cameras != "all":
            gopr_dict = {key: value for key, value in gopr_dict.items() if any(f'_cam{camera}' in key for camera in cameras)}
            print(gopr_dict)

        #Read the dictionary and create txt files which contains files which belong together
        for key in gopr_dict:
            camera = key[-5]
            print(camera)

            gpr_txt_path = output_path / ('cam' + camera + '.txt')
            print(gpr_txt_path.exists())
            if gpr_txt_path.exists() is True:
                print("PASS on TXT FILE")
                pass
            else:
                gpr_sources_txt = open(gpr_txt_path, 'a')

                gprfile_list = sorted(gopr_dict[key])
                for file in gprfile_list:
                    file_stmnt = "file " + '\'' + str(input_path / file) + '\'\n'
                    gpr_sources_txt.write(file_stmnt)

                gpr_sources_txt.close()
                
                
            #Join videos which come from the same camera
            mp4_output = output_path / (f'{group_letter}_e{experiment_number}_c{camera}_joined.MP4')
            if mp4_output.exists():
                print("PASS on joined files")
                pass
            else:
                #ffmpeg_cmd = [
                #                        'ffmpeg', '-safe', '0', '-f', 'concat',  '-i',
                #                        gpr_txt_path, '-c', 'copy',
                #                    mp4_output
                #                    ]
                ffmpeg_cmd = [
                    'ffmpeg', '-analyzeduration', '100M', '-probesize', '50M', '-safe', '0', '-f', 'concat', '-i',
                    gpr_txt_path, '-vf', 'scale=1920:1080', '-c:v', 'libx264', '-crf', '23', '-preset', 'medium',
                    '-c:a', 'aac', '-b:a', '192k',
                    mp4_output
                ]

                subprocess.call(ffmpeg_cmd, shell=False)

        file_list = sorted(os.listdir(output_path))
        file_list = [f for f in file_list if f.endswith("joined.MP4")]


        ## extract audio files from joined videos

        for file in file_list:

            if os.path.isfile(output_path / (file[:-4] + ".wav")):
                pass

            else:
                

                ffmpeg_cmd = [
                            'ffmpeg', '-i', output_path / file, '-ab', '160k', '-ac', '2',
                            '-ar', '44100', '-vn', output_path / (file[:-4] + ".wav")
                            ]
                
                #ffmpeg_cmd = [
                #'ffmpeg', '-err_detect', 'ignore_err', '-i', str(output_path / file), 
                #'-ab', '160k', '-ac', '2', '-ar', '44100', '-vn', str(output_path / (file[:-4] + ".wav"))
                #]

                subprocess.call(ffmpeg_cmd, #was Popen
                                    shell=False)
                

        anchor_video_idx = [idx for idx, s in enumerate(file_list) if 'c7' in s][0]

        channels, nChannels, sampleRate, ampWidth, nFrames = extract_audio(str(output_path / (file_list[anchor_video_idx][:-4] + ".wav")), 
                                                                        tStart, tEnd)
        samples = convert_to_mono(channels, nChannels, np.int16)


        samples = samples[::100]


        for idx, item in enumerate(file_list):
            if idx != anchor_video_idx:
                channels2, nChannels2, sampleRate2, ampWidth2, nFrames2 = extract_audio(str(output_path / (file_list[idx][:-4] + ".wav")), tStart, tEnd2)
                samples2 = convert_to_mono(channels2, nChannels2, np.int16)

                samples2 = samples2[::100]
                print("Processing video: ", idx, item)
                print(len(samples2))
                print(sampleRate)

                #abs_diff = np.correlate(samples, samples2)
                abs_diff = get_abs_diff(samples, samples2)

                peaks, properties = find_peaks(-np.array(abs_diff), prominence = 5000, width = (0,40), wlen = 40)
                sorted_prominences = sorted(zip(properties['prominences'], peaks), key=lambda x: x[0], reverse=True)
                max_element, corresponding_element = sorted_prominences[0] #should be 0 normally
                #max_element, corresponding_element = max(zip(properties['prominences'], peaks), key=lambda x: x[0])
                delay_s = round(corresponding_element/(sampleRate/100), 3)
                delay_frames = round(corresponding_element/(sampleRate/100) * 30)

                plt.figure()
                plt.plot(range(len(abs_diff)), abs_diff)
                plt.plot(corresponding_element, np.array(abs_diff)[corresponding_element], "x")
                plt.savefig(path_to_files +"Converted/"+ item[:-11]+'.png')
                plt.close()
                #delay_s = round(np.argmin(abs_diff)/(sampleRate/100), 3)
                #delay_frames = round(np.argmin(abs_diff)/(sampleRate/100) * 30)
                print(str(delay_s) + "s = " + str(delay_frames) + " frames")
                ## Add black frames to beginning of video
                #https://video.stackexchange.com/questions/20717/ffmpeg-add-3-seconds-of-black-to-video-head-and-tail
                ffmpeg_cmd = [
                                    'ffmpeg', '-y', '-i', output_path / file_list[idx], '-vf', 'trim=0:'+str(delay_s)+',geq=0:128:128', 
                                    '-af', 'atrim=0:'+ str(delay_s) + ',volume=0',
                                    '-video_track_timescale', '600', output_path / ("blank" + str(idx) + ".mp4")
                                    ]

                subprocess.run(ffmpeg_cmd, shell=False)

        for idx, item in enumerate(file_list):
            if idx != anchor_video_idx:        
                ffmpeg_cmd = [
                                'ffmpeg', '-y', '-i', output_path / ("blank" + str(idx) + ".mp4"), '-i', output_path / file_list[idx], 
                                '-filter_complex', '[0:v]fps=fps=30[video0];[1:v]fps=fps=30[video1];[video0][0:a:0][video1][1:a:0]concat=n=2:v=1:a=1[outv][outa]', #'[0:v:0][0:a:0][1:v:0][1:a:0]concat=n=2:v=1:a=1[outv][outa]', 
                                '-map', "[outv]", '-map', "[outa]",
                                output_path / (item[:-11] + ".mp4")
                                    ]


                subprocess.run(ffmpeg_cmd, shell=False)

        ffmpeg_cmd = [
                                'ffmpeg', '-y','-i', output_path / file_list[anchor_video_idx], 
                                '-filter_complex', '[0:v:0][0:a:0]concat=n=1:v=1:a=1[outv][outa]', 
                                '-map', "[outv]", '-map', "[outa]",
                                output_path / (file_list[anchor_video_idx][:-11] + ".mp4")
                                ]


        subprocess.run(ffmpeg_cmd, shell=False)

        ## Remove all files that are not used anymore

        for fname in os.listdir(output_path):
            if "cam" in fname:
                os.remove(os.path.join(output_path, fname))

        for fname in os.listdir(output_path):
            if fname.startswith("blank") or ("joined" in fname):
                os.remove(os.path.join(output_path, fname))
                    
    except:
        print("Video not processed")