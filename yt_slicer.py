import re
import math
import subprocess
import shlex
from pytube import YouTube
from subprocess import check_call, PIPE, Popen

# NOTE: split then compress each of the clips (another way is to compress the video then split it, smaller clips may be less than 10MB ??)

# FIXME
def download_video(url, filename = 'blank'):
    yt = YouTube(url)

    video = yt.streams.filter(res='720p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='1080p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='1440p', type='video', subtype='mp4', fps=30, progressive=True) \
        or yt.streams.filter(res='2160p', type='video', subtype='mp4', fps=30, progressive=True)
    
    if not video:

        # download video and audio, then merge them
        video = yt.streams.filter(res='1080p', type='video', subtype='webm', fps=30, progressive=False) \
            or yt.streams.filter(res='720p', type='video', subtype='webm', fps=30, progressive=False) \
            or yt.streams.filter(res='1440p', type='video', subtype='webm', fps=30, progressive=False) \
            or yt.streams.filter(res='2160p', type='video', subtype='webm', fps=30, progressive=False) \
            or yt.streams.filter(res='1080p', type='video', subtype='mp4', fps=30, progressive=False) \
            or yt.streams.filter(res='720p', type='video', subtype='mp4', fps=30, progressive=False) \
            or yt.streams.filter(res='1440p', type='video', subtype='mp4', fps=30, progressive=False) \
            or yt.streams.filter(res='2160p', type='video', subtype='mp4', fps=30, progressive=False)
        
        audio = yt.streams.filter(type='audio', subtype='mp4', abr='128kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='mp4', abr='160kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='webm', abr='128kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='webm', abr='160kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='mp4', abr='70kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='mp4', abr='50kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='webm', abr='70kbps', progressive=False) \
            or yt.streams.filter(type='audio', subtype='webm', abr='50kbps', progressive=False)
        
        if not video or not audio:
            print('Choose another video')
            return None

        video[0].download(filename = 'videotmp')
        audio[0].download(filename = 'audiotmp')

        grep_video_cmd = "ls |grep 'videotmp'"
        proc = subprocess.Popen(grep_video_cmd, stdout=subprocess.PIPE, shell=True)
        video_name = str(proc.stdout.read().decode('ascii')).strip()

        grep_audio_cmd = "ls |grep 'audiotmp'"
        proc = subprocess.Popen(grep_audio_cmd, stdout=subprocess.PIPE, shell=True)
        audio_name = str(proc.stdout.read().decode('ascii')).strip()

        if audio_name == 'audiotmp.webm':
            convert_cmd = 'ffmpeg -i audiotmp.webm audiotmp.mp4'
            proc = subprocess.Popen(convert_cmd.split())

        merge_cmd = 'ffmpeg -i {} -i audiotmp.mp4 -c:v copy -c:a copy {}.mp4'.format(video_name, filename)
        subprocess.Popen(merge_cmd.split(), stdout=subprocess.PIPE)

        subprocess.Popen(['rm', video_name])
        subprocess.Popen(['rm', audio_name])
    
    else:
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

    # size (MB in decimal)
    cmd = 'ffprobe -i {} -show_entries format=size -v quiet'.format(filename)
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    output = str(proc.stdout.read()).split('\\n')
    size = int(list(filter(lambda x: x.startswith('size='), output))[0][len('size='):]) / (10**6)

    # width x height
    cmd = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 {}'.format(filename)
    proc = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE)
    dimensions = str(proc.stdout.read().decode('ascii')).strip().split('x')

    # return size, width, height
    return size, int(dimensions[0]), int(dimensions[1])

# FIXME
def compress(filename):
    tmp_name = filename[: -len('.mp4')] + 'tmp.mp4'
    rename_cmd = 'mv {} {}'.format(filename, tmp_name)
    subprocess.Popen(rename_cmd.split())

    compress_cmd = 'ffmpeg -i {} -vcodec h264 -acodec aac {}'.format(tmp_name, filename)
    subprocess.Popen(compress_cmd.split())

    subprocess.Popen(['rm', tmp_name])

# NOTE: tmp function to download video. Delete this after fixing download_video()
def get_video(url, filename):
    yt = YouTube(url)
    video = yt.streams.filter(res='720p', type='video', subtype='mp4') or yt.streams.filter(res='1080p', type='video', subtype='mp4')  
    if not video:
        print("Choose another video!")
        return None
    video[0].download(filename = filename)
    return 1

# test
video = get_video('https://youtu.be/nsZObkD1dog', 'test')
if video:
    split_count = split_segment('test.mp4', 60)
    for i in range(split_count):
        size, width, height = get_video_info('test-{}.mp4'.format(i))
        # print(size, width, height)

        # if size > 10:
        #     compress('test-{}.mp4'.format(i))