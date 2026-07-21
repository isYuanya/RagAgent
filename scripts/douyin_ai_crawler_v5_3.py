# -*- coding: utf-8 -*-

"""
Douyin AI Crawler V5.3 (accuracy)

功能:
1. Edge持久化登录
2. Playwright采集
3. 视频流捕获
4. Whisper提取视频正文
5. CSV输出

"""


import os
import re
import json
import csv
import time
import random
import subprocess


from pathlib import Path


from playwright.sync_api import sync_playwright


from faster_whisper import WhisperModel

try:
    from opencc import OpenCC
    _T2S = OpenCC("t2s")
except Exception:
    _T2S = None






# ==================================================
# 配置
# ==================================================


CONFIG_FILE = os.getenv("DOUYIN_CRAWLER_CONFIG", "config.json")



with open(
    CONFIG_FILE,
    "r",
    encoding="utf-8"
) as f:

    CONFIG=json.load(f)





KEYWORD = CONFIG.get(
    "keyword",
    "贷款"
)


MAX_VIDEOS = CONFIG.get(
    "max_videos",
    20
)



MIN_LIKES = CONFIG.get(
    "min_likes",
    500
)



SCROLL_COUNT = CONFIG.get(
    "scroll_count",
    20
)



SCROLL_WAIT = CONFIG.get(
    "scroll_wait",
    5
)



INDUSTRY = CONFIG.get(
    "default_industry",
    "金融贷款"
)

# 枚举值定义（与后端检索保持一致，英文值）
VALID_AUDIENCES = {"new_users", "returning_users", "price_sensitive", "expert_buyers"}
VALID_PURPOSES = {"conversion", "traffic", "engagement", "brand"}
VALID_STYLES = {"practical", "empathetic", "professional", "storytelling"}
VALID_PLATFORMS = {"douyin", "xhs", "wechat", "video_account"}

DEFAULT_AUDIENCE = CONFIG.get("default_audience", "")
DEFAULT_PURPOSE = CONFIG.get("default_purpose", "")
DEFAULT_STYLE = CONFIG.get("default_style", "")

# 启动时校验枚举值
def _validate_enum(value, valid_set, name):
    if value and value not in valid_set:
        raise ValueError(
            f"config.json 中 {name} = '{value}' 不在允许范围内！\n"
            f"允许值：{sorted(valid_set)}"
        )

_validate_enum(DEFAULT_AUDIENCE, VALID_AUDIENCES, "default_audience")
_validate_enum(DEFAULT_PURPOSE, VALID_PURPOSES, "default_purpose")
_validate_enum(DEFAULT_STYLE, VALID_STYLES, "default_style")

# platform 固定为 douyin，也校验一下
assert "douyin" in VALID_PLATFORMS, "platform 枚举值异常"


def emit_progress(**payload):
    try:
        print("CRAWLER_PROGRESS " + json.dumps(payload, ensure_ascii=False), flush=True)
    except Exception:
        pass









# ==================================================
# 路径
# ==================================================


BASE_DIR = Path(__file__).parent



EDGE_PROFILE = (

    BASE_DIR

    /

    "edge_profile"

)



EDGE_PROFILE.mkdir(
    exist_ok=True
)





VIDEO_DIR=(

    BASE_DIR

    /

    "videos"

)



VIDEO_DIR.mkdir(
    exist_ok=True
)





WHISPER_MODEL = CONFIG.get("whisper_model_v3", "faster-whisper-small")


ASR_PROMPT = CONFIG.get(
    "asr_prompt",
    "以下是一段普通话金融理财类短视频的口播文案，内容通顺、有标点，使用简体中文。"
    "常见词汇：房贷、车贷、商贷、公积金、提前还款、等额本息、等额本金、"
    "利率、违约金、征信、放款、面签、重新定价、首套房、二套房、月供、本金、利息。",
)


MODEL_PATH=(

    BASE_DIR

    /

    "models"

    /

    WHISPER_MODEL

)


# 若指定模型不存在，自动回退到本地已有的最优模型
if not MODEL_PATH.exists():
    for _alt in (
        "faster-whisper-medium",
        "faster-whisper-small",
        "faster-whisper-base",
        "faster-whisper-tiny",
    ):
        _p = BASE_DIR / "models" / _alt
        if _p.exists():
            MODEL_PATH = _p
            WHISPER_MODEL = _alt
            break
    print("[v5.3] 指定模型不存在，回退为:", WHISPER_MODEL)





CSV_FILE=(

    Path(CONFIG.get("output_csv") or os.getenv("DOUYIN_CRAWLER_OUTPUT") or (BASE_DIR / "douyin_result.csv"))

)

if not CSV_FILE.is_absolute():
    CSV_FILE = BASE_DIR / CSV_FILE

CSV_FILE.parent.mkdir(parents=True, exist_ok=True)










# ==================================================
# Whisper
# ==================================================



print(
    "加载 faster-whisper..."
)



whisper_model = WhisperModel(



    str(MODEL_PATH),



    device="cpu",



    compute_type="int8"



)





# ==================================================
# 正文纠错后处理（繁简转换 + 领域同音字纠正）
# ==================================================

# 领域高频同音/识别错误 -> 正确写法（仅收录多字、低误伤的词条）
CORRECTIONS = {
    "防待": "房贷", "房带": "房贷", "防贷": "房贷", "房待": "房贷", "放待": "房贷",
    "车带": "车贷", "商带": "商贷", "经营带": "经营贷", "消费带": "消费贷",
    "攻击金": "公积金", "攻积金": "公积金", "公击金": "公积金", "供积金": "公积金", "工积金": "公积金",
    "位月轻": "违约金", "违月金": "违约金", "位约金": "违约金", "位月金": "违约金", "违月轻": "违约金",
    "等了本息": "等额本息", "等额本期": "等额本息", "等奔本息": "等额本息",
    "等奔金": "等额本金", "等了奔金": "等额本金", "等额奔金": "等额本金",
    "提前缓": "提前还", "提前环": "提前还", "缓房贷": "还房贷", "环房贷": "还房贷",
    "缓款": "还款", "环款": "还款", "缓贷": "还贷", "环贷": "还贷", "缓完": "还完", "环完": "还完",
    "重心定价": "重新定价", "重新订家": "重新定价", "重新定家": "重新定价", "重定家": "重定价",
    "手套住房": "首套住房", "手套房": "首套房", "手套防贷": "首套房贷", "手套房贷": "首套房贷",
    "中阶费": "中介费", "中借": "中介", "房产军事": "房产顾问", "房产军师": "房产顾问",
    "征信报告": "征信报告", "面签": "面签", "结清": "结清",
    "哭税": "扣税", "哭碎": "扣税", "抗税": "扣税",
    "本斤": "本金", "利绿": "利率", "绿绿": "利率",
    "月共": "月供", "年线": "年限", "年贡": "年限", "越贡": "月供",
    "预约金": "违约金", "北约轻": "违约金",
    "还带": "还贷", "缓带": "还贷", "环带": "还贷", "接省": "节省",
}

# 需要移除的口水/停顿噪声（成对或单字重复）
_FILLER = re.compile(r"(那个|这个|就是说|然后呢|对不对|是吧|啊|呃|嗯)\1+")


def refine_text(text):
    """繁转简 + 领域纠错 + 基础清洗。"""
    if not text:
        return ""
    s = str(text)
    # 1. 繁体转简体（whisper 常混入繁体，是"错别字"的大来源）
    if _T2S is not None:
        try:
            s = _T2S.convert(s)
        except Exception:
            pass
    # 2. 去掉中文字符之间多余的空格
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)
    # 3. 领域同音字纠正（按 key 长度降序，先长后短，减少误伤）
    for k in sorted(CORRECTIONS, key=len, reverse=True):
        if k in s:
            s = s.replace(k, CORRECTIONS[k])
    # 4. 合并重复标点与空白
    s = re.sub(r"\s{2,}", " ", s)
    s = re.sub(r"([，。！？、])\1+", r"\1", s)
    return s.strip()


print(
    "Whisper加载完成"
)











# ==================================================
# Edge浏览器
# ==================================================



def start_edge(playwright):


    """
    使用独立Edge用户目录

    登录状态永久保存

    """



    print(
        "启动持久化Edge..."
    )




    context = playwright.chromium.launch_persistent_context(




        user_data_dir=str(
            EDGE_PROFILE
        ),





        channel="msedge",




        headless=False,





        viewport={

            "width":1400,

            "height":900

        },




        args=[



            "--disable-blink-features=AutomationControlled",



            "--start-maximized"



        ]



    )



    return context









def get_single_page(context):


    """
    保证只使用一个页面
    """



    pages=context.pages




    if len(pages)==0:


        page=context.new_page()



    else:


        page=pages[0]





    # 删除多余tab


    if len(pages)>1:


        for p in pages[1:]:


            try:

                p.close()

            except:

                pass






    return page











# ==================================================
# 搜索页面
# ==================================================



def open_search(page):


    url=(



        "https://www.douyin.com/jingxuan/search/"



        +

        KEYWORD



        +

        "?aid=65088153-d7f4-496c-8ece-221cd0ea5b19&type=general"



    )





    print(
        "打开搜索:",
        url
    )



    page.goto(



        url,



        timeout=60000



    )




    time.sleep(5)






    if "login" in page.url:


        print(
"""
请登录抖音

登录完成后按回车继续

"""
        )


        input()





    return page











# ==================================================
# 视频资源监听
# ==================================================



class VideoCapture:



    def __init__(self):


        self.url=None

        self.candidates=[]





    def handle(self, response):
        try:
            url = response.url
            low = url.lower()
            is_media = (
                "douyinvod" in low
                or "/video/tos/" in low
                or ("aweme" in low and "play" in low)
                or (".mp4" in low and "video" in low)
            )
            if not is_media:
                return
            if url not in self.candidates:
                self.candidates.append(url)
            cur = (self.url or "").lower()
            better = ("douyinvod" in low) and (
                self.url is None
                or "douyinvod" not in cur
                or len(url) > len(self.url)
            )
            if self.url is None or better:
                self.url = url
        except Exception:
            pass










# ==================================================
# 下载视频
# ==================================================



def _load_cookie_header():
    """从 cookies.txt(Netscape 格式) 拼出 Cookie 请求头字符串。"""
    p = BASE_DIR / "cookies.txt"
    if not p.exists():
        return ""
    pairs = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7 and parts[5]:
            pairs.append(parts[5] + "=" + parts[6])
    return "; ".join(pairs)


COOKIE_HEADER = _load_cookie_header()


def _ffmpeg_headers():
    # 仅用 Referer + UA；douyinvod 签名直链无需 Cookie，附带超长 Cookie 反而可能触发错误
    return "Referer: https://www.douyin.com/\r\nUser-Agent: Mozilla/5.0\r\n"


def pick_play_url(video):
    """挑一个带音轨的渐进式合成地址：优先 format=mp4 的 bit_rate 档，
    避开 media-video-avc1 / play/dash 这类纯视频 DASH 流。"""
    def usable(u):
        low = u.lower()
        return (
            "douyinvod" in low
            and "media-video-avc1" not in low
            and "/play/dash/" not in low
        )

    candidates = []
    # 1) bit_rate 里 format=mp4 的档（渐进式，音视频合一）最优先
    for br in (video.get("bit_rate") or []):
        if (br or {}).get("format") == "mp4":
            candidates += (((br.get("play_addr") or {}).get("url_list")) or [])
    # 2) 顶层 play_addr（通常也是渐进式 mp4）
    for key in ("play_addr", "play_addr_h264"):
        pa = video.get(key)
        if isinstance(pa, dict):
            candidates += (pa.get("url_list") or [])
    # 3) 其余 bit_rate 档兜底
    for br in (video.get("bit_rate") or []):
        candidates += (((br.get("play_addr") or {}).get("url_list")) or [])

    for u in candidates:
        if usable(u):
            return u
    return ""


def _has_audio(video_file):
    """用 ffprobe 判断文件里是否存在音频流。"""
    if not video_file:
        return False
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a",
             "-show_entries", "stream=index", "-of", "csv=p=0", str(video_file)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
        )
        return bool(r.stdout.decode(errors="ignore").strip())
    except Exception:
        return False


def download_video(page, info):
    """优先用 API 渐进式合成地址(含音轨)下载；下载失败再回退浏览器抓流。
    不再用 ffprobe 预判音轨——渐进式 mp4 本身即含音轨，交给后续 extract_audio 处理。"""
    play_url = info.get("play_url")
    if play_url:
        vf = save_video(play_url, info["id"])
        try:
            ok = bool(vf) and os.path.getsize(vf) > 1000
        except Exception:
            ok = False
        if ok:
            print("使用合成播放地址")
            return vf
        print("合成地址下载失败，回退浏览器抓流")
    return capture_video(page, info)


def fetch_follower_count(page, author_url):
    """综合搜索接口不返回粉丝数，打开作者主页从 profile 接口响应里抓 follower_count。"""
    if not author_url or author_url.rstrip("/").endswith("/user"):
        return 0
    got = {"n": 0}

    def h(resp):
        try:
            if "/web/user/" not in resp.url and "user/profile" not in resp.url:
                return
            data = resp.json()
            u = data.get("user") or {}
            fc = u.get("follower_count")
            if fc:
                got["n"] = fc
        except Exception:
            pass

    page.on("response", h)
    try:
        page.goto(author_url, timeout=45000)
        for _ in range(12):
            if got["n"]:
                break
            time.sleep(1)
    except Exception:
        pass
    try:
        page.remove_listener("response", h)
    except Exception:
        pass
    if got["n"]:
        print("补充粉丝数:", got["n"])
    return got["n"]


def save_video(url,video_id):


    if not url:


        return None





    output=(

        VIDEO_DIR

        /

        f"{video_id}.mp4"

    )





    try:



        print(
            "保存视频..."
        )




        _r = subprocess.run(



            [

                "ffmpeg",

                "-y",

                "-headers",
                _ffmpeg_headers(),
                "-i",

                url,

                "-c",

                "copy",

                str(output)

            ],



            stdout=subprocess.PIPE,



            stderr=subprocess.PIPE,



            timeout=120



        )





        if (not output.exists()) or output.stat().st_size < 1000:
            try:
                print("ffmpeg失败:", (_r.stderr.decode(errors="ignore")[-400:] if _r.stderr else "no-stderr"))
            except Exception:
                pass
            return None

        if output.exists():



            return str(output)




    except Exception as e:


        print(

            "视频保存失败",

            e

        )





    return None

# ==================================================
# 抖音搜索采集
# ==================================================


def collect_videos():

    videos = {}



    with sync_playwright() as p:


        context = start_edge(p)



        page = get_single_page(context)



        open_search(page)






        def response_handler(response):


            try:


                url=response.url



                if "aweme" not in url:


                    return




                data=response.json()





                items=data.get(

                    "data",

                    []

                )




                for item in items:



                    aweme=item.get(

                        "aweme_info"

                    )



                    if aweme:



                        videos[

                            aweme["aweme_id"]

                        ]=aweme





            except:



                pass





        page.on(

            "response",

            response_handler

        )







        for i in range(

            SCROLL_COUNT

        ):



            old=len(videos)






            page.mouse.wheel(



                0,



                random.randint(

                    2500,

                    4500

                )



            )





            wait=0




            while wait < SCROLL_WAIT:



                time.sleep(1)



                if len(videos)>old:


                    break



                wait+=1







            print(

                "滚动",

                i+1,

                "数量",

                len(videos)

            )

            eligible_count=sum(
                1
                for aweme in videos.values()
                if (aweme.get("statistics") or {}).get("digg_count", 0) >= MIN_LIKES
            )
            emit_progress(
                phase="scrolling",
                collected_count=len(videos),
                eligible_count=eligible_count,
                saved_count=0,
                target_count=min(MAX_VIDEOS, max(eligible_count, 1)),
                message=f"已滚动 {i + 1}/{SCROLL_COUNT} 次，满足点赞条件 {eligible_count} 条",
            )






            if len(videos)>=MAX_VIDEOS*5:


                break






        context.close()





    return list(

        videos.values()

    )









# ==================================================
# 视频信息解析
# ==================================================


def parse_aweme(aweme):


    author=aweme.get(

        "author",

        {}

    )



    stat=aweme.get(

        "statistics",

        {}

    )



    vid=aweme.get(

        "aweme_id",

        ""

    )

    # 粉丝数：兼容综合搜索里可能出现的不同字段名
    followers = (
        author.get("follower_count")
        or author.get("fans_count")
        or author.get("mplatform_followers_count")
        or 0
    )

    # 合成播放地址(含音轨)，优先于 DASH 纯视频流
    play_url = pick_play_url(aweme.get("video", {}) or {})





    return {




        "id":

            vid,




        "url":

            "https://www.douyin.com/video/"

            +

            vid,




        "desc":

            aweme.get(

                "desc",

                ""

            ),





        "author_name":

            author.get(

                "nickname",

                ""

            ),




        "author_url":

            "https://www.douyin.com/user/"

            +

            author.get(

                "sec_uid",

                ""

            ),




        "followers":

            followers,

        "play_url":

            play_url,




        "likes":

            stat.get(

                "digg_count",

                0

            ),




        "comments":

            stat.get(

                "comment_count",

                0

            ),




        "favorites":

            stat.get(

                "collect_count",

                0

            ),




        "shares":

            stat.get(

                "share_count",

                0

            )



    }









# ==================================================
# 进入详情页抓视频
# ==================================================



def capture_video(page,video):



    capture=VideoCapture()



    page.on(

        "response",

        capture.handle

    )





    try:



        page.goto(



            video["url"],



            timeout=60000
        )

        # 主动触发播放：等待video元素并点击、静音播放
        try:
            page.wait_for_selector("video", timeout=15000)
        except Exception:
            pass

        try:
            page.mouse.click(640, 360)
        except Exception:
            pass

        # 轮询等待视频流被捕获，最多约30秒，命中即提前结束
        for _ in range(30):
            try:
                page.evaluate("() => { const vs=document.querySelectorAll('video'); vs.forEach(v=>{v.muted=true; try{v.play()}catch(e){}}); }")
            except Exception:
                pass
            if capture.url:
                break
            time.sleep(1)

        try:
            page.remove_listener("response", capture.handle)
        except Exception:
            pass




    except Exception as e:



        print(

            "打开视频失败",

            e

        )





    video_url=capture.url





    if video_url:



        print(

            "捕获视频流成功"

        )



        return save_video(

            video_url,

            video["id"]

        )



    else:


        print(

            "未捕获视频流"

        )



        return None










# ==================================================
# 提取音频
# ==================================================



def extract_audio(video_file):


    if not video_file:


        return None





    audio_file=(

        Path(video_file)

        .with_suffix(".wav")

    )





    try:



        result=subprocess.run(



            [

                "ffmpeg",



                "-y",



                "-i",



                video_file,



                "-vn",



                "-ac",



                "1",



                "-ar",



                "16000",



                str(audio_file)



            ],



            stdout=subprocess.PIPE,



            stderr=subprocess.PIPE,



            timeout=120



        )







        if audio_file.exists():



            return str(audio_file)







        print(

            result.stderr.decode(

                errors="ignore"

            )[-500:]

        )






    except Exception as e:



        print(

            "音频转换失败",

            e

        )





    return None


# ==================================================
# Whisper正文识别
# ==================================================


def whisper_text(audio_file):

    if not audio_file:
        return ""


    try:

        print("开始ASR...")


        segments, info = whisper_model.transcribe(
            audio_file,
            language="zh",
            task="transcribe",
            beam_size=5,
            best_of=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            initial_prompt=ASR_PROMPT,
            temperature=[0.0, 0.2, 0.4, 0.6]
        )


        texts=[]


        for seg in segments:

            txt=seg.text.strip()

            print(
                "ASR片段:",
                txt
            )


            if txt:
                texts.append(txt)



        result=refine_text("".join(texts))



        print(
            "最终ASR:",
            result
        )


        return result



    except Exception as e:


        print(
            "ASR失败:",
            e
        )

        return ""










# ==================================================
# CSV
# ==================================================



CSV_HEADER=[


    "source_text",



    "source_url",



    "author_name",



    "author_url",



    "author_follower_count",



    "platform",



    "industry",



    "audience",



    "purpose",



    "style",



    "likes",



    "comments",



    "favorites",



    "shares"



]








def init_csv():



    if not CSV_FILE.exists():



        with open(



            CSV_FILE,



            "w",



            newline="",



            encoding="utf-8-sig"



        ) as f:



            writer=csv.DictWriter(



                f,



                fieldnames=CSV_HEADER



            )



            writer.writeheader()











def save_row(row):


    try:



        with open(



            CSV_FILE,



            "a",



            newline="",



            encoding="utf-8-sig"



        ) as f:



            writer=csv.DictWriter(



                f,



                fieldnames=CSV_HEADER



            )



            writer.writerow(row)





        return True




    except PermissionError:



        print(

            "CSV文件被占用，请关闭Excel"

        )



        time.sleep(3)



        return False











# ==================================================
# 已处理检测
# ==================================================



def load_finished():


    finished=set()



    if not CSV_FILE.exists():


        return finished





    try:



        with open(



            CSV_FILE,



            "r",

            encoding="utf-8-sig"



        ) as f:



            reader=csv.DictReader(f)



            for row in reader:



                finished.add(

                    row.get(

                        "source_url",

                        ""

                    )

                )



    except:



        pass





    return finished












# ==================================================
# 主处理流程
# ==================================================



def process_videos(videos):



    init_csv()



    finished=load_finished()





    videos.sort(



        key=lambda x:



        x.get(

            "statistics",

            {}

        ).get(

            "digg_count",

            0

        ),



        reverse=True



    )






    # 诊断：把排序后的第一条原始 aweme 落盘，便于核对字段结构
    try:
        if videos:
            with open(BASE_DIR / "probe_sample.json", "w", encoding="utf-8") as _f:
                json.dump(videos[0], _f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    eligible_total=min(
        MAX_VIDEOS,
        sum(
            1
            for item in videos
            if (item.get("statistics") or {}).get("digg_count", 0) >= MIN_LIKES
            and ("https://www.douyin.com/video/" + item.get("aweme_id", "")) not in finished
        ),
    )

    emit_progress(
        phase="processing",
        eligible_count=eligible_total,
        saved_count=0,
        target_count=max(eligible_total, 1),
        message=f"开始处理 {eligible_total} 条达标视频",
    )

    count=0

    skipped_likes=0

    skipped_likes=0







    with sync_playwright() as p:



        context=start_edge(p)



        page=get_single_page(context)






        for item in videos:



            info=parse_aweme(item)


            emit_progress(
                phase="processing_video",
                eligible_count=eligible_total,
                saved_count=count,
                target_count=max(eligible_total, 1),
                current_video={
                    "source_url": info["url"],
                    "author_name": info["author_name"],
                    "author_url": info["author_url"],
                    "author_follower_count": info["followers"],
                    "likes": info["likes"],
                    "comments": info["comments"],
                    "favorites": info["favorites"],
                    "shares": info["shares"],
                    "source_text": info["desc"],
                },
                message=f"正在爬取视频 {count + 1}/{eligible_total}",
            )






            if info["url"] in finished:


                print(

                    "跳过已处理:",

                    info["author_name"]

                )

                continue







            if info["likes"] < MIN_LIKES:

                skipped_likes+=1

                print("跳过(点赞<%d):" % MIN_LIKES, info["author_name"], info["likes"])

                continue





            print(

                "\n处理:",

                info["author_name"],

                info["likes"]

            )






            text=""

            source=""






            # -------------------------
            # 视频下载
            # -------------------------


            video_file=download_video(

                page,

                info

            )






            # -------------------------
            # ASR
            # -------------------------


            if video_file:



                audio=extract_audio(

                    video_file

                )



                text=whisper_text(

                    audio

                )



                if text:


                    source="whisper"







            # -------------------------
            # 降级
            # -------------------------


            if (not text) or (len(text.strip()) < 8):



                print(

                    "使用视频描述"

                )



                text=refine_text(info["desc"])



                source="description"







            # 综合搜索不返回粉丝数，去作者主页补一次
            if not info["followers"]:
                info["followers"] = fetch_follower_count(page, info["author_url"])

            row={



                "source_text":

                    text,




                "source_url":

                    info["url"],




                "author_name":

                    info["author_name"],




                "author_url":

                    info["author_url"],




                "author_follower_count":

                    info["followers"],




                "platform":

                    "douyin",




                "industry":

                    INDUSTRY,




                "audience":

                    DEFAULT_AUDIENCE,




                "purpose":

                    DEFAULT_PURPOSE,




                "style":

                    DEFAULT_STYLE,




                "likes":

                    info["likes"],




                "comments":

                    info["comments"],




                "favorites":

                    info["favorites"],




                "shares":

                    info["shares"]



            }





            if save_row(row):



                count+=1
                emit_progress(
                    phase="saving",
                    eligible_count=eligible_total,
                    saved_count=count,
                    target_count=max(eligible_total, 1),
                    message=f"已保存 {count}/{eligible_total} 条",
                )



                print(

                    "已保存:",

                    count

                )







            if count>=MAX_VIDEOS:

                break

        print("汇总: 采集%d 达标保存%d 点赞不足跳过%d(门槛%d)" % (len(videos), count, skipped_likes, MIN_LIKES))

        context.close()












# ==================================================
# MAIN
# ==================================================



def main():



    print(

        "开始采集..."

    )




    videos=collect_videos()






    print(

        "\n采集视频:",

        len(videos)

    )






    process_videos(videos)






    print(

        "\n完成"

    )



    print(

        "输出:",

        CSV_FILE

    )









if __name__=="__main__":


    main()
