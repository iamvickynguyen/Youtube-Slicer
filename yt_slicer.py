import re
import math
import subprocess
import shlex
from pytube import YouTube
from subprocess import check_call, PIPE, Popen

def download_video(url, filename = 'blank'):
    yt = YouTube(url)
    video = yt.streams.filter(res='1080p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='720p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='1440p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='2160p', type='video', subtype='mp4', fps=30, progressive=True)
    
    if not video:
        print("Choose another video!")
        return None

    video[0].download(filename = filename)

    return 1

# https://yohanes.gultom.id/2020/04/03/splitting-video-with-ffmpeg-and-python/
def get_metadata(filename):
    '''
    Get video metadata using ffmpeg
    '''
    p1 = Popen(["ffmpeg", "-hide_banner", "-i", filename], stderr=PIPE, universal_newlines=True)
    output = p1.communicate()[1]

    re_metadata = re.compile('Duration: (\d{2}):(\d{2}):(\d{2})\.\d+,.*\n.* (\d+(\.\d+)?) fps')
    matches = re_metadata.search(output)

    if matches:
        video_length = int(matches.group(1)) * 3600 + int(matches.group(2)) * 60 + int(matches.group(3))
        video_fps = float(matches.group(4))
        # print('video_length = {}\nvideo_fps = {}'.format(video_length, video_fps))
    else:
        raise Exception("Can't parse required metadata")
    return video_length, video_fps
    
def split_segment(filename, n, by='size'):
    '''
    Split video using segment: very fast but sometimes innacurate
    Reference https://medium.com/@taylorjdawson/splitting-a-video-with-ffmpeg-the-great-mystical-magical-video-tool-%EF%B8%8F-1b31385221bd
    '''
    assert n > 0
    assert by in ['size', 'count']
    split_size = n if by == 'size' else None
    split_count = n if by == 'count' else None
    
    # parse meta data
    video_length, video_fps = get_metadata(filename)

    # calculate split_count
    if split_size:
        split_count = math.ceil(video_length / split_size)
        if split_count == 1:        
            raise Exception("Video length is less than the target split_size.")    
    else: #split_count
        split_size = round(video_length / split_count)

    pth, ext = filename.rsplit(".", 1)
    cmd = 'ffmpeg -hide_banner -loglevel panic -i "{}" -c copy -map 0 -segment_time {} -reset_timestamps 1 -g {} -sc_threshold 0 -force_key_frames "expr:gte(t,n_forced*{})" -f segment -y "{}-%d.{}"'.format(filename, split_size, round(split_size*video_fps), split_size, pth, ext)
    check_call(shlex.split(cmd), universal_newlines=True)

    # return the number of videos
    return split_count

def get_video_info(filename):

    # size (MB in decimal), bitrate
    cmd = 'ffprobe -i {} -show_entries format=size,bit_rate -v quiet'.format(filename)
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output = str(proc.stdout.read()).split('\\n')
    size = int(list(filter(lambda x: x.startswith('size='), output))[0][len('size='):]) / (10**6)
    bitrate = int(list(filter(lambda x: x.startswith('bit_rate='), output))[0][len('bit_rate='):]) // (10**3)

    # width x height
    cmd = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {}'.format(filename)
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    dimensions = str(proc.stdout.read().decode('ascii')).strip().split('x')

    # return size, bitrate, width, height
    return size, bitrate, int(dimensions[0]), int(dimensions[1])

def compress_and_scale(filename, outfile_name):
    subprocess.run(["ffmpeg" ,"-i", filename,"-filter:v" ,"scale=1080:1350:force_original_aspect_ratio=decrease,pad=1080:1350:(ow-iw)/2:(oh-ih)/2", "-b", "400k", outfile_name])
    subprocess.Popen(['rm', filename])

# test
video = download_video('https://youtu.be/nsZObkD1dog', 'test')
if video:
    split_count = split_segment('test.mp4', 30)
    for i in range(split_count):
        compress_and_scale('test-{}.mp4'.format(i), 'out-{}.mp4'.format(i))

        # size, bitrate, width, height = get_video_info('out-{}.mp4'.format(i))
        # print(size, bitrate, width, height)