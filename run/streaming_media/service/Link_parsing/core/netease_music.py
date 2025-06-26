import httpx
import re
from PIL import Image, ImageFilter
from io import BytesIO
import time
import os

#常用的请求头
NETEASE_MUSIC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Referer": "https://music.163.com/",
}

OFFICIAL_SONG_DETAIL_API = "https://music.163.com/api/song/detail?ids=[{}]"  #官方API
DOWNLOAD_API = "https://www.byfuns.top/api/1/?id={}"  #下载API

def format_duration(duration_ms):
    """将毫秒时长格式化为 MM:SS"""
    if duration_ms:
        minutes = duration_ms // 60000
        seconds = (duration_ms % 60000) // 1000
        return f"{minutes:02d}:{seconds:02d}"
    else:
        return "未知"

async def fetch_song_info(song_id, filepath):
    """
    根据歌曲 ID 获取歌曲信息（使用官方 API），并获取下载链接保存到文件。
    """
    async with httpx.AsyncClient(headers=NETEASE_MUSIC_HEADERS) as client:
        try:
            #获取歌曲信息
            response = await client.get(OFFICIAL_SONG_DETAIL_API.format(song_id))
            response.raise_for_status()
            response_json = response.json()

            if "songs" not in response_json or not response_json["songs"]:
                raise ValueError("官方 API 返回数据格式错误")

            song_data = response_json["songs"][0]
            album_data = song_data.get("album", {})

            #获取下载链接并保存到文件
            download_url = await fetch_song_download_url(song_id)
            if download_url:
                url_file_path = os.path.join(filepath, "不允许进行传播、销售等商业活动!!.txt")
                with open(url_file_path, "w", encoding="utf-8") as f:
                    f.write(download_url)
            else:
                 url_file_path = None

            return {
                "name": song_data.get("name", "未知歌曲"),
                "artists": [artist.get("name", "未知歌手") for artist in song_data.get("artists", [])],
                "album": album_data.get("name", "未知专辑"),  #其实这里可以不用返回
                "cover_url": album_data.get("picUrl", ""),
                "song_type": get_song_type(song_data),
                "bpm": get_bpm(song_data), #这里也可以不用
                "publish_time":  album_data.get("publishTime"), #这里也可以不用
                "duration":  song_data.get("duration"), #这里也可以不用
                "subType": album_data.get("subType", "未知类型"),#这里也可以不用
                "url_file_path": url_file_path,  #返回文件路径
            }
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            print(f"官方 API 请求失败: {e}")
            return None

async def fetch_song_download_url(song_id):
    """
    根据歌曲 ID 获取下载链接。
    """
    async with httpx.AsyncClient(headers=NETEASE_MUSIC_HEADERS) as client:
        try:
            response = await client.get(DOWNLOAD_API.format(song_id))
            response.raise_for_status()
            return response.text.strip()
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"下载链接 API 请求失败: {e}")
            return None

async def download_image(url: str, path: str = "") -> str:
    def crop_center_square(image):
        width, height = image.size
        min_edge = min(width, height)
        left = (width - min_edge) // 2
        top = (height - min_edge) // 2
        right = left + min_edge
        bottom = top + min_edge
        return image.crop((left, top, right, bottom))
    file_name = re.sub(r"[:/]", "_", url.split('/').pop().split('?')[0])
    path = f"{path}{file_name}"
    async with httpx.AsyncClient(headers=NETEASE_MUSIC_HEADERS) as client:
        response = await client.get(url)
        if response.status_code == 200:
            square_image = crop_center_square(Image.open(BytesIO(response.content)))
            if square_image.mode != "RGB":
                square_image = square_image.convert("RGB")
            square_image.save(path)
            return path

def get_song_type(song_data):
    if "lyric" not in song_data:
      return ""
    lyric = ''
    try:
      if song_data.get("lrc") and song_data.get("lyric"):
          lyric = song_data["lrc"]["lyric"].lower()
      elif song_data.get("tlyric") and song_data.get("tlyric"):
          lyric = song_data["tlyric"]["lyric"].lower()
    except:
       pass
    if "纯音乐" in lyric or "instrumental" in lyric:
        return "纯音乐"
    elif "原声带" in song_data["album"]["name"].lower() or "ost" in song_data["album"]["name"].lower():
        return "原声带"
    return ""


def get_bpm(song_data):
    return ""
